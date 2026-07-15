"""Integration-owned editable number entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DATA_MANAGER, DOMAIN
from .entity import DynamicEntityController, item_device_info
from .manager import MedicationStockManager


@dataclass(frozen=True)
class NumberDefinition:
    key: str
    name: str
    icon: str
    category: EntityCategory | None = EntityCategory.CONFIG


DEFINITIONS = (
    NumberDefinition("stock", "Current stock", "mdi:counter", None),
    NumberDefinition("threshold", "Warning threshold", "mdi:alert-box"),
    NumberDefinition("package_size", "Package size", "mdi:package-variant"),
    NumberDefinition("usage_per_day", "Usage per active day", "mdi:calendar-clock"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: MedicationStockManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]

    def build() -> dict[str, NumberEntity]:
        return {
            f"{item['id']}:{definition.key}": MedicationItemNumber(
                manager, item["id"], definition
            )
            for item in manager.summary_items()
            for definition in DEFINITIONS
        }

    controller = DynamicEntityController(
        hass, entry, manager, async_add_entities, build
    )
    await controller.async_setup()


class MedicationItemNumber(NumberEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 1_000_000
    _attr_native_step = 0.001
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        manager: MedicationStockManager,
        item_id: str,
        definition: NumberDefinition,
    ) -> None:
        self.manager = manager
        self.item_id = item_id
        self.definition = definition
        slug = slugify(item_id)
        self.entity_id = f"number.medication_stock_{slug}_{definition.key}"
        self._attr_unique_id = f"medication_stock_{slug}_{definition.key}"
        self._attr_name = definition.name
        self._attr_icon = definition.icon
        self._attr_entity_category = definition.category

    @property
    def _item(self):
        return self.manager._require_item(self.item_id)

    @property
    def device_info(self):
        return item_device_info(self._item)

    @property
    def native_value(self) -> float:
        return float(self._item.get(self.definition.key, 0))

    @property
    def native_unit_of_measurement(self) -> str | None:
        unit = str(self._item.get("unit", "items"))
        if self.definition.key == "usage_per_day":
            return f"{unit}/day"
        return unit

    async def async_set_native_value(self, value: float) -> None:
        await self.manager.async_set_item_number(
            self.item_id, self.definition.key, value
        )
