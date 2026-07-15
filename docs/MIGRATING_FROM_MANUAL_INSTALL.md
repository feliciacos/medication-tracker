# Migrating an existing manual installation to HACS

The integration domain, config-entry data, storage key, entity unique IDs,
service names, frontend URL, and sidebar path remain unchanged. Existing
owners, items, calendars, devices, and entities should therefore continue
to work after changing the installation method.

1. Create a full Home Assistant backup.
2. Do **not** remove the Medication Stock Manager config entry. Removing the
   config entry intentionally deletes the integration-owned stored data.
3. Add `https://github.com/feliciacos/medication-tracker` to HACS as an **Integration** custom repository.
4. Download Medication Stock Manager through HACS.
5. If HACS reports that the destination already exists, stop Home Assistant,
   back up and remove only this folder:

   ```text
   /config/custom_components/medication_stock_manager/
   ```

   Then download it through HACS again.
6. Restart Home Assistant.
7. Hard-refresh or fully reopen the browser so the bundled frontend module
   is loaded at the new release version.
8. Verify that the existing config entry, owners, items, stock values, and
   calendars are still present.

Never create this accidental nested path:

```text
/config/custom_components/custom_components/medication_stock_manager/
```
