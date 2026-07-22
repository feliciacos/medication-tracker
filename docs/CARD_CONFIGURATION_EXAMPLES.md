# Card configuration examples

The custom card is bundled and registered by Medication Stock Manager. No
separate HACS frontend repository or `/local/...` resource is required.

The optional owner-calendar example at
`examples/dashboards/owner_medication_stock_bubble_card.yaml` also uses
[Bubble Card](https://github.com/Clooos/Bubble-Card). It is the only separate
HACS frontend card required by that example; it is not required for the bundled
Medication Stock Manager card shown below.

## Interactive stock buttons

```yaml
type: custom:medication-stock-manager-card
view: stock_buttons
owner: all
show_header: false
group_by_owner: true
```

Use a specific configured owner ID when needed:

```yaml
type: custom:medication-stock-manager-card
view: stock_buttons
owner: your_owner_id
show_header: false
```

## Stock table

```yaml
type: custom:medication-stock-manager-card
view: stock_table
owner: all
title: Medication & Supply Stock
columns:
  - name
  - owner
  - stock
  - supply
  - status
horizontal_scroll: false
```

## Item configuration

```yaml
type: custom:medication-stock-manager-card
view: item_configuration
owner: all
title: Medication & Item Configuration
show_restore_defaults: true
show_remove: true
show_actions: true
```

The card automatically renders separate `Medication` and `Supplies` sections.
Each item has a drag handle. Drag an item above or below another item with
the same owner in the same section. The backend persists the before/after
position and rejects cross-owner or cross-category drops, so medication cannot
be moved into Supplies and supplies cannot be moved into Medication. The handle
also supports Arrow Up and Arrow Down when focused.

The red delete-all action permanently removes all items and their generated
calendar events while retaining owner profiles.

## New medication or supply

```yaml
type: custom:medication-stock-manager-card
view: create_item
owner: all
title: New Medication / Item
default_type: capsule
default_schedule: manual
```

## Owner management

```yaml
type: custom:medication-stock-manager-card
view: create_owner
title: Owners
show_existing_owners: true
```

## Sidebar settings

```yaml
type: custom:medication-stock-manager-card
view: sidebar_settings
title: Sidebar Settings
```

## Complete blank-safe setup view

A complete example is included at:

```text
examples/dashboards/medication_stock_overview_view.yaml
```
