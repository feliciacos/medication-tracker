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
- Medication and medical-supply items with custom units, a searchable Home
  Assistant icon picker, and explicit `custom_med` or `custom_supply` categories.
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
- Bundled frontend card with stock tables, stock buttons, category-separated
  item configuration, owner management, item creation, sidebar settings, and
  item details.
- Persistent per-owner ordering controls that keep medication and supplies in
  their own sections.
- Optional configurable Home Assistant sidebar panel.
- UI config flow, options flow, config-entry migration, unload support, and
  removal cleanup.

## Screenshots / Custom Cards
 - Add Medication / Supply Item
<img width="1350" height="867" alt="chrome_dKthi4tIRw" src="https://github.com/user-attachments/assets/56f0a0bd-280d-4114-889c-d8611f17bfb8" />

 - Medication / Item Configuration
<img width="1352" height="728" alt="chrome_HJbjZpQCA1" src="https://github.com/user-attachments/assets/9f2245e6-a252-44ba-a674-e975deebda25" />
<img width="1351" height="1071" alt="chrome_cOlCM7afCF" src="https://github.com/user-attachments/assets/a98eea0f-f462-406b-ada5-96c3d01f4649" />

 - Add Owner
<img width="1357" height="1125" alt="chrome_00hdtea1yg" src="https://github.com/user-attachments/assets/50d53845-ac2a-4800-8b33-c4ee6d06da85" />
 
 - Update Medication / Supply Item Card
<img width="573" height="989" alt="image" src="https://github.com/user-attachments/assets/17215f4e-6cc1-4904-b351-de6d8891d5d7" />
<img width="740" height="677" alt="image" src="https://github.com/user-attachments/assets/1e60ca64-ea3d-4edc-9215-b409cf629514" />

 - Medication Stock Overview Card 
<img width="568" height="756" alt="image" src="https://github.com/user-attachments/assets/1938cf7e-4567-4472-9f37-90274ab08b83" />


## Requirements

- Home Assistant **2026.3.0 or newer**.
- HACS is optional but recommended for installation and updates.
- JavaScript must be enabled in the browser for the bundled frontend card and
  sidebar panel.
- [Bubble Card](https://github.com/Clooos/Bubble-Card) is the only third-party
  HACS frontend card used by the optional owner-calendar dashboard example.
  Install Bubble Card through HACS before importing that example. The core
  integration, bundled Medication Stock Manager card, and generic setup page do
  not require Bubble Card.

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
3. Configure schedules, stock values, reminders, warning thresholds, and icons.
4. Drag items by their handle inside the Medication or Supplies section.
   Items cannot cross owner or category boundaries.
5. Use the stock buttons to receive a box, mark an order, or adjust stock.

Useful card examples are available in
[`docs/CARD_CONFIGURATION_EXAMPLES.md`](docs/CARD_CONFIGURATION_EXAMPLES.md).
Example dashboard views are in [`examples/dashboards`](examples/dashboards),
including a generic setup view and an optional Bubble Card owner-calendar view.

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

This repository uses semantic versioning. The current prepared release is
**1.5.1**.

1. Commit and push the repository.
2. Create and push the tag `v1.5.1`.
3. Create a published GitHub release from that tag.
4. Keep the manifest, Python constant, frontend constant, changelog, tag, and
   release synchronized.

See [`docs/RELEASING.md`](docs/RELEASING.md).

## License

MIT License. See [`LICENSE`](LICENSE).
