"""Constants for Medication Stock Manager."""

from __future__ import annotations

DOMAIN = "medication_stock_manager"
VERSION = "1.4.0"
PLATFORMS = ["sensor", "number", "switch", "button", "calendar"]

STORAGE_KEY = f"{DOMAIN}.items"
STORAGE_VERSION = 1

DATA_MANAGER = "manager"
SUMMARY_ENTITY_ID = "sensor.medication_stock_manager"

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
ALL_DAYS = list(WEEKDAYS)
DEFAULT_OWNER_ID = "default"

FRONTEND_PATH = "/medication-stock-manager/medication-stock-manager-card.js"
FRONTEND_URL = f"{FRONTEND_PATH}?v={VERSION}"

DEFAULT_UNIT_TYPES = {
    "capsule": "capsules",
    "tablet": "tablets",
    "chewable_tablet": "chewable tablets",
    "plaster": "plasters",
    "sachet": "sachets",
    "syringe": "syringes",
    "catheter": "catheters",
    "sheet": "sheets",
    "custom": "items",
}

PANEL_URL_PATH = "medication-stock-manager"
PANEL_COMPONENT_NAME = "medication-stock-manager"
PANEL_TITLE = "Medication Stock"
PANEL_ICON = "mdi:medical-bag"
DEFAULT_SHOW_SIDEBAR_PANEL = True

DEFAULT_PANEL_REQUIRE_ADMIN = True
DEFAULT_PANEL_TITLE = PANEL_TITLE
DEFAULT_PANEL_ICON = PANEL_ICON
