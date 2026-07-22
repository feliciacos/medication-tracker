# Fresh setup

Medication Stock Manager 1.5.0 is self-contained. A new installation does not
need `configuration.yaml`, packages, YAML automations, input helpers, Local
Calendar, or files in `/config/www`.

## Install with HACS

1. Add `https://github.com/feliciacos/medication-tracker` to HACS as an
   **Integration** custom repository.
2. Download Medication Stock Manager.
3. Restart Home Assistant.
4. Open **Settings -> Devices & services -> Add integration**.
5. Select **Medication Stock Manager**.

## First-run choices

The setup flow can:

- create the first owner immediately; or
- start empty and let the owner-management card create owners later.

The setup flow also configures the optional sidebar page:

- enabled or disabled;
- title;
- icon;
- administrator-only access.

## Expected entities

A new empty installation initially creates the manager service device and its
summary/configuration entities. Creating an owner adds an owner device,
calendar, reminder switch, and stock-warning switch. Creating an item adds its
stock sensor, number entities, switches, and action buttons.

## Frontend

The integration serves its bundled frontend from:

```text
/medication-stock-manager/medication-stock-manager-card.js?v=1.5.0
```

It registers that module automatically. Do not add a second `/local/...`
Lovelace resource.

## Blank-safe configuration dashboard

Use the example in:

```text
examples/dashboards/medication_stock_overview_view.yaml
```

It can create the first owner and first item without assuming any existing
owner or calendar.
