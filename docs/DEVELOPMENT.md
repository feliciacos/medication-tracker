# Development and validation

## Repository layout

Runtime files must stay under:

```text
custom_components/medication_stock_manager/
```

Documentation and examples may live elsewhere because HACS does not copy
them into Home Assistant.

## Local checks

```bash
python -m compileall custom_components/medication_stock_manager
node --check custom_components/medication_stock_manager/frontend/medication-stock-manager-card.js
python scripts/validate_repository.py
```

The repository workflow also runs the HACS repository validator and Home
Assistant hassfest on pushes, pull requests, a daily schedule, and manual
dispatches.

## Test in Home Assistant

Copy the integration directory to a development Home Assistant config:

```text
/config/custom_components/medication_stock_manager/
```

Restart Home Assistant, add the integration through **Settings -> Devices
& services**, and verify config flow, owner creation, item creation,
integration-owned entities, calendars, services, frontend cards, sidebar
registration, unload/reload, and removal behavior.
