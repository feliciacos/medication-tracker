#!/usr/bin/env python3
"""Validate the Medication Stock Manager repository before release."""

from __future__ import annotations

import json
import py_compile
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "medication_stock_manager"

REQUIRED_ROOT = (
    ".gitattributes",
    ".gitignore",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "hacs.json",
)
REQUIRED_RUNTIME = (
    "__init__.py",
    "button.py",
    "calendar.py",
    "config_flow.py",
    "const.py",
    "entity.py",
    "manager.py",
    "manifest.json",
    "number.py",
    "sensor.py",
    "services.yaml",
    "strings.json",
    "switch.py",
    "translations/en.json",
    "frontend/medication-stock-manager-card.js",
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        fail(f"Invalid JSON: {path.relative_to(ROOT)}: {err}")


def extract(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        fail(f"Could not find {label}")
    return match.group(1)


def main() -> int:
    for relative in REQUIRED_ROOT:
        if not (ROOT / relative).is_file():
            fail(f"Missing required root file: {relative}")

    custom_components = ROOT / "custom_components"
    component_dirs = sorted(
        path.name for path in custom_components.iterdir() if path.is_dir()
    )
    if component_dirs != ["medication_stock_manager"]:
        fail(
            "custom_components must contain only medication_stock_manager; "
            f"found {component_dirs}"
        )

    for relative in REQUIRED_RUNTIME:
        if not (INTEGRATION / relative).is_file():
            fail(
                "Missing runtime file: "
                f"custom_components/medication_stock_manager/{relative}"
            )

    hacs = read_json(ROOT / "hacs.json")
    manifest = read_json(INTEGRATION / "manifest.json")
    read_json(INTEGRATION / "strings.json")
    read_json(INTEGRATION / "translations/en.json")

    if manifest.get("domain") != "medication_stock_manager":
        fail("manifest domain changed")
    if "http" not in manifest.get("dependencies", []):
        fail("manifest must include the http dependency")
    if not manifest.get("config_flow"):
        fail("manifest must keep config_flow enabled")
    if hacs.get("content_in_root") is not False:
        fail("hacs.json content_in_root must be false")

    manifest_version = str(manifest.get("version", ""))
    const_text = (INTEGRATION / "const.py").read_text(encoding="utf-8")
    frontend_text = (
        INTEGRATION / "frontend/medication-stock-manager-card.js"
    ).read_text(encoding="utf-8")
    const_version = extract(
        r'^VERSION\s*=\s*["\']([^"\']+)["\']',
        const_text,
        "const.py VERSION",
    )
    frontend_version = extract(
        r'^const MSM_CARD_VERSION\s*=\s*["\']([^"\']+)["\']',
        frontend_text,
        "frontend MSM_CARD_VERSION",
    )
    if len({manifest_version, const_version, frontend_version}) != 1:
        fail(
            "Version mismatch: "
            f"manifest={manifest_version}, const={const_version}, "
            f"frontend={frontend_version}"
        )

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{manifest_version}]" not in changelog:
        fail(f"CHANGELOG.md has no {manifest_version} release section")

    init_text = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    if "config_entry_only_config_schema(DOMAIN)" not in init_text:
        fail("config-entry-only CONFIG_SCHEMA is missing")
    if '("move_item", move_item, MOVE_ITEM_SCHEMA)' not in init_text:
        fail("move_item service registration is missing")
    if "async def async_move_item" not in (
        INTEGRATION / "manager.py"
    ).read_text(encoding="utf-8"):
        fail("manager async_move_item implementation is missing")
    for marker in ("ha-icon-picker", "Medication", "Supplies", "move-item"):
        if marker not in frontend_text:
            fail(f"Frontend feature marker missing: {marker}")

    for path in sorted(INTEGRATION.rglob("*.py")):
        py_compile.compile(str(path), doraise=True)

    node = shutil.which("node")
    if node:
        subprocess.run(
            [
                node,
                "--check",
                str(INTEGRATION / "frontend/medication-stock-manager-card.js"),
            ],
            check=True,
        )
    else:
        print("Warning: node is unavailable; skipped JavaScript syntax check")

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        print("Warning: PyYAML is unavailable; skipped YAML parser check")
    else:
        for path in sorted(ROOT.rglob("*.yaml")):
            if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
                continue
            with path.open("r", encoding="utf-8") as handle:
                yaml.safe_load(handle)

    print(
        "Repository validation passed for Medication Stock Manager "
        f"{manifest_version}."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        RuntimeError,
        subprocess.CalledProcessError,
        py_compile.PyCompileError,
    ) as err:
        print(f"Validation failed: {err}", file=sys.stderr)
        raise SystemExit(1) from err
