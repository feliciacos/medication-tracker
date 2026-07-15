"""Integration-owned switches for owners and items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import (
    DATA_MANAGER,
    DEFAULT_SHOW_SIDEBAR_PANEL,
    DOMAIN,
)
from .entity import (
    DynamicEntityController,
    item_device_info,
    manager_device_info,
    owner_device_info,
)
from .manager import MedicationStockManager


@dataclass(frozen=True)
class SwitchDefinition:
    key: str
    name: str
    icon: str


OWNER_SWITCHES = (
    SwitchDefinition("tracking_enabled", "Stock warnings", "mdi:bell-alert"),
    SwitchDefinition("reminders_enabled", "Medication reminders", "mdi:alarm"),
)
ITEM_SWITCHES = (
    SwitchDefinition("enabled", "Automatic stock management", "mdi:calendar-sync"),
    SwitchDefinition("reminder_enabled", "Send reminders", "mdi:bell-ring"),
    SwitchDefinition("ordered", "Ordered", "mdi:package-check"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: MedicationStockManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]

    def build() -> dict[str, SwitchEntity]:
        entities: dict[str, SwitchEntity] = {
            "manager:sidebar_panel": MedicationSidebarPanelSwitch(
                hass,
                entry,
            )
        }
        for owner in manager.summary_owners():
            for definition in OWNER_SWITCHES:
                entities[f"owner:{owner['id']}:{definition.key}"] = MedicationSwitch(
                    manager, "owner", owner["id"], definition
                )
        for item in manager.summary_items():
            for definition in ITEM_SWITCHES:
                entities[f"item:{item['id']}:{definition.key}"] = MedicationSwitch(
                    manager, "item", item["id"], definition
                )
        return entities

    controller = DynamicEntityController(
        hass, entry, manager, async_add_entities, build
    )
    await controller.async_setup()


class MedicationSidebarPanelSwitch(SwitchEntity):
    """Enable or disable the integration-owned sidebar page."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "Show sidebar panel"
    _attr_icon = "mdi:dock-left"
    _attr_unique_id = "medication_stock_manager_sidebar_panel"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_info = manager_device_info()

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        self.hass_ref = hass
        self.entry = entry
        self.entity_id = "switch.medication_stock_manager_sidebar_panel"

    @property
    def is_on(self) -> bool:
        return bool(
            self.entry.options.get(
                "show_sidebar_panel",
                self.entry.data.get(
                    "show_sidebar_panel",
                    DEFAULT_SHOW_SIDEBAR_PANEL,
                ),
            )
        )

    async def _async_set(self, enabled: bool) -> None:
        self.hass_ref.config_entries.async_update_entry(
            self.entry,
            options={
                **self.entry.options,
                "show_sidebar_panel": enabled,
            },
        )
        await self.hass_ref.config_entries.async_reload(
            self.entry.entry_id
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set(False)


class MedicationSwitch(SwitchEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        manager: MedicationStockManager,
        target_type: Literal["owner", "item"],
        target_id: str,
        definition: SwitchDefinition,
    ) -> None:
        self.manager = manager
        self.target_type = target_type
        self.target_id = target_id
        self.definition = definition
        slug = slugify(target_id)
        self.entity_id = (
            f"switch.medication_stock_{target_type}_{slug}_{definition.key}"
        )
        self._attr_unique_id = (
            f"medication_stock_{target_type}_{slug}_{definition.key}"
        )
        self._attr_name = definition.name
        self._attr_icon = definition.icon
        if definition.key == "ordered":
            self._attr_entity_category = None

    @property
    def device_info(self):
        if self.target_type == "owner":
            return owner_device_info(self.manager._require_owner(self.target_id))
        return item_device_info(self.manager._require_item(self.target_id))

    @property
    def is_on(self) -> bool:
        if self.target_type == "owner":
            return bool(
                self.manager._require_owner(self.target_id).get(
                    self.definition.key, True
                )
            )
        return bool(
            self.manager._require_item(self.target_id).get(
                self.definition.key, False
            )
        )

    async def _async_set(self, enabled: bool) -> None:
        if self.target_type == "owner":
            await self.manager.async_set_owner_option(
                self.target_id, self.definition.key, enabled
            )
            return
        if self.definition.key == "ordered":
            await self.manager.async_set_ordered(self.target_id, enabled)
            return
        await self.manager.async_set_item_option(
            self.target_id, self.definition.key, enabled
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set(False)
