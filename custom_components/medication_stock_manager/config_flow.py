"""Config flow for Medication Stock Manager."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    DEFAULT_PANEL_ICON,
    DEFAULT_PANEL_REQUIRE_ADMIN,
    DEFAULT_PANEL_TITLE,
    DEFAULT_SHOW_SIDEBAR_PANEL,
    DOMAIN,
)

SETUP_CREATE_OWNER = "create_owner"
SETUP_EMPTY = "empty"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one local Medication Stock Manager instance."""

    VERSION = 2
    MINOR_VERSION = 4

    def __init__(self) -> None:
        self._setup_mode = SETUP_CREATE_OWNER
        self._show_sidebar_panel = DEFAULT_SHOW_SIDEBAR_PANEL
        self._sidebar_title = DEFAULT_PANEL_TITLE
        self._sidebar_icon = DEFAULT_PANEL_ICON
        self._sidebar_require_admin = DEFAULT_PANEL_REQUIRE_ADMIN

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Choose whether to create the first owner during setup."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            self._setup_mode = user_input["setup_mode"]
            self._show_sidebar_panel = bool(
                user_input.get(
                    "show_sidebar_panel",
                    DEFAULT_SHOW_SIDEBAR_PANEL,
                )
            )
            self._sidebar_title = (
                str(
                    user_input.get(
                        "sidebar_title",
                        DEFAULT_PANEL_TITLE,
                    )
                ).strip()
                or DEFAULT_PANEL_TITLE
            )
            self._sidebar_icon = (
                str(
                    user_input.get(
                        "sidebar_icon",
                        DEFAULT_PANEL_ICON,
                    )
                ).strip()
                or DEFAULT_PANEL_ICON
            )
            self._sidebar_require_admin = bool(
                user_input.get(
                    "sidebar_require_admin",
                    DEFAULT_PANEL_REQUIRE_ADMIN,
                )
            )
            if self._setup_mode == SETUP_EMPTY:
                return self.async_create_entry(
                    title="Medication Stock Manager",
                    data={
                        "bootstrap_complete": True,
                        **self._sidebar_data(),
                    },
                )
            return await self.async_step_owner()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "setup_mode",
                        default=SETUP_CREATE_OWNER,
                    ): vol.In(
                        {
                            SETUP_CREATE_OWNER: "Create the first owner now",
                            SETUP_EMPTY: "Start empty and create owners from the card",
                        }
                    ),
                    vol.Required(
                        "show_sidebar_panel",
                        default=DEFAULT_SHOW_SIDEBAR_PANEL,
                    ): bool,
                    vol.Optional(
                        "sidebar_title",
                        default=DEFAULT_PANEL_TITLE,
                    ): str,
                    vol.Optional(
                        "sidebar_icon",
                        default=DEFAULT_PANEL_ICON,
                    ): str,
                    vol.Required(
                        "sidebar_require_admin",
                        default=DEFAULT_PANEL_REQUIRE_ADMIN,
                    ): bool,
                }
            ),
        )

    async def async_step_owner(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Collect the minimal first-owner settings."""
        if user_input is not None:
            owner = {
                **user_input,
                "reminder_notify_entities": self._split_entities(
                    user_input.get("reminder_notify_entities", "")
                ),
                "stock_notify_entities": self._split_entities(
                    user_input.get("stock_notify_entities", "")
                ),
            }
            return self.async_create_entry(
                title="Medication Stock Manager",
                data={
                    "initial_owner": owner,
                    "bootstrap_complete": False,
                    **self._sidebar_data(),
                },
            )

        return self.async_show_form(
            step_id="owner",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Optional("owner_id", default=""): str,
                    vol.Optional("person_entity", default=""): str,
                    vol.Optional("auto_create_person", default=True): bool,
                    vol.Optional("auto_detect_notify", default=True): bool,
                    vol.Optional(
                        "reminder_notify_entities", default=""
                    ): str,
                    vol.Optional(
                        "stock_notify_entities", default=""
                    ): str,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "MedicationStockManagerOptionsFlow":
        """Create the integration options flow."""
        return MedicationStockManagerOptionsFlow()

    def _sidebar_data(self) -> dict[str, Any]:
        """Return normalized sidebar settings for the config entry."""
        return {
            "show_sidebar_panel": self._show_sidebar_panel,
            "sidebar_title": self._sidebar_title,
            "sidebar_icon": self._sidebar_icon,
            "sidebar_require_admin": self._sidebar_require_admin,
        }

    @staticmethod
    def _split_entities(value: Any) -> list[str]:
        """Split comma-separated entity IDs from a config-flow text field."""
        return [
            item.strip()
            for item in str(value or "").split(",")
            if item.strip()
        ]


class MedicationStockManagerOptionsFlow(OptionsFlowWithReload):
    """Configure optional Medication Stock Manager UI features."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage sidebar-panel visibility."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        def current_value(key: str, default: Any) -> Any:
            return self.config_entry.options.get(
                key,
                self.config_entry.data.get(key, default),
            )

        schema = vol.Schema(
            {
                vol.Required(
                    "show_sidebar_panel",
                    default=current_value(
                        "show_sidebar_panel",
                        DEFAULT_SHOW_SIDEBAR_PANEL,
                    ),
                ): bool,
                vol.Optional(
                    "sidebar_title",
                    default=current_value(
                        "sidebar_title",
                        DEFAULT_PANEL_TITLE,
                    ),
                ): str,
                vol.Optional(
                    "sidebar_icon",
                    default=current_value(
                        "sidebar_icon",
                        DEFAULT_PANEL_ICON,
                    ),
                ): str,
                vol.Required(
                    "sidebar_require_admin",
                    default=current_value(
                        "sidebar_require_admin",
                        DEFAULT_PANEL_REQUIRE_ADMIN,
                    ),
                ): bool,
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
