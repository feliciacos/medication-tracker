"""Integration-owned stock action buttons."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DATA_MANAGER, DOMAIN
from .entity import DynamicEntityController, item_device_info
from .manager import MedicationStockManager


@dataclass(frozen=True)
class ButtonDefinition:
    key: str
    name: str
    icon: str


DEFINITIONS = (
    ButtonDefinition("receive_box", "Received box", "mdi:package-variant-plus"),
    ButtonDefinition("subtract_one", "Subtract one", "mdi:minus-circle"),
    ButtonDefinition("add_one", "Add one", "mdi:plus-circle"),
    ButtonDefinition("mark_ordered", "Mark ordered", "mdi:package-check"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: MedicationStockManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]

    def build() -> dict[str, ButtonEntity]:
        return {
            f"{item['id']}:{definition.key}": MedicationItemButton(
                manager, item["id"], definition
            )
            for item in manager.summary_items()
            for definition in DEFINITIONS
        }

    controller = DynamicEntityController(
        hass, entry, manager, async_add_entities, build
    )
    await controller.async_setup()


class MedicationItemButton(ButtonEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        manager: MedicationStockManager,
        item_id: str,
        definition: ButtonDefinition,
    ) -> None:
        self.manager = manager
        self.item_id = item_id
        self.definition = definition
        slug = slugify(item_id)
        self.entity_id = f"button.medication_stock_{slug}_{definition.key}"
        self._attr_unique_id = f"medication_stock_{slug}_{definition.key}"
        self._attr_name = definition.name
        self._attr_icon = definition.icon

    @property
    def device_info(self):
        return item_device_info(self.manager._require_item(self.item_id))

    async def async_press(self) -> None:
        if self.definition.key == "receive_box":
            await self.manager.async_receive_box(self.item_id)
        elif self.definition.key == "subtract_one":
            await self.manager.async_adjust_stock(self.item_id, -1)
        elif self.definition.key == "add_one":
            await self.manager.async_adjust_stock(self.item_id, 1)
        elif self.definition.key == "mark_ordered":
            await self.manager.async_set_ordered(self.item_id, True)
