"""Integration-owned sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import (
    DATA_MANAGER,
    DEFAULT_PANEL_ICON,
    DEFAULT_PANEL_REQUIRE_ADMIN,
    DEFAULT_PANEL_TITLE,
    DEFAULT_SHOW_SIDEBAR_PANEL,
    DOMAIN,
    SUMMARY_ENTITY_ID,
    VERSION,
)
from .entity import (
    DynamicEntityController,
    item_device_info,
    manager_device_info,
    owner_device_info,
)
from .manager import MedicationStockManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: MedicationStockManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]

    def build() -> dict[str, SensorEntity]:
        entities: dict[str, SensorEntity] = {
            "summary": MedicationStockSummarySensor(manager, entry)
        }
        for owner in manager.summary_owners():
            entities[f"owner:{owner['id']}"] = MedicationOwnerSummarySensor(
                manager, owner["id"]
            )
        for item in manager.summary_items():
            entities[f"item:{item['id']}"] = MedicationStockItemSensor(
                manager, item["id"]
            )
        return entities

    controller = DynamicEntityController(
        hass, entry, manager, async_add_entities, build
    )
    await controller.async_setup()


class MedicationStockSummarySensor(SensorEntity):
    _attr_name = "Medication Stock Manager"
    _attr_unique_id = "medication_stock_manager_summary"
    _attr_icon = "mdi:medical-bag"
    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_device_info = manager_device_info()

    def __init__(
        self,
        manager: MedicationStockManager,
        entry: ConfigEntry,
    ) -> None:
        self.manager = manager
        self.entry = entry
        self.entity_id = SUMMARY_ENTITY_ID

    def _entry_setting(self, key: str, default: Any) -> Any:
        return self.entry.options.get(
            key,
            self.entry.data.get(key, default),
        )

    @property
    def native_value(self) -> int:
        return len(self.manager.summary_items())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self.manager.summary_items()
        owners = self.manager.summary_owners()
        return {
            "items": items,
            "owners": owners,
            "people": self.manager.summary_people(),
            "owner_counts": {
                owner["id"]: sum(
                    1 for item in items if item["owner"] == owner["id"]
                )
                for owner in owners
            },
            "low_items": sum(1 for item in items if item["low"]),
            "manager_version": VERSION,
            "storage": "integration_owned",
            "configuration_yaml_required": False,
            "sidebar": {
                "show_sidebar_panel": bool(
                    self._entry_setting(
                        "show_sidebar_panel",
                        DEFAULT_SHOW_SIDEBAR_PANEL,
                    )
                ),
                "sidebar_title": str(
                    self._entry_setting(
                        "sidebar_title",
                        DEFAULT_PANEL_TITLE,
                    )
                ),
                "sidebar_icon": str(
                    self._entry_setting(
                        "sidebar_icon",
                        DEFAULT_PANEL_ICON,
                    )
                ),
                "sidebar_require_admin": bool(
                    self._entry_setting(
                        "sidebar_require_admin",
                        DEFAULT_PANEL_REQUIRE_ADMIN,
                    )
                ),
            },
        }


class MedicationOwnerSummarySensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "Managed items"
    _attr_icon = "mdi:account-medical"

    def __init__(self, manager: MedicationStockManager, owner_id: str) -> None:
        self.manager = manager
        self.owner_id = owner_id
        slug = slugify(owner_id)
        self.entity_id = f"sensor.medication_stock_owner_{slug}"
        self._attr_unique_id = f"medication_stock_owner_{slug}_summary"

    @property
    def device_info(self):
        return owner_device_info(self.manager._require_owner(self.owner_id))

    @property
    def native_value(self) -> int:
        return sum(
            1
            for item in self.manager.items.values()
            if item.get("owner") == self.owner_id
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        owner = self.manager._require_owner(self.owner_id)
        items = [
            item
            for item in self.manager.summary_items()
            if item["owner"] == self.owner_id
        ]
        return {
            "owner_id": self.owner_id,
            "person_entity": owner.get("person_entity", ""),
            "calendar_entity": self.manager.owner_calendar_entity_id(self.owner_id),
            "low_items": sum(1 for item in items if item["low"]),
            "notification_targets": sorted(
                set(owner.get("reminder_notify_entities", []))
                | set(owner.get("stock_notify_entities", []))
            ),
        }


class MedicationStockItemSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, manager: MedicationStockManager, item_id: str) -> None:
        self.manager = manager
        self.item_id = item_id
        slug = slugify(item_id)
        self.entity_id = f"sensor.medication_stock_item_{slug}"
        self._attr_unique_id = f"medication_stock_item_{slug}"

    @property
    def _item(self) -> dict[str, Any]:
        return self.manager._require_item(self.item_id)

    @property
    def name(self) -> str:
        return str(self._item.get("name", self.item_id))

    @property
    def icon(self) -> str:
        return str(self._item.get("icon", "mdi:pill"))

    @property
    def device_info(self):
        return item_device_info(self._item)

    @property
    def native_value(self) -> float:
        return self.manager.item_stock(self._item)

    @property
    def native_unit_of_measurement(self) -> str:
        return str(self._item.get("unit", "items"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        summary = next(
            item
            for item in self.manager.summary_items()
            if item["id"] == self.item_id
        )
        return {
            **summary,
            "item_id": self.item_id,
            "manager_item": True,
        }
