"""Integration-owned owner calendars."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DATA_MANAGER, DOMAIN
from .entity import DynamicEntityController, owner_device_info
from .manager import MedicationStockManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: MedicationStockManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]

    def build() -> dict[str, CalendarEntity]:
        return {
            owner["id"]: MedicationOwnerCalendar(manager, owner["id"])
            for owner in manager.summary_owners()
        }

    controller = DynamicEntityController(
        hass, entry, manager, async_add_entities, build
    )
    await controller.async_setup()


class MedicationOwnerCalendar(CalendarEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "Medication"
    _attr_icon = "mdi:calendar-medical"
    _attr_initial_color = "#42a5f5"

    def __init__(self, manager: MedicationStockManager, owner_id: str) -> None:
        self.manager = manager
        self.owner_id = owner_id
        slug = slugify(owner_id)
        self.entity_id = f"calendar.medication_stock_{slug}"
        self._attr_unique_id = f"medication_stock_owner_{slug}_calendar"

    @property
    def device_info(self):
        return owner_device_info(self.manager._require_owner(self.owner_id))

    @property
    def event(self) -> CalendarEvent | None:
        return self.manager.next_calendar_event(self.owner_id)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        return self.manager.calendar_events(self.owner_id, start_date, end_date)
