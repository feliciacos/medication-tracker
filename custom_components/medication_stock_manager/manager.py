"""Persistent, integration-owned medication stock manager."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from copy import deepcopy
from datetime import date, datetime, time, timedelta
import logging
import re
from typing import Any

from homeassistant.components.calendar import CalendarEvent
from homeassistant.components.person import async_create_person
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_call_later, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import (
    ALL_DAYS,
    DEFAULT_OWNER_ID,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    VERSION,
    WEEKDAYS,
)

_LOGGER = logging.getLogger(__name__)
_TIME_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")


class MedicationStockManager:
    """Own all configuration, controls, schedules, calendars and state."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
        )
        self.items: dict[str, dict[str, Any]] = {}
        self.owners: dict[str, dict[str, Any]] = {}
        self.last_runs: dict[str, str] = {}
        self._last_low: dict[str, bool] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribers: list[Callable[[], None]] = []
        self._save_cancel: Callable[[], None] | None = None
        self._device_cleanup_cancels: dict[str, Callable[[], None]] = {}

    async def async_load(self) -> None:
        """Load integration storage and detach any historical helper fields."""
        stored = await self._store.async_load() or {}
        self.items = dict(stored.get("items", {}))
        self.owners = dict(stored.get("owners", {}))
        self.last_runs = dict(stored.get("last_runs", {}))
        changed = False

        # Older releases allowed item data without a separately stored owner.
        for item in self.items.values():
            owner_id = slugify(str(item.get("owner", ""))) or DEFAULT_OWNER_ID
            if item.get("owner") != owner_id:
                item["owner"] = owner_id
                changed = True
            if owner_id not in self.owners:
                self.owners[owner_id] = self._normalize_owner(
                    {
                        "id": owner_id,
                        "name": owner_id.replace("_", " ").title(),
                    }
                )
                changed = True

        normalized_owners: dict[str, dict[str, Any]] = {}
        for old_id, old_owner in self.owners.items():
            owner_id = slugify(str(old_owner.get("id") or old_id)) or DEFAULT_OWNER_ID
            owner = self._normalize_owner({**old_owner, "id": owner_id})
            self._migrate_owner_helpers(owner, old_owner)
            normalized_owners[owner_id] = owner
            if owner_id != old_id or owner != old_owner:
                changed = True
        self.owners = normalized_owners

        normalized_items: dict[str, dict[str, Any]] = {}
        for index, (old_id, old_item) in enumerate(self.items.items(), start=1):
            item = dict(old_item)
            item_id = slugify(str(item.get("id") or old_id)) or f"item_{index}"
            owner_id = slugify(str(item.get("owner", ""))) or DEFAULT_OWNER_ID
            if owner_id not in self.owners:
                self.owners[owner_id] = self._normalize_owner(
                    {"id": owner_id, "name": owner_id.replace("_", " ").title()}
                )
            item.update(
                {
                    "id": item_id,
                    "owner": owner_id,
                    "name": str(item.get("name") or item_id.replace("_", " ").title()),
                    "item_type": self._normalize_item_type(
                        item.get("item_type", "custom_med")
                    ),
                    "unit": str(item.get("unit", "items")) or "items",
                    "icon": str(item.get("icon", "mdi:pill")) or "mdi:pill",
                    "stock": self._legacy_number(item, "stock_entity", item.get("stock", 0)),
                    "threshold": self._legacy_number(
                        item, "threshold_entity", item.get("threshold", 0)
                    ),
                    "ordered": self._legacy_boolean(
                        item, "ordered_entity", item.get("ordered", False)
                    ),
                    "display_order": int(item.get("display_order", 1000 + index * 10)),
                    "package_size": max(float(item.get("package_size", 0)), 0),
                    "usage_per_day": max(float(item.get("usage_per_day", 0)), 0),
                    "enabled": bool(item.get("enabled", True)),
                    "reminder_enabled": bool(item.get("reminder_enabled", False)),
                    "reminder_title": str(item.get("reminder_title", "")),
                    "reminder_message": str(item.get("reminder_message", "")),
                    "product_url": str(item.get("product_url", "")),
                }
            )
            for obsolete in (
                "stock_entity",
                "threshold_entity",
                "ordered_entity",
                "calendar_entity",
                "built_in",
                "deleted",
            ):
                item.pop(obsolete, None)
            try:
                self._normalize_schedule(item)
            except ValueError:
                item["schedule_mode"] = "manual"
                item["usage_per_day"] = 0
                item["times"] = []
            normalized_items[item_id] = item
            if item_id != old_id or item != old_item:
                changed = True
        self.items = normalized_items
        if self._normalize_display_orders():
            changed = True

        if changed or not stored:
            await self.async_save()

    def _migrate_owner_helpers(
        self,
        owner: dict[str, Any],
        old_owner: dict[str, Any],
    ) -> None:
        """Copy legacy helper states once, then use integration switches."""
        for old_field, new_field, fallback in (
            ("tracking_enabled_entity", "tracking_enabled", True),
            ("reminders_enabled_entity", "reminders_enabled", True),
        ):
            if new_field in old_owner:
                owner[new_field] = bool(old_owner[new_field])
                continue
            entity_id = str(old_owner.get(old_field, "")).strip()
            state = self.hass.states.get(entity_id) if entity_id else None
            owner[new_field] = fallback if state is None else state.state == "on"

    def _legacy_number(
        self,
        item: dict[str, Any],
        entity_field: str,
        fallback: Any,
    ) -> float:
        entity_id = str(item.get(entity_field, "")).strip()
        state = self.hass.states.get(entity_id) if entity_id else None
        try:
            return max(float(state.state if state is not None else fallback), 0)
        except (TypeError, ValueError):
            return max(float(fallback or 0), 0)

    def _legacy_boolean(
        self,
        item: dict[str, Any],
        entity_field: str,
        fallback: Any,
    ) -> bool:
        entity_id = str(item.get(entity_field, "")).strip()
        state = self.hass.states.get(entity_id) if entity_id else None
        return bool(fallback) if state is None else state.state == "on"

    async def async_start(self) -> None:
        """Start the integration-owned scheduler."""
        self._unsubscribers.append(
            async_track_time_change(self.hass, self._minute_tick, second=5)
        )
        self._unsubscribers.append(
            async_call_later(self.hass, 30, self._startup_tasks)
        )
        self._refresh_low_cache()
        self.async_notify_listeners()

    async def async_stop(self) -> None:
        """Stop scheduler and pending jobs."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        if self._save_cancel is not None:
            self._save_cancel()
            self._save_cancel = None
        for cancel in self._device_cleanup_cancels.values():
            cancel()
        self._device_cleanup_cancels.clear()
        await self.async_save()

    async def async_save(self) -> None:
        """Persist all manager data in integration storage."""
        await self._store.async_save(
            {
                "items": self.items,
                "owners": self.owners,
                "last_runs": self.last_runs,
            }
        )

    @callback
    def _schedule_save(self, delay: float = 0.2) -> None:
        """Debounce rapid stock changes into one disk write."""
        if self._save_cancel is not None:
            self._save_cancel()

        @callback
        def save_now(_: datetime) -> None:
            self._save_cancel = None
            self.hass.async_create_task(self.async_save())

        self._save_cancel = async_call_later(self.hass, delay, save_now)

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an entity-platform update listener."""
        self._listeners.append(listener)

        @callback
        def remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    @callback
    def async_notify_listeners(self) -> None:
        """Notify every integration entity platform."""
        for listener in list(self._listeners):
            listener()

    # ------------------------------------------------------------------
    # Device registry
    # ------------------------------------------------------------------
    async def async_ensure_devices(self) -> None:
        """Create service, owner and item devices in the integration page."""
        registry = dr.async_get(self.hass)
        registry.async_get_or_create(
            config_entry_id=self.entry_id,
            identifiers={(DOMAIN, "manager")},
            name="Medication Stock Manager",
            manufacturer="Medication Stock Manager",
            model="Integration service",
            sw_version=VERSION,
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        for owner in self.owners.values():
            self._ensure_owner_device(registry, owner)
        for item in self.items.values():
            self._ensure_item_device(registry, item)

    def _ensure_owner_device(
        self,
        registry: dr.DeviceRegistry,
        owner: dict[str, Any],
    ) -> None:
        registry.async_get_or_create(
            config_entry_id=self.entry_id,
            identifiers={(DOMAIN, f"owner:{owner['id']}")},
            name=owner["name"],
            manufacturer="Medication Stock Manager",
            model="Owner profile",
            sw_version=VERSION,
            via_device=(DOMAIN, "manager"),
        )

    def _ensure_item_device(
        self,
        registry: dr.DeviceRegistry,
        item: dict[str, Any],
    ) -> None:
        registry.async_get_or_create(
            config_entry_id=self.entry_id,
            identifiers={(DOMAIN, f"item:{item['id']}")},
            name=item["name"],
            manufacturer="Medication Stock Manager",
            model=self._normalize_item_type(
                item.get("item_type", "custom_med")
            ).replace("_", " ").title(),
            sw_version=VERSION,
            via_device=(DOMAIN, f"owner:{item['owner']}"),
        )

    def _schedule_device_removal(self, identifier: str) -> None:
        if cancel := self._device_cleanup_cancels.pop(identifier, None):
            cancel()

        @callback
        def remove(_: datetime) -> None:
            self._device_cleanup_cancels.pop(identifier, None)
            registry = dr.async_get(self.hass)
            device = registry.async_get_device(
                identifiers={(DOMAIN, identifier)}
            )
            if device is not None:
                registry.async_remove_device(device.id)

        self._device_cleanup_cancels[identifier] = async_call_later(
            self.hass, 1.0, remove
        )

    # ------------------------------------------------------------------
    # Owners and Person/mobile discovery
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_entity_list(value: Any) -> list[str]:
        if value is None:
            return []
        values = value if isinstance(value, list) else str(value).split(",")
        result: list[str] = []
        for entry in values:
            entity_id = str(entry).strip()
            if entity_id and entity_id not in result:
                result.append(entity_id)
        return result

    def _normalize_owner(self, owner: dict[str, Any]) -> dict[str, Any]:
        owner_id = slugify(str(owner.get("id", ""))) or DEFAULT_OWNER_ID
        name = str(owner.get("name", "")).strip()
        return {
            "id": owner_id,
            "name": name or owner_id.replace("_", " ").title(),
            "person_entity": str(owner.get("person_entity", "")).strip(),
            "auto_create_person": bool(owner.get("auto_create_person", True)),
            "auto_detect_notify": bool(owner.get("auto_detect_notify", True)),
            "reminder_notify_entities": self._normalize_entity_list(
                owner.get("reminder_notify_entities")
            ),
            "stock_notify_entities": self._normalize_entity_list(
                owner.get("stock_notify_entities")
            ),
            "tracking_enabled": bool(owner.get("tracking_enabled", True)),
            "reminders_enabled": bool(owner.get("reminders_enabled", True)),
            "default_reminder_title": str(
                owner.get("default_reminder_title", "Medication Reminder")
            ).strip()
            or "Medication Reminder",
            "order_title": str(owner.get("order_title", "Order Medication")).strip()
            or "Order Medication",
            "check_order_title": str(
                owner.get("check_order_title", "Check Medication Order")
            ).strip()
            or "Check Medication Order",
        }

    def _require_owner(self, owner_id: str) -> dict[str, Any]:
        owner = self.owners.get(slugify(str(owner_id)))
        if owner is None:
            raise ValueError(f"Unknown owner: {owner_id}. Create the owner first.")
        return owner

    def _find_person_by_name(self, name: str) -> str:
        wanted = name.strip().casefold()
        for state in self.hass.states.async_all("person"):
            friendly = str(state.attributes.get("friendly_name", "")).casefold()
            if friendly == wanted:
                return state.entity_id
        return ""

    async def _ensure_person(
        self,
        name: str,
        person_entity: str,
        create_person: bool,
    ) -> str:
        if person_entity and self.hass.states.get(person_entity) is not None:
            return person_entity
        matched = self._find_person_by_name(name)
        if matched or not create_person:
            return matched
        before = {state.entity_id for state in self.hass.states.async_all("person")}
        await async_create_person(self.hass, name)
        for _ in range(20):
            await asyncio.sleep(0.05)
            matched = self._find_person_by_name(name)
            if matched:
                return matched
            new_states = [
                state.entity_id
                for state in self.hass.states.async_all("person")
                if state.entity_id not in before
            ]
            if len(new_states) == 1:
                return new_states[0]
        return f"person.{slugify(name)}"

    def _discover_notify_entities(self, person_entity: str) -> list[str]:
        person = self.hass.states.get(person_entity)
        if person is None:
            return []
        trackers = list(person.attributes.get("device_trackers", []) or [])
        source = person.attributes.get("source")
        if source and source not in trackers:
            trackers.append(source)
        registry = er.async_get(self.hass)
        device_ids = {
            entry.device_id
            for tracker in trackers
            if (entry := registry.async_get(tracker)) is not None
            and entry.device_id is not None
        }
        return sorted(
            {
                entry.entity_id
                for entry in registry.entities.values()
                if entry.domain == "notify"
                and entry.device_id in device_ids
                and entry.disabled_by is None
            }
        )

    def summary_people(self) -> list[dict[str, Any]]:
        return [
            {
                "entity_id": state.entity_id,
                "name": state.attributes.get("friendly_name", state.name),
                "device_trackers": list(
                    state.attributes.get("device_trackers", []) or []
                ),
                "notify_entities": self._discover_notify_entities(state.entity_id),
            }
            for state in self.hass.states.async_all("person")
        ]

    async def async_add_owner(self, data: dict[str, Any]) -> str:
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Owner name is required")
        owner_id = slugify(str(data.get("owner_id") or name))
        if not owner_id or owner_id == "all":
            raise ValueError("Owner ID is invalid or reserved")
        if owner_id in self.owners:
            raise ValueError(f"Owner already exists: {owner_id}")

        person_entity = await self._ensure_person(
            name,
            str(data.get("person_entity", "")).strip(),
            bool(data.get("auto_create_person", True)),
        )
        reminder_targets = self._normalize_entity_list(
            data.get("reminder_notify_entities")
        )
        stock_targets = self._normalize_entity_list(
            data.get("stock_notify_entities")
        )
        if bool(data.get("auto_detect_notify", True)) and person_entity:
            detected = self._discover_notify_entities(person_entity)
            if not reminder_targets:
                reminder_targets = detected
            if not stock_targets:
                stock_targets = detected

        owner = self._normalize_owner(
            {
                **data,
                "id": owner_id,
                "name": name,
                "person_entity": person_entity,
                "reminder_notify_entities": reminder_targets,
                "stock_notify_entities": stock_targets,
            }
        )
        self.owners[owner_id] = owner
        registry = dr.async_get(self.hass)
        self._ensure_owner_device(registry, owner)
        await self.async_save()
        self.async_notify_listeners()
        return owner_id

    async def async_update_owner(
        self,
        owner_id: str,
        data: dict[str, Any],
    ) -> None:
        owner = self._require_owner(owner_id)
        merged = {**owner, **data, "id": owner["id"]}
        name = str(merged.get("name") or owner["name"]).strip()
        person_entity = await self._ensure_person(
            name,
            str(merged.get("person_entity", "")).strip(),
            bool(merged.get("auto_create_person", True)),
        )
        merged["person_entity"] = person_entity
        if bool(merged.get("auto_detect_notify", True)) and person_entity:
            detected = self._discover_notify_entities(person_entity)
            if not self._normalize_entity_list(
                merged.get("reminder_notify_entities")
            ):
                merged["reminder_notify_entities"] = detected
            if not self._normalize_entity_list(merged.get("stock_notify_entities")):
                merged["stock_notify_entities"] = detected
        updated = self._normalize_owner(merged)
        self.owners[owner["id"]] = updated
        self._ensure_owner_device(dr.async_get(self.hass), updated)
        await self.async_save()
        self.async_notify_listeners()

    async def async_set_owner_option(
        self,
        owner_id: str,
        field: str,
        enabled: bool,
    ) -> None:
        if field not in {"tracking_enabled", "reminders_enabled"}:
            raise ValueError(f"Unsupported owner option: {field}")
        owner = self._require_owner(owner_id)
        owner[field] = bool(enabled)
        self._schedule_save()
        self.async_notify_listeners()

    async def async_remove_owner(self, owner_id: str) -> None:
        owner = self._require_owner(owner_id)
        if any(item.get("owner") == owner["id"] for item in self.items.values()):
            raise ValueError("Move or remove all items assigned to this owner first.")
        self.owners.pop(owner["id"], None)
        await self.async_save()
        self.async_notify_listeners()
        self._schedule_device_removal(f"owner:{owner['id']}")

    def owner_calendar_entity_id(self, owner_id: str) -> str:
        return f"calendar.medication_stock_{slugify(owner_id)}"

    def summary_owners(self) -> list[dict[str, Any]]:
        return sorted(
            [
                {
                    **deepcopy(owner),
                    "calendar_entity": self.owner_calendar_entity_id(owner["id"]),
                }
                for owner in self.owners.values()
            ],
            key=lambda owner: owner["name"].lower(),
        )

    # ------------------------------------------------------------------
    # Item state and editing
    # ------------------------------------------------------------------
    def _require_item(self, item_id: str) -> dict[str, Any]:
        reference = str(item_id)
        if reference in self.items:
            return self.items[reference]
        state = self.hass.states.get(reference)
        resolved = state.attributes.get("item_id") if state is not None else None
        if resolved and str(resolved) in self.items:
            return self.items[str(resolved)]
        raise ValueError(f"Unknown item: {reference}")

    def item_stock(self, item: dict[str, Any]) -> float:
        return float(item.get("stock", 0))

    def item_threshold(self, item: dict[str, Any]) -> float:
        return float(item.get("threshold", 0))

    def item_ordered(self, item: dict[str, Any]) -> bool:
        return bool(item.get("ordered", False))

    def item_low(self, item: dict[str, Any]) -> bool:
        return self.item_stock(item) <= self.item_threshold(item)

    async def async_set_stock(self, item_id: str, value: float) -> None:
        item = self._require_item(item_id)
        item["stock"] = round(max(float(value), 0), 3)
        if not self.item_low(item):
            item["ordered"] = False
        self._schedule_save()
        self.async_notify_listeners()
        self.hass.async_create_task(self._check_low_transition(item))

    async def async_set_threshold(self, item_id: str, value: float) -> None:
        item = self._require_item(item_id)
        item["threshold"] = round(max(float(value), 0), 3)
        if not self.item_low(item):
            item["ordered"] = False
        self._schedule_save()
        self.async_notify_listeners()
        self.hass.async_create_task(self._check_low_transition(item))

    async def async_adjust_stock(self, item_id: str, amount: float) -> None:
        item = self._require_item(item_id)
        await self.async_set_stock(item["id"], self.item_stock(item) + float(amount))

    async def async_receive_box(self, item_id: str) -> None:
        item = self._require_item(item_id)
        item["stock"] = round(
            max(self.item_stock(item) + float(item.get("package_size", 0)), 0),
            3,
        )
        item["ordered"] = False
        self._schedule_save()
        self.async_notify_listeners()
        self.hass.async_create_task(self._check_low_transition(item))

    async def async_set_ordered(self, item_id: str, ordered: bool) -> None:
        item = self._require_item(item_id)
        item["ordered"] = bool(ordered) and self.item_low(item)
        self._schedule_save()
        self.async_notify_listeners()

    async def async_set_item_option(
        self,
        item_id: str,
        field: str,
        enabled: bool,
    ) -> None:
        if field not in {"enabled", "reminder_enabled"}:
            raise ValueError(f"Unsupported item option: {field}")
        item = self._require_item(item_id)
        item[field] = bool(enabled)
        self._schedule_save()
        self.async_notify_listeners()

    async def async_set_item_number(
        self,
        item_id: str,
        field: str,
        value: float,
    ) -> None:
        if field == "stock":
            await self.async_set_stock(item_id, value)
            return
        if field == "threshold":
            await self.async_set_threshold(item_id, value)
            return
        if field not in {"package_size", "usage_per_day"}:
            raise ValueError(f"Unsupported item number: {field}")
        item = self._require_item(item_id)
        item[field] = round(max(float(value), 0), 3)
        self._normalize_schedule(item)
        self._schedule_save()
        self.async_notify_listeners()

    async def async_add_item(self, data: dict[str, Any]) -> str:
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Item name is required")
        requested_owner = str(data.get("owner", "")).strip()
        if requested_owner:
            owner = self._require_owner(requested_owner)["id"]
        elif self.owners:
            owner = self.summary_owners()[0]["id"]
        else:
            raise ValueError("Create an owner before creating an item")

        base_id = slugify(f"{owner}_{name}") or f"{owner}_item"
        item_id = base_id
        suffix = 2
        while item_id in self.items:
            item_id = f"{base_id}_{suffix}"
            suffix += 1

        item_type = self._normalize_item_type(data.get("item_type", "custom_med"))
        item = {
            "id": item_id,
            "owner": owner,
            "name": name,
            "item_type": item_type,
            "display_order": self._next_display_order(owner, item_type),
            "unit": str(data.get("unit", "items")).strip() or "items",
            "icon": str(data.get("icon", "mdi:pill")).strip() or "mdi:pill",
            "stock": max(float(data.get("stock", 0)), 0),
            "threshold": max(float(data.get("threshold", 0)), 0),
            "package_size": max(float(data.get("package_size", 0)), 0),
            "usage_per_day": max(float(data.get("usage_per_day", 0)), 0),
            "schedule_mode": str(data.get("schedule_mode", "daily")),
            "days": self._normalize_days(data.get("days", ALL_DAYS)),
            "times": self._normalize_times(data.get("times", [])),
            "interval_days": max(int(data.get("interval_days", 1)), 1),
            "start_date": self._normalize_date(data.get("start_date")),
            "ordered": False,
            "enabled": bool(data.get("enabled", True)),
            "reminder_enabled": bool(data.get("reminder_enabled", False)),
            "reminder_title": str(data.get("reminder_title", "")).strip(),
            "reminder_message": str(data.get("reminder_message", name)).strip(),
            "product_url": str(data.get("product_url", "")).strip(),
        }
        self._normalize_schedule(item)
        self.items[item_id] = item
        self._last_low[item_id] = False
        registry = dr.async_get(self.hass)
        self._ensure_item_device(registry, item)
        await self.async_save()
        self.async_notify_listeners()
        await self._check_low_transition(item)
        return item_id

    async def async_update_item(self, item_id: str, data: dict[str, Any]) -> None:
        item = self._require_item(item_id)
        previous_bucket = (
            item.get("owner", ""),
            self._item_category(str(item.get("item_type", "custom_med"))),
        )
        if "stock" in data:
            item["stock"] = max(float(data["stock"]), 0)
        if "threshold" in data:
            item["threshold"] = max(float(data["threshold"]), 0)
        for field in (
            "name",
            "unit",
            "icon",
            "schedule_mode",
            "start_date",
            "reminder_title",
            "reminder_message",
            "product_url",
        ):
            if field in data:
                item[field] = str(data[field]).strip()
        if "item_type" in data:
            item["item_type"] = self._normalize_item_type(data["item_type"])
        if "owner" in data:
            item["owner"] = self._require_owner(str(data["owner"]))["id"]
        for field in ("package_size", "usage_per_day"):
            if field in data:
                item[field] = max(float(data[field]), 0)
        if "interval_days" in data:
            item["interval_days"] = max(int(data["interval_days"]), 1)
        if "days" in data:
            item["days"] = self._normalize_days(data["days"])
        if "times" in data:
            item["times"] = self._normalize_times(data["times"])
        if "enabled" in data:
            item["enabled"] = bool(data["enabled"])
        if "reminder_enabled" in data:
            item["reminder_enabled"] = bool(data["reminder_enabled"])

        current_bucket = (
            item.get("owner", ""),
            self._item_category(str(item.get("item_type", "custom_med"))),
        )
        if current_bucket != previous_bucket:
            item["display_order"] = self._next_display_order(
                str(item.get("owner", "")),
                str(item.get("item_type", "custom_med")),
                exclude_item_id=item["id"],
            )

        self._normalize_schedule(item)
        self._normalize_display_orders()
        if not self.item_low(item):
            item["ordered"] = False
        self._ensure_item_device(dr.async_get(self.hass), item)
        await self.async_save()
        await self._check_low_transition(item)
        self.async_notify_listeners()

    async def async_move_item(self, item_id: str, direction: str) -> None:
        """Move an item within its owner and medication/supply category."""
        item = self._require_item(item_id)
        normalized_direction = str(direction).strip().lower()
        if normalized_direction not in {"up", "down"}:
            raise ValueError("Direction must be up or down")

        owner = str(item.get("owner", ""))
        category = self._item_category(
            str(item.get("item_type", "custom_med"))
        )
        siblings = sorted(
            (
                candidate
                for candidate in self.items.values()
                if candidate.get("owner") == owner
                and self._item_category(
                    str(candidate.get("item_type", "custom_med"))
                )
                == category
            ),
            key=lambda candidate: (
                int(candidate.get("display_order", 1000)),
                str(candidate.get("name", "")).lower(),
                str(candidate.get("id", "")),
            ),
        )
        current_index = next(
            (
                index
                for index, candidate in enumerate(siblings)
                if candidate["id"] == item["id"]
            ),
            None,
        )
        if current_index is None:
            return
        target_index = current_index + (-1 if normalized_direction == "up" else 1)
        if target_index < 0 or target_index >= len(siblings):
            return

        target = siblings[target_index]
        item_order = int(item.get("display_order", 1000))
        target_order = int(target.get("display_order", 1000))
        item["display_order"], target["display_order"] = target_order, item_order
        self._normalize_display_orders()
        await self.async_save()
        self.async_notify_listeners()

    async def async_remove_item(self, item_id: str) -> None:
        item = self._require_item(item_id)
        self.items.pop(item["id"], None)
        self._normalize_display_orders()
        self._last_low.pop(item["id"], None)
        self.last_runs = {
            key: value
            for key, value in self.last_runs.items()
            if not key.startswith(f"{item['id']}|")
        }
        await self.async_save()
        self.async_notify_listeners()
        self._schedule_device_removal(f"item:{item['id']}")

    async def async_clear_all_items(self) -> None:
        item_ids = list(self.items)
        self.items.clear()
        self.last_runs.clear()
        self._last_low.clear()
        await self.async_save()
        self.async_notify_listeners()
        for item_id in item_ids:
            self._schedule_device_removal(f"item:{item_id}")

    async def async_restore_defaults(self) -> None:
        await self.async_clear_all_items()

    # ------------------------------------------------------------------
    # Schedule calculations and processing
    # ------------------------------------------------------------------
    def _normalize_days(self, value: Any) -> list[str]:
        if value is None:
            return list(ALL_DAYS)
        if isinstance(value, str):
            value = [part.strip().lower() for part in value.split(",")]
        if not isinstance(value, list):
            return list(ALL_DAYS)
        selected = {str(day).lower() for day in value}
        return [day for day in WEEKDAYS if day in selected]

    def _normalize_times(self, value: Any) -> list[str]:
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        if not isinstance(value, list):
            return []
        normalized: set[str] = set()
        for raw in value:
            candidate = str(raw).strip()
            if not _TIME_RE.match(candidate):
                continue
            hour, minute = candidate.split(":", 1)
            normalized.add(f"{int(hour):02d}:{minute}")
        return sorted(normalized)

    def _normalize_date(self, value: Any) -> str:
        try:
            return date.fromisoformat(str(value)).isoformat()
        except (TypeError, ValueError):
            return dt_util.now().date().isoformat()

    def _normalize_schedule(self, item: dict[str, Any]) -> None:
        item["usage_per_day"] = max(float(item.get("usage_per_day", 0)), 0)
        item["times"] = self._normalize_times(item.get("times", []))
        item["days"] = self._normalize_days(item.get("days", ALL_DAYS))
        item["interval_days"] = max(int(item.get("interval_days", 1)), 1)
        item["start_date"] = self._normalize_date(item.get("start_date"))
        requested = str(item.get("schedule_mode", "daily")).lower()
        if requested == "weekly":
            requested = (
                "daily"
                if set(item["days"]) == set(ALL_DAYS)
                else "selected_weekdays"
            )
        if requested == "manual" or item["usage_per_day"] <= 0 or not item["times"]:
            item["schedule_mode"] = "manual"
            item["usage_per_day"] = 0
            item["times"] = []
            return
        if requested in {"interval", "every_x_days"}:
            item["schedule_mode"] = "interval"
            item["days"] = list(ALL_DAYS)
            return
        if requested == "selected_weekdays":
            if not item["days"]:
                raise ValueError("Select at least one active weekday")
            item["schedule_mode"] = "selected_weekdays"
            return
        item["schedule_mode"] = "daily"
        item["days"] = list(ALL_DAYS)

    def _date_is_active(self, item: dict[str, Any], check_date: date) -> bool:
        if float(item.get("usage_per_day", 0)) <= 0 or not item.get("times"):
            return False
        mode = item.get("schedule_mode")
        if mode == "interval":
            try:
                start = date.fromisoformat(str(item.get("start_date")))
            except ValueError:
                start = check_date
            delta = (check_date - start).days
            return delta >= 0 and delta % max(int(item.get("interval_days", 1)), 1) == 0
        if mode == "selected_weekdays":
            return WEEKDAYS[check_date.weekday()] in item.get("days", ALL_DAYS)
        return mode == "daily"

    def _schedule_text(self, item: dict[str, Any]) -> str:
        usage = float(item.get("usage_per_day", 0))
        times = item.get("times", [])
        mode = item.get("schedule_mode")
        if usage <= 0 or not times or mode == "manual":
            return "Manual"
        time_text = ", ".join(times)
        if mode == "interval":
            return (
                f"{self._format_number(usage)} per active day, every "
                f"{item.get('interval_days', 1)} days at {time_text}"
            )
        if mode == "selected_weekdays":
            day_text = ", ".join(day.title() for day in item.get("days", []))
            return f"{self._format_number(usage)} per active day; {day_text} at {time_text}"
        return f"{self._format_number(usage)} per day at {time_text}"

    def _calculate_dates(
        self,
        item: dict[str, Any],
        stock: float | None = None,
        threshold: float | None = None,
    ) -> tuple[date | None, date | None, int | None]:
        usage = float(item.get("usage_per_day", 0))
        if usage <= 0 or not item.get("times"):
            return None, None, None
        remaining = self.item_stock(item) if stock is None else stock
        threshold_value = self.item_threshold(item) if threshold is None else threshold
        today = dt_util.now().date()
        order_date: date | None = today if remaining <= threshold_value else None
        run_out_date: date | None = today if remaining <= 0 else None
        for offset in range(0, 3651):
            current = today + timedelta(days=offset)
            if not self._date_is_active(item, current):
                continue
            remaining -= usage
            if order_date is None and remaining <= threshold_value:
                order_date = current
            if remaining <= 0:
                return order_date, current, offset
        return order_date, run_out_date, None

    @callback
    def _minute_tick(self, now: datetime) -> None:
        self.hass.async_create_task(self.async_process_time(now))

    @callback
    def _startup_tasks(self, _: datetime) -> None:
        self.hass.async_create_task(self.async_startup_refresh())

    async def async_startup_refresh(self) -> None:
        await self.async_clear_completed_orders()
        self._refresh_low_cache()
        self.async_notify_listeners()
        await self.async_send_due_stock_warnings(startup=True)

    async def async_process_time(self, now: datetime | None = None) -> None:
        now = dt_util.as_local(now or dt_util.now())
        current_time = now.strftime("%H:%M")
        changed = False
        for item in list(self.items.values()):
            if not item.get("enabled", True):
                continue
            if not self._date_is_active(item, now.date()):
                continue
            if current_time not in item.get("times", []):
                continue
            run_key = f"{item['id']}|{now.date().isoformat()}|{current_time}"
            if run_key in self.last_runs:
                continue
            amount = float(item.get("usage_per_day", 0)) / max(
                len(item.get("times", [])), 1
            )
            await self.async_set_stock(item["id"], self.item_stock(item) - amount)
            await self._send_item_reminder(item)
            self.last_runs[run_key] = now.isoformat()
            changed = True
        if current_time == "09:00":
            key = f"warnings|{now.date().isoformat()}|09:00"
            if key not in self.last_runs:
                await self.async_send_due_stock_warnings(now=now)
                self.last_runs[key] = now.isoformat()
                changed = True
        if changed:
            cutoff = now.date() - timedelta(days=45)
            self.last_runs = {
                key: value
                for key, value in self.last_runs.items()
                if self._run_key_is_recent(key, cutoff)
            }
            await self.async_save()
            self.async_notify_listeners()

    @staticmethod
    def _run_key_is_recent(key: str, cutoff: date) -> bool:
        for part in key.split("|"):
            try:
                return date.fromisoformat(part) >= cutoff
            except ValueError:
                continue
        return True

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _owner_notification_targets(
        self,
        owner: dict[str, Any],
        field: str,
    ) -> list[str]:
        """Return configured targets and self-heal Person/mobile discovery."""
        targets = self._normalize_entity_list(owner.get(field))
        available: list[str] = []
        for target in targets:
            if self.hass.states.get(target) is not None:
                available.append(target)
                continue
            if "." in target:
                domain, service = target.split(".", 1)
                if self.hass.services.has_service(domain, service):
                    available.append(target)

        if owner.get("auto_detect_notify", True) and owner.get("person_entity"):
            for target in self._discover_notify_entities(
                str(owner["person_entity"])
            ):
                if target not in available:
                    available.append(target)

        if available != targets:
            owner[field] = available
            self._schedule_save()
            self.async_notify_listeners()
        return available

    async def _send_item_reminder(self, item: dict[str, Any]) -> None:
        if not item.get("reminder_enabled"):
            return
        owner = self.owners.get(str(item.get("owner")))
        if owner is None or not owner.get("reminders_enabled", True):
            return
        targets = self._owner_notification_targets(
            owner,
            "reminder_notify_entities",
        )
        if not targets:
            return
        await self._send_notification(
            targets,
            item.get("reminder_title")
            or owner.get("default_reminder_title")
            or "Medication Reminder",
            item.get("reminder_message") or item["name"],
            f"medication_manager_reminder_{item['id']}",
        )

    async def _send_notification(
        self,
        targets: list[str],
        title: str,
        message: str,
        tag: str,
    ) -> None:
        """Send to notify entities and legacy mobile-app notify actions.

        The notify.send_message entity action accepts message/title only.
        Companion-app legacy actions can additionally receive the tag payload.
        Calls are blocking so validation or delivery setup errors are logged.
        """
        delivered = 0
        for raw_target in targets:
            target = str(raw_target).strip()
            if not target:
                continue

            try:
                if (
                    target.startswith("notify.")
                    and self.hass.states.get(target) is not None
                ):
                    await self.hass.services.async_call(
                        "notify",
                        "send_message",
                        {
                            "title": title,
                            "message": message,
                        },
                        blocking=True,
                        target={"entity_id": target},
                    )
                    delivered += 1
                    continue

                if "." in target:
                    domain, service = target.split(".", 1)
                    if self.hass.services.has_service(domain, service):
                        await self.hass.services.async_call(
                            domain,
                            service,
                            {
                                "title": title,
                                "message": message,
                                "data": {"tag": tag},
                            },
                            blocking=True,
                        )
                        delivered += 1
                        continue

                _LOGGER.error(
                    "Medication notification target is unavailable: %s",
                    target,
                )
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "Could not send medication notification %s to %s",
                    title,
                    target,
                )

        if delivered == 0 and targets:
            _LOGGER.error(
                "Medication notification was not delivered to any target: %s",
                ", ".join(str(target) for target in targets),
            )

    def _active_items(self, owner: str | None = None) -> list[dict[str, Any]]:
        return [
            item
            for item in self.items.values()
            if item.get("enabled", True)
            and (owner is None or item.get("owner") == owner)
        ]

    async def async_send_due_stock_warnings(
        self,
        now: datetime | None = None,
        startup: bool = False,
    ) -> None:
        now = dt_util.as_local(now or dt_util.now())
        monday = now.weekday() == 0
        for owner_id, owner in self.owners.items():
            if not owner.get("tracking_enabled", True):
                continue
            targets = self._owner_notification_targets(
                owner,
                "stock_notify_entities",
            )
            if not targets:
                continue
            for item in self._active_items(owner_id):
                if not self.item_low(item):
                    continue
                ordered = self.item_ordered(item)
                if ordered and not monday:
                    continue
                await self._send_notification(
                    targets,
                    owner.get("check_order_title")
                    if ordered
                    else owner.get("order_title"),
                    item["name"],
                    (
                        "medication_manager_check_order_"
                        if ordered
                        else "medication_manager_order_"
                    )
                    + item["id"],
                )

    def _refresh_low_cache(self) -> None:
        self._last_low = {
            item["id"]: self.item_low(item) for item in self._active_items()
        }

    async def _check_low_transition(self, item: dict[str, Any]) -> None:
        if not item.get("enabled", True):
            return
        current = self.item_low(item)
        previous = self._last_low.get(item["id"], current)
        self._last_low[item["id"]] = current
        if not current or previous:
            return
        owner = self.owners.get(str(item.get("owner")))
        if (
            owner is None
            or not owner.get("tracking_enabled", True)
        ):
            return
        targets = self._owner_notification_targets(
            owner,
            "stock_notify_entities",
        )
        if not targets:
            return
        await self._send_notification(
            targets,
            owner.get("order_title") or "Order Medication",
            item["name"],
            f"medication_manager_order_{item['id']}",
        )

    async def _clear_order_if_completed(self, item: dict[str, Any]) -> None:
        if not self.item_low(item) and self.item_ordered(item):
            await self.async_set_ordered(item["id"], False)

    async def async_clear_completed_orders(self) -> None:
        for item in self._active_items():
            await self._clear_order_if_completed(item)

    # ------------------------------------------------------------------
    # Integration-owned calendar generation
    # ------------------------------------------------------------------
    def calendar_events(
        self,
        owner_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return expanded events directly from stored item configuration."""
        start_local = dt_util.as_local(start_date)
        end_local = dt_util.as_local(end_date)
        timezone = start_local.tzinfo or dt_util.now().tzinfo
        events: list[CalendarEvent] = []

        for item in self._active_items(owner_id):
            order_date, run_out_date, _ = self._calculate_dates(item)
            for event_date, summary, uid_suffix in (
                (order_date, f"Order - {item['name']}", "order"),
                (run_out_date, f"Runs out - {item['name']}", "runout"),
            ):
                if event_date is None:
                    continue
                event_start = dt_util.start_of_local_day(event_date)
                event_end = dt_util.start_of_local_day(event_date + timedelta(days=1))
                if event_end <= start_local or event_start >= end_local:
                    continue
                events.append(
                    CalendarEvent(
                        start=event_date,
                        end=event_date + timedelta(days=1),
                        summary=summary,
                        description=(
                            f"Stock: {self._format_number(self.item_stock(item))} "
                            f"{item.get('unit', 'items')}. "
                            f"Schedule: {self._schedule_text(item)}."
                        ),
                        uid=f"msm:{item['id']}:{uid_suffix}:{event_date.isoformat()}",
                    )
                )

            if not self._date_is_active_range_possible(item):
                continue
            cursor = start_local.date() - timedelta(days=1)
            final_date = end_local.date() + timedelta(days=1)
            while cursor <= final_date:
                if self._date_is_active(item, cursor):
                    amount = float(item.get("usage_per_day", 0)) / max(
                        len(item.get("times", [])), 1
                    )
                    for time_text in item.get("times", []):
                        hour, minute = (int(part) for part in time_text.split(":"))
                        event_start = datetime.combine(
                            cursor,
                            time(hour, minute),
                            tzinfo=timezone,
                        )
                        event_end = event_start + timedelta(hours=1)
                        if event_end <= start_local or event_start >= end_local:
                            continue
                        title = (
                            item.get("reminder_title")
                            or self.owners.get(owner_id, {}).get(
                                "default_reminder_title", "Take Medication"
                            )
                        )
                        events.append(
                            CalendarEvent(
                                start=event_start,
                                end=event_end,
                                summary=f"{title} - {item['name']}",
                                description=(
                                    item.get("reminder_message")
                                    or f"Configured amount: {self._format_number(amount)} "
                                    f"{item.get('unit', 'items')}."
                                ),
                                uid=(
                                    f"msm:{item['id']}:take:"
                                    f"{cursor.isoformat()}:{time_text}"
                                ),
                            )
                        )
                cursor += timedelta(days=1)

        return sorted(events, key=lambda event: event.start_datetime_local)

    @staticmethod
    def _date_is_active_range_possible(item: dict[str, Any]) -> bool:
        return (
            item.get("enabled", True)
            and item.get("schedule_mode") != "manual"
            and float(item.get("usage_per_day", 0)) > 0
            and bool(item.get("times"))
        )

    def next_calendar_event(self, owner_id: str) -> CalendarEvent | None:
        now = dt_util.now()
        events = self.calendar_events(owner_id, now, now + timedelta(days=400))
        return next((event for event in events if event.end_datetime_local > now), None)

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_item_type(value: Any) -> str:
        """Normalize legacy custom items while preserving other item types."""
        item_type = str(value or "custom_med").strip().lower()
        if item_type == "custom":
            return "custom_med"
        return item_type or "custom_med"

    @classmethod
    def _item_category(cls, item_type: str) -> str:
        normalized = cls._normalize_item_type(item_type)
        return (
            "supply"
            if normalized in {"syringe", "catheter", "sheet", "custom_supply"}
            else "medication"
        )

    def _next_display_order(
        self,
        owner: str,
        item_type: str,
        *,
        exclude_item_id: str | None = None,
    ) -> int:
        category = self._item_category(item_type)
        existing = [
            int(item.get("display_order", 0))
            for item in self.items.values()
            if item.get("owner") == owner
            and item.get("id") != exclude_item_id
            and self._item_category(
                str(item.get("item_type", "custom_med"))
            )
            == category
        ]
        return (max(existing) if existing else 0) + 10

    def _normalize_display_orders(self) -> bool:
        """Keep ordering stable and independent inside each owner/category bucket."""
        changed = False
        buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in self.items.values():
            key = (
                str(item.get("owner", "")),
                self._item_category(str(item.get("item_type", "custom_med"))),
            )
            buckets.setdefault(key, []).append(item)

        for items in buckets.values():
            items.sort(
                key=lambda item: (
                    int(item.get("display_order", 1000)),
                    str(item.get("name", "")).lower(),
                    str(item.get("id", "")),
                )
            )
            for index, item in enumerate(items, start=1):
                display_order = index * 10
                if int(item.get("display_order", 0)) != display_order:
                    item["display_order"] = display_order
                    changed = True
        return changed

    def summary_items(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in sorted(
            self.items.values(),
            key=lambda value: (
                value.get("owner", ""),
                0
                if self._item_category(str(value.get("item_type", "custom_med")))
                == "medication"
                else 1,
                int(value.get("display_order", 1000)),
                value.get("name", "").lower(),
            ),
        ):
            stock = self.item_stock(item)
            threshold = self.item_threshold(item)
            order_date, run_out_date, days_remaining = self._calculate_dates(
                item, stock, threshold
            )
            result.append(
                {
                    "id": item["id"],
                    "owner": item["owner"],
                    "owner_name": self.owners.get(
                        item["owner"], {"name": item["owner"]}
                    )["name"],
                    "name": item["name"],
                    "item_type": self._normalize_item_type(
                        item.get("item_type", "custom_med")
                    ),
                    "category": self._item_category(
                        str(item.get("item_type", "custom_med"))
                    ),
                    "display_order": int(item.get("display_order", 1000)),
                    "unit": item.get("unit", "items"),
                    "icon": item.get("icon", "mdi:pill"),
                    "stock": stock,
                    "stock_text": self._format_number(stock),
                    "threshold": threshold,
                    "threshold_text": self._format_number(threshold),
                    "package_size": float(item.get("package_size", 0)),
                    "package_size_text": self._format_number(
                        float(item.get("package_size", 0))
                    ),
                    "usage_per_day": float(item.get("usage_per_day", 0)),
                    "schedule_mode": item.get("schedule_mode", "manual"),
                    "days": list(item.get("days", ALL_DAYS)),
                    "times": list(item.get("times", [])),
                    "interval_days": int(item.get("interval_days", 1)),
                    "start_date": item.get("start_date", ""),
                    "schedule_text": self._schedule_text(item),
                    "manual": (
                        item.get("schedule_mode") == "manual"
                        or float(item.get("usage_per_day", 0)) <= 0
                        or not item.get("times")
                    ),
                    "low": stock <= threshold,
                    "ordered": self.item_ordered(item),
                    "days_remaining": days_remaining,
                    "order_date": order_date.isoformat() if order_date else None,
                    "run_out_date": run_out_date.isoformat() if run_out_date else None,
                    "enabled": bool(item.get("enabled", True)),
                    "reminder_enabled": bool(item.get("reminder_enabled", False)),
                    "reminder_title": item.get("reminder_title", ""),
                    "reminder_message": item.get("reminder_message", ""),
                    "product_url": item.get("product_url", ""),
                }
            )
        return result

    @staticmethod
    def _format_number(value: float) -> str:
        if float(value).is_integer():
            return str(int(value))
        return f"{value:.3f}".rstrip("0").rstrip(".")
