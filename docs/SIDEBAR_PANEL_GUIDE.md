# Sidebar panel guide

The optional sidebar page is owned by the integration and uses this URL:

```text
/medication-stock-manager
```

It contains sidebar settings, owner management, new-item creation, and item
configuration. The same custom-card views remain usable on ordinary Lovelace
dashboards.

## Configure during initial setup

The config flow asks for:

- whether the page should be shown;
- sidebar title;
- sidebar icon;
- whether only administrators may open it.

## Configure later

Use any of these methods:

1. **Settings -> Devices & services -> Medication Stock Manager -> Configure**
2. `switch.medication_stock_manager_sidebar_panel`
3. A dashboard card:

   ```yaml
   type: custom:medication-stock-manager-card
   view: sidebar_settings
   title: Sidebar Settings
   ```

When the sidebar page is disabled from inside itself, re-enable it with the
integration-owned switch or a `sidebar_settings` card on a normal dashboard.

## Verify the panel element

```javascript
customElements.get("ha-panel-medication-stock-manager")
```

Expected result: a class, not `undefined`.

The frontend also registers compatibility aliases for older installations.
