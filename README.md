# Medication Stock Manager

[![Validate](https://github.com/feliciacos/medication-tracker/actions/workflows/validate.yml/badge.svg)](https://github.com/feliciacos/medication-tracker/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/feliciacos/medication-tracker)](https://github.com/feliciacos/medication-tracker/releases)
[![HACS custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)

Medication Stock Manager is a self-contained Home Assistant custom integration
for medication schedules, medical-supply stock, recurring usage, owner profiles,
mobile reminders, order warnings, integration-owned calendars, and dashboard
controls.

The integration does not require packages, YAML automations, input helpers,
Local Calendar, a `/config/www` file, or a normal `configuration.yaml` entry.
It stores its owner and item data in Home Assistant storage and creates its own
entities, devices, calendars, services, frontend module, custom cards, and
optional sidebar page.

## Features

- Multiple owner profiles with optional Home Assistant Person association.
- Medication and medical-supply items with custom units and icons.
- Manual, daily, selected-weekday, and every-X-days schedules.
- Automatic stock deduction at configured times.
- Configurable stock, warning threshold, package size, and usage values.
- Order-date and run-out-date calculation.
- Immediate low-stock warnings, recurring order reminders, and weekly
  check-order reminders.
- Mobile notification target detection from linked Person/device entities when
  Home Assistant exposes that relationship.
- Integration-owned read-only calendars for scheduled use, order dates, and
  run-out dates.
- Integration-owned sensors, numbers, switches, buttons, calendars, and devices.
- Bundled frontend card with stock tables, stock buttons, item configuration,
  owner management, item creation, sidebar settings, and item details.
- Optional configurable Home Assistant sidebar panel.
- UI config flow, options flow, config-entry migration, unload support, and
  removal cleanup.
- No personal medication defaults in runtime code.

## Requirements

- Home Assistant **2026.3.0 or newer**.
- HACS is optional but recommended for installation and updates.
- JavaScript must be enabled in the browser for the bundled frontend card and
  sidebar panel.
- The personalized dashboard examples may use third-party cards such as Bubble
  Card; the integration and its generic setup page do not depend on those
  examples.

## HACS installation

1. Publish or push this repository to GitHub.
2. Open **HACS** in Home Assistant.
3. Open the three-dot menu in the upper-right corner.
4. Select **Custom repositories**.
5. Add this repository URL:

   ```text
   https://github.com/feliciacos/medication-tracker
   ```

6. Choose **Integration** as the category.
7. Select **Add**, open **Medication Stock Manager**, and choose **Download**.
8. Restart Home Assistant.
9. Open **Settings -> Devices & services -> Add integration**.
10. Search for **Medication Stock Manager** and complete the setup flow.

The integration serves and registers its frontend module from inside the
installed custom-component directory. Do not add a separate `/local/...`
Lovelace resource.

## Manual installation

1. Download or clone this repository.
2. Copy this folder:

   ```text
   custom_components/medication_stock_manager/
   ```

   into the Home Assistant configuration directory so the final path is:

   ```text
   /config/custom_components/medication_stock_manager/
   ```

3. Restart Home Assistant.
4. Add **Medication Stock Manager** through **Settings -> Devices & services**.

Do not accidentally create this nested path:

```text
/config/custom_components/custom_components/medication_stock_manager/
```

Manual installations do not receive automatic update notifications. HACS is
recommended for ongoing updates.

## Initial configuration

The setup flow can start empty or create the first owner immediately. It also
configures the optional sidebar page, including its title, icon, visibility,
and administrator-only setting.

After setup, use either the sidebar page or a normal dashboard card to:

1. Create or edit owners.
2. Create medication or medical-supply items.
3. Configure schedules, stock values, reminders, and warning thresholds.
4. Use the stock buttons to receive a box, mark an order, or adjust stock.

Useful card examples are available in
[`docs/CARD_CONFIGURATION_EXAMPLES.md`](docs/CARD_CONFIGURATION_EXAMPLES.md).
Example dashboard views are in [`examples/dashboards`](examples/dashboards).

No `configuration.yaml` entry is needed for normal operation.

## Updating

### HACS

1. Open HACS and select **Medication Stock Manager**.
2. Install the available update.
3. Restart Home Assistant.
4. Fully reopen or hard-refresh the browser tab so the new bundled frontend
   version is loaded.

HACS uses the published GitHub release version when releases are available.
The `manifest.json`, Python constant, frontend constant, changelog, tag, and
release should all use the same semantic version.

### Manual

Replace `/config/custom_components/medication_stock_manager/` with the new release's folder,
restart Home Assistant, and hard-refresh the browser. Do not remove the config
entry during an update.

Existing manual users should read
[`docs/MIGRATING_FROM_MANUAL_INSTALL.md`](docs/MIGRATING_FROM_MANUAL_INSTALL.md).

## Removing the integration

1. Open **Settings -> Devices & services**.
2. Open **Medication Stock Manager**.
3. Remove the config entry.
4. Restart Home Assistant if prompted.
5. If installed through HACS, remove the repository from HACS afterward.
6. For a manual installation, delete `/config/custom_components/medication_stock_manager/`.

**Important:** removing the config entry intentionally deletes the
integration-owned owner/item storage and removes its frontend resource and
sidebar panel. Create a Home Assistant backup first when the data may be needed
again.

## Troubleshooting

### Integration is not listed

Confirm this file exists:

```text
/config/custom_components/medication_stock_manager/manifest.json
```

Then restart Home Assistant and inspect **Settings -> System -> Logs**.

### Custom element does not exist

- Confirm the integration finished loading.
- Fully close and reopen the browser tab.
- Clear the site cache if an old frontend version remains loaded.
- Do not register a second `/local/medication-stock-manager-card.js` resource.
- Follow [`docs/FRONTEND_DIAGNOSTICS.md`](docs/FRONTEND_DIAGNOSTICS.md).

### Sidebar page is missing

Enable it from the integration-owned **Show sidebar panel** switch, the
`sidebar_settings` card, or **Settings -> Devices & services -> Medication
Stock Manager -> Configure**.

### Notifications are not sent

Open the owner configuration and verify the `notify.*` targets. Automatic
Person/device detection depends on Home Assistant exposing the tracked device
and notify entity through the same device relationship.

### Calendar is empty

Confirm the owner has active non-manual items with valid times and schedules.
The integration calendar is generated from stored item configuration and is
read-only.

## Debug logging

Normal operation needs no YAML. For temporary debug logging, add this optional
configuration and restart Home Assistant:

```yaml
logger:
  default: info
  logs:
    custom_components.medication_stock_manager: debug
```

Remove it after troubleshooting to avoid excessive logs.

## Known limitations

- Browser caching may keep an old frontend module until the tab is fully
  reopened or the site cache is cleared.
- Automatic mobile notification discovery is best-effort and depends on the
  Home Assistant Person/device/entity relationships available on the system.
- Integration calendars are generated and read-only; edit the item schedule
  instead of editing calendar events.
- Personalized example dashboards are reference files and may require separate
  dashboard cards that are not dependencies of this integration.
- Removing the config entry deletes integration-owned stored data by design.

## Development and validation

The repository keeps every runtime dependency under:

```text
custom_components/medication_stock_manager/
```

Run local checks:

```bash
python -m compileall custom_components/medication_stock_manager
node --check custom_components/medication_stock_manager/frontend/medication-stock-manager-card.js
python scripts/validate_repository.py
```

GitHub Actions runs both the HACS repository validator and Home Assistant
hassfest. See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## Versioning and releases

This repository uses semantic versioning. The first HACS-ready release was
**1.4.0**. The current release is **1.4.2**.

1. Commit and push the repository.
2. Create and push the tag `v1.4.2`.
3. Create a **published GitHub release** from that tag.
4. Ensure `custom_components/medication_stock_manager/manifest.json` contains `1.4.2`.
5. Increment the version before every later release.

HACS installs the integration directly from
`custom_components/medication_stock_manager/`; a separate release ZIP is not required. See
[`docs/RELEASING.md`](docs/RELEASING.md).

## License

MIT License. See [`LICENSE`](LICENSE).


## Validation status for 1.4.2

The repository passes both HACS validation and Home Assistant hassfest on
push and pull-request events. The hassfest compatibility fixes are:

- the `http` dependency in `manifest.json`;
- `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)` in
  `__init__.py`.

The validation workflow pins `actions/checkout` v7.0.0 by commit SHA.
