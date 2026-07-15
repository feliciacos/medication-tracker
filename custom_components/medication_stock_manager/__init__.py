"""Medication Stock Manager integration setup."""

from __future__ import annotations

from pathlib import Path
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.frontend import (
    add_extra_js_url,
    async_panel_exists,
    async_register_built_in_panel,
    async_remove_panel,
    remove_extra_js_url,
)
from homeassistant.components.lovelace.const import (
    CONF_RESOURCE_TYPE_WS,
    LOVELACE_DATA,
)
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ID,
    CONF_NAME,
    CONF_TYPE,
    CONF_URL,
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store

from .const import (
    DATA_MANAGER,
    DOMAIN,
    DEFAULT_PANEL_ICON,
    DEFAULT_PANEL_REQUIRE_ADMIN,
    DEFAULT_PANEL_TITLE,
    DEFAULT_SHOW_SIDEBAR_PANEL,
    FRONTEND_PATH,
    FRONTEND_URL,
    PANEL_COMPONENT_NAME,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
    PLATFORMS,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .manager import MedicationStockManager

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

ADD_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional("owner", default=""): cv.string,
        vol.Optional("item_type", default="custom_med"): cv.string,
        vol.Optional("unit", default="items"): cv.string,
        vol.Optional("icon", default="mdi:pill"): cv.string,
        vol.Optional("stock", default=0): vol.Coerce(float),
        vol.Optional("threshold", default=0): vol.Coerce(float),
        vol.Optional("package_size", default=0): vol.Coerce(float),
        vol.Optional("usage_per_day", default=0): vol.Coerce(float),
        vol.Optional("schedule_mode", default="manual"): cv.string,
        vol.Optional("days", default=[]): vol.Any(list, cv.string),
        vol.Optional("times", default=[]): vol.Any(list, cv.string),
        vol.Optional("interval_days", default=1): vol.Coerce(int),
        vol.Optional("start_date", default=""): cv.string,
        vol.Optional("enabled", default=True): cv.boolean,
        vol.Optional("reminder_enabled", default=False): cv.boolean,
        vol.Optional("reminder_title", default=""): cv.string,
        vol.Optional("reminder_message", default=""): cv.string,
        vol.Optional("product_url", default=""): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

ADD_OWNER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional("owner_id", default=""): cv.string,
        vol.Optional("person_entity", default=""): cv.string,
        vol.Optional("auto_create_person", default=True): cv.boolean,
        vol.Optional("auto_detect_notify", default=True): cv.boolean,
        vol.Optional("reminder_notify_entities", default=[]): vol.Any(list, cv.string),
        vol.Optional("stock_notify_entities", default=[]): vol.Any(list, cv.string),
        vol.Optional("tracking_enabled", default=True): cv.boolean,
        vol.Optional("reminders_enabled", default=True): cv.boolean,
        vol.Optional("default_reminder_title", default="Medication Reminder"): cv.string,
        vol.Optional("order_title", default="Order Medication"): cv.string,
        vol.Optional("check_order_title", default="Check Medication Order"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)
UPDATE_OWNER_SCHEMA = vol.Schema(
    {vol.Required("owner_id"): cv.string}, extra=vol.ALLOW_EXTRA
)
OWNER_SCHEMA = vol.Schema({vol.Required("owner_id"): cv.string})
UPDATE_ITEM_SCHEMA = vol.Schema(
    {vol.Required("item_id"): cv.string}, extra=vol.ALLOW_EXTRA
)
ITEM_SCHEMA = vol.Schema({vol.Required("item_id"): cv.string})
VALUE_SCHEMA = vol.Schema(
    {
        vol.Required("item_id"): cv.string,
        vol.Required("value"): vol.Coerce(float),
    }
)
ADJUST_SCHEMA = vol.Schema(
    {
        vol.Required("item_id"): cv.string,
        vol.Required("amount"): vol.Coerce(float),
    }
)
ORDERED_SCHEMA = vol.Schema(
    {
        vol.Required("item_id"): cv.string,
        vol.Required("ordered"): cv.boolean,
    }
)
SIDEBAR_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required("show_sidebar_panel"): cv.boolean,
        vol.Optional("sidebar_title", default=DEFAULT_PANEL_TITLE): cv.string,
        vol.Optional("sidebar_icon", default=DEFAULT_PANEL_ICON): cv.string,
        vol.Optional(
            "sidebar_require_admin",
            default=DEFAULT_PANEL_REQUIRE_ADMIN,
        ): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up global services and the integration-owned frontend."""
    hass.data.setdefault(DOMAIN, {})
    _register_services(hass)
    await _register_frontend(hass)

    # Run one more resource check after Home Assistant is fully started.
    # This covers installations where Lovelace finishes initializing after
    # the custom integration component itself.
    if not hass.is_running:
        @callback
        def _frontend_startup_retry(_: Any) -> None:
            hass.async_create_task(_register_frontend(hass))

        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            _frontend_startup_retry,
        )

    return True


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Migrate config entries created by earlier project versions."""
    if entry.version > 2:
        _LOGGER.error(
            "Cannot migrate Medication Stock Manager entry version %s",
            entry.version,
        )
        return False

    data = dict(entry.data)

    if entry.version == 1:
        # v1 entries did not contain setup-wizard bookkeeping. Existing
        # storage already contains their owner/item data, so mark them as
        # bootstrapped unless a pending initial owner is explicitly present.
        data.setdefault(
            "bootstrap_complete",
            not bool(data.get("initial_owner")),
        )

    data.setdefault(
        "show_sidebar_panel",
        DEFAULT_SHOW_SIDEBAR_PANEL,
    )
    data.setdefault("sidebar_title", DEFAULT_PANEL_TITLE)
    data.setdefault("sidebar_icon", DEFAULT_PANEL_ICON)
    data.setdefault(
        "sidebar_require_admin",
        DEFAULT_PANEL_REQUIRE_ADMIN,
    )
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        version=2,
        minor_version=4,
    )
    _LOGGER.info(
        "Migrated Medication Stock Manager config entry to 2.4"
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one self-contained manager config entry."""
    await _register_frontend(hass)
    _sync_sidebar_panel(hass, entry)
    manager = MedicationStockManager(hass, entry.entry_id)
    await manager.async_load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_MANAGER: manager}

    await _bootstrap_initial_owner(hass, entry, manager)
    await manager.async_ensure_devices()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await manager.async_start()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove integration-owned persistent data and frontend resource."""
    await Store[dict[str, Any]](
        hass,
        STORAGE_VERSION,
        STORAGE_KEY,
    ).async_remove()
    await _async_remove_lovelace_resource(hass)
    if async_panel_exists(hass, PANEL_URL_PATH):
        async_remove_panel(
            hass,
            PANEL_URL_PATH,
            warn_if_unknown=False,
        )
    if hass.data.get(DOMAIN, {}).get("frontend_module_added"):
        try:
            remove_extra_js_url(hass, FRONTEND_URL)
        except (KeyError, ValueError):
            pass
        hass.data[DOMAIN].pop("frontend_module_added", None)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload all integration-owned platforms."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unloaded:
        return False
    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data:
        await entry_data[DATA_MANAGER].async_stop()
    # Keep the frontend module registered during integration reloads.
    # Removing it here can leave dashboards with an undefined custom element
    # while the config entry is being migrated or reloaded. It is removed only
    # when the integration entry itself is deleted.
    return True


def _entry_setting(
    entry: ConfigEntry,
    key: str,
    default: Any,
) -> Any:
    """Return an option value, falling back to setup data."""
    return entry.options.get(key, entry.data.get(key, default))


def _sidebar_panel_enabled(entry: ConfigEntry) -> bool:
    """Return whether the optional configuration panel is enabled."""
    return bool(
        _entry_setting(
            entry,
            "show_sidebar_panel",
            DEFAULT_SHOW_SIDEBAR_PANEL,
        )
    )


def _sync_sidebar_panel(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Create, update, or remove the optional sidebar configuration page."""
    enabled = _sidebar_panel_enabled(entry)
    exists = async_panel_exists(hass, PANEL_URL_PATH)

    if not enabled:
        if exists:
            async_remove_panel(
                hass,
                PANEL_URL_PATH,
                warn_if_unknown=False,
            )
        return

    sidebar_title = (
        str(
            _entry_setting(
                entry,
                "sidebar_title",
                DEFAULT_PANEL_TITLE,
            )
        ).strip()
        or DEFAULT_PANEL_TITLE
    )
    sidebar_icon = (
        str(
            _entry_setting(
                entry,
                "sidebar_icon",
                DEFAULT_PANEL_ICON,
            )
        ).strip()
        or DEFAULT_PANEL_ICON
    )
    require_admin = bool(
        _entry_setting(
            entry,
            "sidebar_require_admin",
            DEFAULT_PANEL_REQUIRE_ADMIN,
        )
    )

    # Built-in panel components are resolved by the frontend as:
    #   component_name "medication-stock-manager"
    #   -> custom element "ha-panel-medication-stock-manager"
    # The frontend module defines that exact element and legacy aliases.
    async_register_built_in_panel(
        hass,
        PANEL_COMPONENT_NAME,
        sidebar_title=sidebar_title,
        sidebar_icon=sidebar_icon,
        sidebar_default_visible=True,
        frontend_url_path=PANEL_URL_PATH,
        config={
            "domain": DOMAIN,
            "entry_id": entry.entry_id,
            "sidebar_title": sidebar_title,
            "sidebar_icon": sidebar_icon,
        },
        require_admin=require_admin,
        update=exists,
        config_panel_domain=DOMAIN,
        show_in_sidebar=True,
    )
    _LOGGER.info(
        "Medication Stock Manager sidebar panel registered at /%s "
        "with component %s",
        PANEL_URL_PATH,
        PANEL_COMPONENT_NAME,
    )


async def _register_frontend(hass: HomeAssistant) -> None:
    """Serve the card and self-heal all frontend registration paths."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    if not domain_data.get("frontend_static_path_registered"):
        frontend_file = (
            Path(__file__).parent
            / "frontend"
            / "medication-stock-manager-card.js"
        )
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_PATH, str(frontend_file), False)]
            )
        except RuntimeError:
            # A reload can encounter the route registered by the earlier
            # instance. The existing path is still valid.
            _LOGGER.debug("Frontend static path was already registered")
        domain_data["frontend_static_path_registered"] = True

    if not domain_data.get("frontend_module_added"):
        add_extra_js_url(hass, FRONTEND_URL)
        domain_data["frontend_module_added"] = True

    # Recheck the Lovelace resource on every setup/reload. The storage entry
    # can be removed by a user or can be unavailable during early startup.
    try:
        await _async_ensure_lovelace_resource(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.exception(
            "Could not ensure Medication Stock Manager Lovelace resource; "
            "the frontend extra-module registration remains active"
        )
    else:
        domain_data["lovelace_resource_registered"] = True

    domain_data["frontend_registered"] = True
    _LOGGER.info("Medication Stock Manager frontend registered: %s", FRONTEND_URL)


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Create one versioned module resource without touching other resources."""
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        _LOGGER.warning(
            "Lovelace data is unavailable; relying on the extra module URL"
        )
        return

    resources = lovelace_data.resources
    if not isinstance(resources, ResourceStorageCollection):
        _LOGGER.info(
            "Lovelace resources use YAML mode; relying on the extra module URL"
        )
        return

    # The storage collection is lazy-loaded. Load it explicitly before
    # inspecting or modifying resources. This avoids replacing an unloaded
    # collection and works across Home Assistant versions with either the
    # guarded or unguarded collection implementation.
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True
    await resources.async_get_info()
    matches = [
        item
        for item in resources.async_items()
        if "medication-stock-manager-card.js" in str(item.get(CONF_URL, ""))
    ]

    if matches:
        primary = matches[0]
        if (
            primary.get(CONF_URL) != FRONTEND_URL
            or primary.get(CONF_TYPE) != "module"
        ):
            await resources.async_update_item(
                primary[CONF_ID],
                {
                    CONF_RESOURCE_TYPE_WS: "module",
                    CONF_URL: FRONTEND_URL,
                },
            )
        for duplicate in matches[1:]:
            await resources.async_delete_item(duplicate[CONF_ID])
        _LOGGER.debug("Updated existing Lovelace resource %s", FRONTEND_URL)
        return

    await resources.async_create_item(
        {
            CONF_RESOURCE_TYPE_WS: "module",
            CONF_URL: FRONTEND_URL,
        }
    )
    _LOGGER.info("Created Lovelace module resource %s", FRONTEND_URL)


async def _async_remove_lovelace_resource(hass: HomeAssistant) -> None:
    """Remove only Medication Stock Manager Lovelace resources."""
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return
    resources = lovelace_data.resources
    if not isinstance(resources, ResourceStorageCollection):
        return
    await resources.async_get_info()
    for item in list(resources.async_items()):
        if "medication-stock-manager-card.js" in str(item.get(CONF_URL, "")):
            await resources.async_delete_item(item[CONF_ID])


async def _bootstrap_initial_owner(
    hass: HomeAssistant,
    entry: ConfigEntry,
    manager: MedicationStockManager,
) -> None:
    """Create the first owner selected in the setup flow exactly once."""
    if entry.data.get("bootstrap_complete"):
        return

    initial_owner = entry.data.get("initial_owner")
    if initial_owner and not manager.owners:
        await manager.async_add_owner(dict(initial_owner))

    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, "bootstrap_complete": True},
    )


def _get_entry(hass: HomeAssistant) -> ConfigEntry:
    """Return the single Medication Stock Manager config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError(
            "Medication Stock Manager is not configured"
        )
    return entries[0]


def _get_manager(hass: HomeAssistant) -> MedicationStockManager:
    for value in hass.data.get(DOMAIN, {}).values():
        if isinstance(value, dict) and DATA_MANAGER in value:
            return value[DATA_MANAGER]
    raise HomeAssistantError("Medication Stock Manager is not loaded")


def _register_services(hass: HomeAssistant) -> None:
    if hass.data[DOMAIN].get("services_registered"):
        return

    async def invoke(method: str, call: ServiceCall, *args: Any) -> None:
        try:
            await getattr(_get_manager(hass), method)(*args)
        except (TypeError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err

    async def add_owner(call: ServiceCall) -> None:
        await invoke("async_add_owner", call, dict(call.data))

    async def update_owner(call: ServiceCall) -> None:
        data = dict(call.data)
        owner_id = data.pop("owner_id")
        await invoke("async_update_owner", call, owner_id, data)

    async def remove_owner(call: ServiceCall) -> None:
        await invoke("async_remove_owner", call, call.data["owner_id"])

    async def clear_all_items(call: ServiceCall) -> None:
        await invoke("async_clear_all_items", call)

    async def add_item(call: ServiceCall) -> None:
        await invoke("async_add_item", call, dict(call.data))

    async def update_item(call: ServiceCall) -> None:
        data = dict(call.data)
        item_id = data.pop("item_id")
        await invoke("async_update_item", call, item_id, data)

    async def remove_item(call: ServiceCall) -> None:
        await invoke("async_remove_item", call, call.data["item_id"])

    async def set_stock(call: ServiceCall) -> None:
        await invoke("async_set_stock", call, call.data["item_id"], call.data["value"])

    async def set_threshold(call: ServiceCall) -> None:
        await invoke(
            "async_set_threshold", call, call.data["item_id"], call.data["value"]
        )

    async def adjust_stock(call: ServiceCall) -> None:
        await invoke(
            "async_adjust_stock", call, call.data["item_id"], call.data["amount"]
        )

    async def receive_box(call: ServiceCall) -> None:
        await invoke("async_receive_box", call, call.data["item_id"])

    async def set_ordered(call: ServiceCall) -> None:
        await invoke(
            "async_set_ordered", call, call.data["item_id"], call.data["ordered"]
        )

    async def process_now(call: ServiceCall) -> None:
        await invoke("async_process_time", call)

    async def set_sidebar_options(call: ServiceCall) -> None:
        entry = _get_entry(hass)
        options = {
            **entry.options,
            "show_sidebar_panel": bool(
                call.data["show_sidebar_panel"]
            ),
            "sidebar_title": (
                str(
                    call.data.get(
                        "sidebar_title",
                        DEFAULT_PANEL_TITLE,
                    )
                ).strip()
                or DEFAULT_PANEL_TITLE
            ),
            "sidebar_icon": (
                str(
                    call.data.get(
                        "sidebar_icon",
                        DEFAULT_PANEL_ICON,
                    )
                ).strip()
                or DEFAULT_PANEL_ICON
            ),
            "sidebar_require_admin": bool(
                call.data.get(
                    "sidebar_require_admin",
                    DEFAULT_PANEL_REQUIRE_ADMIN,
                )
            ),
        }
        hass.config_entries.async_update_entry(
            entry,
            options=options,
        )
        await hass.config_entries.async_reload(entry.entry_id)

    registrations = (
        ("add_owner", add_owner, ADD_OWNER_SCHEMA),
        ("update_owner", update_owner, UPDATE_OWNER_SCHEMA),
        ("remove_owner", remove_owner, OWNER_SCHEMA),
        ("clear_all_items", clear_all_items, None),
        ("restore_defaults", clear_all_items, None),
        ("add_item", add_item, ADD_ITEM_SCHEMA),
        ("update_item", update_item, UPDATE_ITEM_SCHEMA),
        ("remove_item", remove_item, ITEM_SCHEMA),
        ("set_stock", set_stock, VALUE_SCHEMA),
        ("set_threshold", set_threshold, VALUE_SCHEMA),
        ("adjust_stock", adjust_stock, ADJUST_SCHEMA),
        ("receive_box", receive_box, ITEM_SCHEMA),
        ("set_ordered", set_ordered, ORDERED_SCHEMA),
        ("process_now", process_now, None),
        (
            "set_sidebar_options",
            set_sidebar_options,
            SIDEBAR_OPTIONS_SCHEMA,
        ),
    )
    for service, handler, schema in registrations:
        if schema is None:
            hass.services.async_register(DOMAIN, service, handler)
        else:
            hass.services.async_register(DOMAIN, service, handler, schema=schema)
    hass.data[DOMAIN]["services_registered"] = True
