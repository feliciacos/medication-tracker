"""Shared entity and dynamic platform helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, VERSION
from .manager import MedicationStockManager


def manager_device_info() -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, "manager")},
        name="Medication Stock Manager",
        manufacturer="Medication Stock Manager",
        model="Integration service",
        sw_version=VERSION,
        entry_type=DeviceEntryType.SERVICE,
    )


def owner_device_info(owner: dict[str, Any]) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"owner:{owner['id']}")},
        name=owner["name"],
        manufacturer="Medication Stock Manager",
        model="Owner profile",
        sw_version=VERSION,
        via_device=(DOMAIN, "manager"),
    )


def item_device_info(item: dict[str, Any]) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"item:{item['id']}")},
        name=item["name"],
        manufacturer="Medication Stock Manager",
        model=str(item.get("item_type", "custom_med")).replace("_", " ").title(),
        sw_version=VERSION,
        via_device=(DOMAIN, f"owner:{item['owner']}"),
    )


class DynamicEntityController:
    """Add, update and permanently remove dynamically configured entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        manager: MedicationStockManager,
        async_add_entities: AddEntitiesCallback,
        builder: Callable[[], dict[str, Entity]],
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.manager = manager
        self.async_add_entities = async_add_entities
        self.builder = builder
        self.entities: dict[str, Entity] = {}
        self._lock = asyncio.Lock()
        self._sync_pending = False

    async def async_setup(self) -> None:
        await self._async_sync()
        self.entry.async_on_unload(
            self.manager.async_add_listener(self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        if self._sync_pending:
            return
        self._sync_pending = True
        self.hass.async_create_task(self._async_sync())

    async def _async_sync(self) -> None:
        async with self._lock:
            self._sync_pending = False
            desired = self.builder()
            new_entities: list[Entity] = []
            for key, entity in desired.items():
                if key not in self.entities:
                    self.entities[key] = entity
                    new_entities.append(entity)
            if new_entities:
                self.async_add_entities(new_entities)

            for key, entity in list(self.entities.items()):
                if key not in desired:
                    self.entities.pop(key, None)
                    entity_id = entity.entity_id
                    if entity.hass is not None:
                        await entity.async_remove()
                    if entity_id:
                        registry = er.async_get(self.hass)
                        if registry.async_get(entity_id) is not None:
                            registry.async_remove(entity_id)
                    continue
                if entity.hass is not None:
                    entity.async_write_ha_state()
