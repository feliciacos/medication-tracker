# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
