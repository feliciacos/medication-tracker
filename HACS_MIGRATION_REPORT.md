# HACS migration report

## Runtime files moved

The complete integration was moved from:

```text
homeassistant/custom_components/medication_stock_manager/
```

to the HACS repository location:

```text
custom_components/medication_stock_manager/
```

No Python import changes were required because integration modules use
package-relative imports. The frontend static path already resolves its
JavaScript with `Path(__file__).parent`, so it remains valid after HACS
installs the integration folder.

## Runtime compatibility preserved

- domain: `medication_stock_manager`
- storage key: unchanged
- service names: unchanged
- config entry versions/migrations: unchanged
- entity unique IDs: unchanged
- frontend URL: unchanged apart from the version query value
- sidebar URL/component: unchanged
- translations and service descriptions: included
- all Python platforms: included
- bundled frontend JavaScript: included
- local brand assets: included

## Repository files created

- `hacs.json`
- `.github/workflows/validate.yml`
- `.github/dependabot.yml`
- `LICENSE`
- `CHANGELOG.md`
- public `README.md`
- HACS/manual/release/development/branding documentation
- local repository validator
- example dashboards and non-runtime personal setup reference

## Placeholder

`logo.png` and `logo@2x.png` currently reuse the existing icon artwork.
Replace them later when final rectangular logo artwork is available.


## Post-migration validation fixes

The HACS repository now also includes the two declarations required by
hassfest for the current runtime code:

- `http` in the manifest dependency list because the integration registers a
  static HTTP path;
- `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)` because the
  integration implements `async_setup` but intentionally supports only UI
  config entries, not `configuration.yaml`.

Dependabot PR #1 updates the pinned checkout action to v7.0.0.
