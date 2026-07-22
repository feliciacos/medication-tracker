# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.5.0] - 2026-07-22

### Added

- Added Home Assistant's native searchable icon picker to existing-item, new-item, and
  sidebar icon fields, while continuing to accept custom `mdi:` values.
- Added separate `Medication` and `Supplies` sections to Medication & Item
  Configuration.
- Added persistent up/down ordering controls and a `move_item` service.

### Changed

- Item ordering is normalized independently for each owner and category.
- Reordering is restricted to items belonging to the same owner and the same
  medication/supply category.
- Changing an item's owner or type places it at the end of the destination
  category without disturbing unrelated items.

## [1.4.3] - 2026-07-16

### Added

- Added `custom_med` and `custom_supply` item types for user-defined items.
- Added explicit custom-supply grouping in the bundled dashboard cards.
- Documented Bubble Card as the only third-party HACS frontend card used by
  the optional owner-calendar dashboard example.

### Changed

- Existing legacy `custom` items are migrated automatically to `custom_med` so
  current installations remain compatible.
- Custom medication and custom supply types preserve the manually entered unit
  instead of replacing it with a predefined unit.

## [1.4.2] - 2026-07-15

### Changed

- Reordered sidebar settings so title and icon are on the top row and the two
  checkbox settings are on the bottom row.
- Updated synchronized runtime, frontend, manifest, validation, and release
  versions to `1.4.2`.
- Added ignore rules for private project-context files and personalized setup
  examples.

## [1.4.1] - 2026-07-15

### Fixed

- Declared the integration as config-entry-only with
  `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)`, satisfying
  Home Assistant hassfest without adding YAML configuration support.
- Declared the Home Assistant `http` dependency used by the bundled frontend
  static-file route.

### Changed

- Updated the pinned `actions/checkout` workflow dependency from v6.0.3 to
  v7.0.0 through Dependabot PR #1.
- Kept HACS and hassfest validation green for push and pull-request events.

## [1.4.0] - 2026-07-15

### Added

- HACS-compatible repository layout with one integration under
  `custom_components/medication_stock_manager`.
- Root `hacs.json` manifest.
- Pinned HACS and Home Assistant hassfest validation workflow.
- Dependabot configuration for GitHub Actions updates.
- Public installation, update, removal, troubleshooting, debugging,
  development, migration, branding, and release documentation.
- MIT license.
- Local `logo.png` and `logo@2x.png` placeholder files derived from the
  existing project icon.
- Example dashboards and personal setup reference outside the runtime folder.
- Repository self-validation script.

### Changed

- Release version advanced from `1.3.5` to `1.4.0`.
- Integration manifest now links to the public documentation and issue tracker,
  declares `@feliciacos` as code owner, includes an explicit empty requirements
  list, and marks the integration as single-config-entry.
- Distribution is now HACS-first while preserving manual folder installation.

### Preserved

- Integration domain and storage key.
- Config entry and migration behavior.
- Entity unique IDs and service names.
- Owner/item storage and integration-owned calendars.
- Configuration and options flows.
- Notification, stock, schedule, panel, and frontend functionality.
- Frontend static URL and sidebar URL.

[1.4.0]: https://github.com/feliciacos/medication-tracker/releases/tag/v1.4.0

[1.4.1]: https://github.com/feliciacos/medication-tracker/releases/tag/v1.4.1

[1.4.2]: https://github.com/feliciacos/medication-tracker/releases/tag/v1.4.2
[1.4.3]: https://github.com/feliciacos/medication-tracker/releases/tag/v1.4.3
[1.5.0]: https://github.com/feliciacos/medication-tracker/releases/tag/v1.5.0
