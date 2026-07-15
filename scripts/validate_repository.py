#!/usr/bin/env python3
"""Validate the Medication Stock Manager HACS repository structure."""

from __future__ import annotations

from pathlib import Path
import ast
import json
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "medication_stock_manager"
EXPECTED_VERSION = "1.4.2"
INTEGRATION = ROOT / "custom_components" / DOMAIN


def fail(message: str) -> None:
    raise SystemExit(message)


children = [path for path in (ROOT / "custom_components").iterdir() if path.is_dir()]
if children != [INTEGRATION]:
    fail(f"Expected exactly one integration directory: {INTEGRATION}")

manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
if manifest.get("domain") != DOMAIN:
    fail("manifest domain does not match integration directory")
if manifest.get("version") != EXPECTED_VERSION:
    fail("manifest version is not synchronized")
if not manifest.get("documentation") or not manifest.get("issue_tracker"):
    fail("manifest documentation or issue tracker is missing")
if "http" not in manifest.get("dependencies", []):
    fail("manifest must declare the http dependency")

const_text = (INTEGRATION / "const.py").read_text(encoding="utf-8")
if f'VERSION = "{EXPECTED_VERSION}"' not in const_text:
    fail("const.py version is not synchronized")

frontend = INTEGRATION / "frontend/medication-stock-manager-card.js"
frontend_text = frontend.read_text(encoding="utf-8")
if f'MSM_CARD_VERSION = "{EXPECTED_VERSION}"' not in frontend_text:
    fail("frontend version is not synchronized")

init_text = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
if "CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)" not in init_text:
    fail("config-entry-only CONFIG_SCHEMA declaration is missing")

for path in INTEGRATION.rglob("*.py"):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

for path in ROOT.rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))
for path in list(ROOT.rglob("*.yaml")) + list(ROOT.rglob("*.yml")):
    yaml.safe_load(path.read_text(encoding="utf-8"))

for required in (
    ROOT / "hacs.json",
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / "CHANGELOG.md",
    INTEGRATION / "config_flow.py",
    INTEGRATION / "strings.json",
    INTEGRATION / "translations/en.json",
    INTEGRATION / "brand/icon.png",
    INTEGRATION / "brand/logo.png",
    frontend,
):
    if not required.is_file() or required.stat().st_size == 0:
        fail(f"Missing required file: {required}")

for path in ROOT.rglob("*"):
    if "__pycache__" in path.parts or path.suffix == ".pyc":
        fail(f"Compiled Python artifact found: {path}")

result = subprocess.run(
    ["node", "--check", str(frontend)],
    capture_output=True,
    text=True,
    check=False,
)
if result.returncode:
    fail(result.stderr)

print("Repository structure and local syntax validation passed.")
