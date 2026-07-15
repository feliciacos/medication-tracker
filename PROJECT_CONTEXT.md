# CURRENT PROJECT STATE - v1.3.1

This section overrides historical implementation notes later in this file.
The history is retained only so previous decisions remain traceable.

- Runtime is fully integration-owned.
- No `configuration.yaml` key is required.
- No package YAML, automation YAML, input helper, Local Calendar, `/config/www`
  file or manually registered Dashboard Resource is required.
- Owner calendars are `calendar.medication_stock_<owner_id>`.
- Frontend is served and loaded by the integration itself.
- All later bundles must preserve this architecture unless the user explicitly
  changes it.

---

# Home Assistant Medication & Medical Supplies Project Context

## Purpose

This document is the working context for future ChatGPT sessions involving the Home Assistant medication-stock, reminder, ordering, and dashboard project.

Use this file as the source of truth before making new changes. Preserve all existing behavior unless a later request explicitly changes it.

---

## Delivery preference

For every future configuration iteration:

- Include **all previously requested Home Assistant configuration and dashboard files together in one ZIP archive**.
- Also provide the specifically changed dashboard or automation file separately when useful.
- Validate all YAML, JSON, and Python files before creating the ZIP.
- Do not drop earlier features when implementing a new request.

Latest known complete baseline bundle:

- `homeassistant_medication_dynamic_manager_v1.3.5.zip`

The project contains:

- `homeassistant/packages/`
- `homeassistant/automations/medication_stock_alerts.yaml`
- `homeassistant/custom_components/medication_order_calendar/`
- `dashboard_views/`

---

## Home Assistant environment and conventions

### Calendars

Medication schedules and generated stock/order events use:

- `calendar.felicia_medication`
- `calendar.celine_medication`

Separate order calendars are no longer used.

### Notification entities

Felicia's phone:

- `notify.red_magic_9_pro`
- Friendly name: `Red Magic 9 Pro`

Celine's phone:

- `notify.sm_a556b`
- Friendly name: `SM-A556B`

### Notification routing

Felicia:

- Medication reminders: Felicia's phone only
- Stock warnings: Felicia's phone only
- Preserve Felicia's current notification wording/layout unless explicitly changed

Celine:

- Medication reminders: Celine's phone only
- Stock/order warnings: both Felicia's and Celine's phones

### Current Celine notification wording

Medication-time reminder:

- Title: `Neem Medicatie In`
- Description: medication name

Medication needs ordering:

- Title: `Bestel Medicatie`
- Description: medication name

Medication already marked as ordered:

- Title: `Controleer Bestelling Medicatie`
- Description: medication name

Unordered medication warnings repeat daily.

Ordered medication warnings repeat once per week on Monday at 09:00 until stock is replenished.

---

## Current medication behavior

### General rules

- Medication with a recurring schedule must reduce stock automatically.
- Medication without a recurrence is manual.
- Manual correction buttons remain available:
  - `Received Box`
  - `Ordered Box`
  - `-1`
  - `+1`
- Pressing `Ordered Box`:
  - asks for confirmation
  - changes the warning to `Stock warning: check order.`
  - changes reminders from daily to weekly
- Pressing `Received Box`:
  - asks for confirmation
  - adds one configured package/box
  - clears the ordered status
- Ordered status also clears automatically when stock rises above the warning threshold.

### Felicia medication

#### Estradiol SDZ 100 µg/24 uur

- Stock entity: `input_number.felicia_estradiol_100_stock`
- Usage: 1 plaster
- Schedule: Thursday and Sunday at 11:00
- Automatic reduction: 1 plaster per scheduled use
- Box size: 8 plasters

#### Estradiol SDZ 50 µg/24 uur

- Stock entity: `input_number.felicia_estradiol_50_stock`
- Usage: 1 plaster
- Schedule: Thursday and Sunday at 11:00
- Automatic reduction: 1 plaster per scheduled use
- Box size: 8 plasters

#### Utrogestan Progesteron 100 mg

- Stock entity: `input_number.felicia_utrogestan_stock`
- Usage: 2 capsules
- Schedule: daily at 21:00
- Automatic reduction: 2 capsules per day
- Box size: 30 capsules

### Celine medication

#### Omeprazol 1A 40 mg

- Usage: 1 capsule
- Schedule: daily at 08:00
- Automatic reduction: 1 per day

#### Mebeverine HCl Retard 200 mg

- Usage: 1 capsule at 08:00 and 1 capsule at 20:00
- Automatic reduction: 2 per day

#### MagnesiumHydroxide 724 mg

- Usage: 1 chewable tablet
- Schedule: daily at 08:00
- Automatic reduction: 1 per day

#### Loratadine Hooikoortstabletten 10 mg

- Usage: 1 tablet
- Schedule: daily at 08:00
- Automatic reduction: 1 per day

#### Macrogol / Molaxole 13.7–13.8 g

- One combined stock entry
- Uses the existing Molaxole entity IDs internally
- Usage: 1 sachet every 3 days
- Schedule: 08:00, starting 13 July 2026
- Automatic reduction: 1 sachet every 3 days

#### Buscopan 10 mg

- No recurrence
- Manual stock reduction only
- Dashboard text: `Manual`

---

## Dashboard design

### Detailed medication pages

There are separate detailed pages for:

- Felicia
- Celine

Main medication buttons show:

- medication name
- current stock
- supply days in the calendar sub-button
- red warning text when ordering is needed

Popup content shows:

- current stock
- schedule
- supply
- order date
- run-out date
- red stock warning or green normal status

Popup buttons use Bubble Card controls to avoid delayed layout jumps:

1. Full-width `Received Box`
2. Full-width `Ordered Box`
3. Shorter horizontal row:
   - minus icon followed by `-1`
   - plus icon followed by `+1`

Internal button animations/transitions are disabled so the layout appears immediately.

### Medication Stock overview page

Path:

- `medication-stock`

Contains:

- Felicia stock summary table
- Celine stock summary table
- notification switches
- warning thresholds
- stock totals

All native `input_number` controls on this page should use Card Mod:

- same fixed width
- numbers aligned to the left
- current target widths:
  - 185 px desktop
  - 160 px mobile

Card Mod must remain installed through HACS.

---

## Custom integration

Custom component:

- `homeassistant/custom_components/medication_order_calendar/`

Service:

- `medication_order_calendar.replace_future_events`

Behavior:

- Deletes matching current/future generated events
- Recreates supplied all-day or timed events
- Does not modify past events

Order/run-out events:

- Created once initially
- Updated only when the relevant medication stock changes
- Stored in the person's normal medication calendar

---

# New medical supplies to add

These items are not conventional medication but must be integrated into the same stock/order/dashboard system.

They belong to **Felicia** unless a later request says otherwise.

## 1. BD Plastipak Catheter Tip Syringe 50 ml

Display name:

- `BD Plastipak Catheter Tip Syringe 50 ml`

Product description:

- `BD Plastipak injectiespuiten - 50ml - 3-delig - Katheter tip - 60 stuks`

Product URL:

- https://www.medischevakhandel.nl/nl/bd-plastipak-injectiespuiten-50ml-3-delig-katheter-tip-60-stuks

Requirements:

- Manual usage
- No recurring stock reduction
- User replaces one occasionally
- Package size: 60 syringes
- Stock warning threshold: 3 syringes
- Must support:
  - `Received Box`
  - `Ordered Box`
  - `-1`
  - `+1`
- Ordered-status and reminder behavior should match the existing Felicia workflow

Suggested unit text:

- singular: `syringe`
- plural: `syringes`

Do not invent an automatic usage schedule.

---

## 2. DCT Nelaton-Katheter for women

Display name:

- `DCT Nelaton-Katheter for women`

Product description:

- `DCT vrouwenkatheter - Keuze uit 5 maten - 50 stuks CH12`

Product URL:

- https://www.medischevakhandel.nl/nl/dct-vrouwenkatheter-keuze-uit-5-maten-50-stuks-ch12

Requirements:

- Manual usage
- No recurring stock reduction
- User replaces one occasionally
- Variant: CH12
- Package size: 50 catheters
- Stock warning threshold: 3 catheters
- Must support:
  - `Received Box`
  - `Ordered Box`
  - `-1`
  - `+1`
- Ordered-status and reminder behavior should match the existing Felicia workflow

Suggested unit text:

- singular: `catheter`
- plural: `catheters`

Do not invent an automatic usage schedule.

---

## 3. Gynotex Premium Incontinence Sheets

Display name:

- `Gynotex Premium Incontinence Sheets`

Product description:

- `Gynotex - Premium incontinentie bed onderleggers - matrasbeschermers 60x90 cm - tot 1400 ml absorptie - 25 stuks`

Product URL:

- https://www.bol.com/nl/nl/p/gynotex-premium-incontinentie-bed-onderleggers-wegwerp-incontinentie-onderleggers-matrasbeschermers-60-x-90-cm-tot-1400-ml-absorptie-25-stuks/9300000233154156/

Requirements:

- Package size: 25 sheets
- Usage: 1 sheet twice per day
- Schedule:
  - 08:00
  - 20:00
- Automatic stock reduction:
  - subtract 1 sheet at 08:00
  - subtract 1 sheet at 20:00
  - total: 2 sheets per day
- Stock warning threshold: 1 complete box/package
- Numeric threshold should therefore default to 25 sheets
- Must support:
  - `Received Box`
  - `Ordered Box`
  - `-1`
  - `+1`
- Ordered-status and reminder behavior should match the existing Felicia workflow

Reminder exception:

- Do **not** use the normal medication reminder wording for this item.
- At both scheduled times, notify Felicia with the exact text:
  - `Dillateren 30m`

The exact placement of `Dillateren 30m` as title or description should be confirmed during implementation if not otherwise specified. The important requirement is that the notification visible to Felicia says exactly `Dillateren 30m`, rather than telling her to take medication.

Suggested unit text:

- singular: `sheet`
- plural: `sheets`

---

## Expected implementation scope for the three supplies

When implementing these items, update the complete project, including as applicable:

- Felicia package helpers
- stock input numbers
- reorder threshold input numbers
- ordered-status input booleans
- days-remaining/order-date/run-out sensors
- order-needed binary sensors
- box-receipt scripts
- automatic stock reduction automation
- reminder automation
- stock warning automation
- weekly ordered follow-up behavior
- generated calendar order/run-out events
- Felicia detailed dashboard
- combined Medication Stock overview dashboard
- all relevant README/context documentation

For the two manual supplies:

- supply days, run-out dates, and order dates may be unavailable because there is no predictable recurrence
- display `Manual` where a schedule would normally appear
- do not create fake run-out calculations

For Gynotex:

- calculate supply from 2 sheets per day
- calculate order/run-out dates from that recurring usage
- use threshold 25 by default
- schedule reminders and automatic reductions at 08:00 and 20:00

---

## Important implementation cautions

- Do not remove or rename existing entities unless necessary.
- Reuse established naming conventions.
- Keep all existing Celine and Felicia medication behavior.
- Preserve dashboard styling and smooth popup controls.
- Preserve the fixed-width, left-aligned stock input controls.
- Avoid grouped notification text for Celine; current Celine stock notifications are per medication.
- Keep Felicia's existing notification layout unless a specific item requires an exception.
- The Gynotex reminder is the explicit exception.
- Create a complete ZIP containing every project file after changes.
---

# Implemented medical supplies

The following supplies are now implemented in the Felicia package, detailed
dashboard, Stock overview dashboard, warning workflow, ordered-status workflow,
and box-receipt scripts.

## BD Plastipak Catheter Tip Syringe 50 ml

- Stock: `input_number.felicia_bd_syringe_stock`
- Threshold: `input_number.felicia_bd_syringe_reorder_threshold`
- Ordered: `input_boolean.felicia_bd_syringe_box_ordered`
- Order needed: `binary_sensor.felicia_bd_syringe_order_needed`
- Received-box script: `script.felicia_bd_syringe_add_box`
- Package size: 60
- Default threshold: 3
- Usage: manual
- No calculated supply, order date, or run-out date

## DCT Nelaton-Katheter for women CH12

- Stock: `input_number.felicia_dct_catheter_stock`
- Threshold: `input_number.felicia_dct_catheter_reorder_threshold`
- Ordered: `input_boolean.felicia_dct_catheter_box_ordered`
- Order needed: `binary_sensor.felicia_dct_catheter_order_needed`
- Received-box script: `script.felicia_dct_catheter_add_box`
- Package size: 50
- Default threshold: 3
- Usage: manual
- No calculated supply, order date, or run-out date

## Gynotex Premium Incontinence Sheets

- Stock: `input_number.felicia_gynotex_sheets_stock`
- Threshold: `input_number.felicia_gynotex_sheets_reorder_threshold`
- Ordered: `input_boolean.felicia_gynotex_sheets_box_ordered`
- Order needed: `binary_sensor.felicia_gynotex_sheets_order_needed`
- Days remaining: `sensor.felicia_gynotex_sheets_days_remaining`
- Order date: `sensor.felicia_gynotex_sheets_order_date`
- Run-out date: `sensor.felicia_gynotex_sheets_run_out_date`
- Received-box script: `script.felicia_gynotex_sheets_add_box`
- Package size: 25
- Default threshold: 25
- Automatic stock reduction: one sheet at 08:00 and one sheet at 20:00
- Reminder at 08:00 and 20:00:
  - Title: `Dillateren 30m`
  - Description: `Gynotex Premium Incontinence Sheets`

The detailed popup design matches the existing Felicia medication design:

1. `Received Box`
2. `Ordered Box`
3. Horizontal `-1` and `+1`

The two manual supplies display `Manual` and do not use fake date
calculations. Gynotex uses two sheets per day for supply/date calculations.

## Artifact rule

For every later iteration, update this `PROJECT_CONTEXT.md` file and include it
in the ZIP together with the complete project and all changed files.

---

# Dynamic Medication Stock Manager (implemented)

## Why this architecture was added

Static YAML helpers and automations required code changes whenever an item or
schedule changed. The project now includes a local custom integration and a
custom Lovelace card so stock items can be managed from the Medication Stock
page.

Home Assistant config entries and integration storage are used for persistent
configuration. The active registry is stored by Home Assistant under its
hidden `.storage` directory; do not edit that file manually.

## Custom integration

Domain:

- `medication_stock_manager`

Files:

- `homeassistant/custom_components/medication_stock_manager/__init__.py`
- `homeassistant/custom_components/medication_stock_manager/config_flow.py`
- `homeassistant/custom_components/medication_stock_manager/const.py`
- `homeassistant/custom_components/medication_stock_manager/manager.py`
- `homeassistant/custom_components/medication_stock_manager/sensor.py`
- `homeassistant/custom_components/medication_stock_manager/services.yaml`
- `homeassistant/custom_components/medication_stock_manager/manifest.json`
- translation/string files

The package declaration that loads it is:

- `homeassistant/packages/medication_stock_manager.yaml`

Summary entity:

- `sensor.medication_stock_manager`

The sensor exposes the active item registry to the stock configuration card.

## Custom stock configuration card

Frontend file:

- `homeassistant/www/medication-stock-manager-card.js`

Dashboard resource URL:

- `/local/medication-stock-manager-card.js?v=1.0.0`

Card type:

- `custom:medication-stock-manager-card`

The `medication-stock` view now uses this card. It dynamically displays both
Felicia and Celine items, including items created later.

## Editable fields per item

Each medication or supply now has one expandable configuration menu with:

- name
- owner
- preset type or custom unit
- icon
- current stock
- warning threshold
- package/box size
- usage per active day
- schedule type
- active weekdays
- one or more times
- interval days and start date for every-X-days schedules
- automatic stock-management enabled switch
- optional reminder title and description
- product URL

Usage behavior:

- `usage per active day = 0` means manual stock usage
- for multiple configured times, the daily amount is divided evenly over the
  times
- weekly schedules use selected weekdays
- interval schedules support items such as Molaxole every three days

## Add and remove items

The stock configuration page contains:

- `New medication / item`
- `Remove item`
- `Restore default items`

New items do not require new YAML helpers or automations. Their stock,
threshold, ordered state, schedule, reminders, notifications, and generated
order/run-out calendar events are handled by the manager.

Removing a custom item deletes it from the manager. Removing a migrated
built-in item hides and disables it so it can be restored safely.

## Manager-owned behavior

Medication Stock Manager now owns:

- automatic stock deductions
- daily and weekly stock-warning cadence
- ordered-status cleanup
- optional time-based reminders
- generated order and run-out calendar events

The old hard-coded versions of those automations were removed from the active
automation file to prevent duplicate deductions and notifications. A backup is
included at:

- `backups/medication_stock_alerts_before_dynamic_manager.yaml`

The calendar-event reminder automations remain active for existing manually
maintained medication calendar events.

## Notification compatibility

Felicia stock notifications retain the existing grouped English layout.

Celine stock notifications remain one notification per medication/item:

- unordered title: `Bestel Medicatie`
- ordered title: `Controleer Bestelling Medicatie`
- description: item name

Celine notifications go to both phones. Felicia notifications go to Felicia's
phone.

The existing notification and reminder enable/disable helpers remain on the
stock page.

## Current built-in schedules seeded into the manager

- Felicia Estradiol 100: 1 on Thursday and Sunday at 11:00
- Felicia Estradiol 50: 1 on Thursday and Sunday at 11:00
- Felicia Utrogestan: 2 daily at 21:00
- Felicia BD syringe: manual
- Felicia DCT catheter: manual
- Felicia Gynotex sheets: 2 daily at 08:00 and 20:00
- Celine Omeprazol: 1 daily at 08:00
- Celine Mebeverine: 2 daily, divided across 08:00 and 20:00
- Celine MagnesiumHydroxide: 1 daily at 08:00
- Celine Loratadine: 1 daily at 08:00
- Celine Buscopan: manual
- Celine Molaxole: 1 every three days at 08:00, starting 13 July 2026

## Important limitation

The dynamic stock configuration page immediately supports newly created items.
The older person-specific Bubble Card pages remain static presentation pages;
a newly created item does not automatically receive a separate legacy Bubble
popup there. All stock controls and configuration for new items are available
on the dynamic stock page without a recode.

## Artifact rule

Every later iteration must update this `PROJECT_CONTEXT.md` and include it in
the ZIP with all changed project files.


---

## Dynamic manager startup fix — version 1.0.1

The initial dynamic manager implementation had a startup deadlock in:

- `custom_components/medication_stock_manager/__init__.py`

Cause:

- `async_setup()` awaited `hass.config_entries.flow.async_init(...)`.
- The import flow created a config entry.
- Setting up that entry required `async_setup()` to finish first.
- Both operations therefore waited on one another.

Fix:

- Schedule the import with `hass.async_create_task(...)`.
- Return from `async_setup()` immediately.
- Continue normal setup through `async_setup_entry()`.

Manifest version:

- `1.0.1`

Keep this fix in every later bundle.


---

## Dynamic manager frontend fix — version 1.0.2

Symptom:

- The first Medication Stock dashboard card shows `Configuration error`.
- Notification Bubble Cards below it still render.

This isolates the failure to the custom Lovelace JavaScript resource rather
than the backend integration.

Frontend changes:

- Deferred the initial render until the element is connected.
- Copied the frozen Lovelace configuration object before storing it.
- Guarded `customElements.define()` against duplicate resource entries.
- De-duplicated the `window.customCards` metadata entry.
- Added a console banner showing version `1.0.2`.

Required dashboard resource:

- `/local/medication-stock-manager-card.js?v=1.0.2`
- Type: JavaScript Module
- Keep exactly one resource entry.

Keep this frontend lifecycle and registration fix in every later bundle.


---

## Dynamic manager UI/config-flow fix — version 1.0.3

Medication Stock Manager is configured only through:

- Settings
- Devices & services
- Add integration
- Medication Stock Manager

Do not add this YAML key:

```yaml
medication_stock_manager:
```

The package file now only loads the JavaScript module:

```yaml
frontend:
  extra_module_url:
    - /local/medication-stock-manager-card.js?v=1.0.3
```

The config flow is a minimal single-instance UI flow. Replace the complete
custom-component folder and remove `__pycache__` during installation to avoid
stale code.

Remove old manually added Lovelace resource entries for the manager card.

Expected checks:

- The UI setup flow opens.
- `sensor.medication_stock_manager` exists after setup.
- `customElements.get("medication-stock-manager-card")` returns a class.
- The console logs `Medication Stock Manager Card v1.0.3 loaded`.

Keep this UI-only setup and package-based frontend loading in future versions.


---

## Dynamic manager complete-folder repair — version 1.0.4

The custom integration must always be deployed as a complete folder. Never
build a repair archive containing only the Python files changed in the latest
iteration.

Required files:

- `__init__.py`
- `config_flow.py`
- `const.py`
- `manager.py`
- `manifest.json`
- `sensor.py`
- `services.yaml`
- `strings.json`
- `translations/en.json`

A previous partial deployment omitted `const.py`, causing the component import
and config flow to fail.

The frontend card must use normal Lovelace resource registration:

- URL: `/local/medication-stock-manager-card.js?v=1.0.4`
- Type: `JavaScript module`

Do not rely on `frontend.extra_module_url` for this project. The manager
resource must be visible under Settings → Dashboards → Resources.

Expected browser checks:

```javascript
fetch("/local/medication-stock-manager-card.js?v=1.0.4")
  .then((response) => response.status)
```

Expected result:

```text
200
```

```javascript
customElements.get("medication-stock-manager-card")
```

Expected result: the registered card class, not `undefined`.

Keep `PROJECT_CONTEXT.md` updated and include it in every later ZIP.


---

## Dynamic manager persistent editor fix — version 1.0.5

The Medication Stock Manager card performs full HTML renders when Home
Assistant publishes state updates. The card must preserve its editor state
across those renders.

Required frontend behavior:

- Open medication/item menus remain open.
- The New medication/item menu remains open.
- Unsaved field values are stored as per-field drafts.
- Weekday selections are preserved.
- The active input and cursor are restored when possible.
- Save clears the saved item's draft only after the service succeeds.
- Create clears the new-item draft after the service succeeds.
- Received Box and stock adjustment controls refresh the stock value from the
  backend without discarding other unsaved fields.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.0.5`
- Type: `JavaScript module`

Expected console message:

- `Medication Stock Manager Card v1.0.5 loaded`

Keep this behavior in all later frontend versions.

---

## Dynamic dashboard and calendar scheduling — version 1.1.0

Latest complete bundle:

- `homeassistant_medication_dynamic_manager_v1.3.5.zip`

The Medication Stock Manager card supports multiple independent views:

- `stock_table`
- `item_configuration`
- `create_item`
- `item_cards`
- `all`

Card YAML can configure:

- `owner`: `felicia`, `celine`, or `all`
- `title`
- `items`
- `exclude_items`
- `item_types`
- `fields`
- `columns`
- `show_header`
- `show_description`
- `show_section_title`
- `show_actions`
- `show_remove`
- `show_restore_defaults`
- `show_dates`
- `show_schedule`
- `show_product_url`
- `group_by`
- new-item defaults and owner locking

The Felicia and Celine detailed dashboard views now use dynamic `item_cards`.
Do not return to static one-card-per-medication YAML because dynamically added
items must appear automatically.

Schedule modes stored by the backend are:

- `daily`
- `selected_weekdays`
- `interval`
- `manual`

Legacy `weekly` values are migrated on load:

- all weekdays selected → `daily`
- a weekday subset → `selected_weekdays`

UI rules:

- Daily: Times only
- Selected weekdays: Times and weekday checkboxes
- Interval: Times, interval days, and start date
- Manual: no recurring schedule fields; usage is `0`

The time parser accepts `9:00` and normalizes it to `09:00`.

The manager creates recurring Local Calendar take-time series in each item's
`calendar_entity`:

- Daily → `FREQ=DAILY`
- Selected weekdays → `FREQ=WEEKLY;BYDAY=...`
- Every X days → `FREQ=DAILY;INTERVAL=X`

One series is created for each configured time. The event duration is one
hour. Generated take-event summaries use:

- `Medication Schedule - <item id> - Take - <item name>`

Updating an item replaces its recurring schedule events. Removing it deletes
both schedule events and generated stock order/run-out events. The Calendar
Tools integration supports an optional `rrule` field and deletes complete
recurring UIDs rather than individual expanded occurrences.

The existing calendar reminder automations ignore `Medication Schedule - `
events to prevent duplicate notifications because Medication Stock Manager
already sends the configured reminder directly.

The stock table preserves horizontal/vertical scroll positions and the custom
card avoids rerendering for unrelated Home Assistant state updates.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.1.0`
- JavaScript module

Keep `CARD_CONFIGURATION_EXAMPLES.md` in future bundles and update it when card
configuration options change.


---

## Dynamic Bubble dashboard restoration — version 1.1.1

Felicia's and Celine's visible medication pages use their original Bubble Card
design. Auto-Entities dynamically generates:

- medication and medical-supply separators;
- one Bubble Card button per manager item;
- one matching standalone Bubble popup per manager item;
- Received Box, Ordered Box, -1, and +1 actions.

The source of truth remains `sensor.medication_stock_manager`. No dashboard
rewrite is required when an item is created, removed, renamed, or reassigned.

Required frontend components:

- Bubble Card
- Auto-Entities
- Card Mod

The manager configuration card compares the manager sensor state signature
instead of the complete Home Assistant hass object. It preserves page-level
and table-level scroll positions after required renders.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.1.1`


---

## Complete #Install workflow and Bubble popup fix — version 1.1.2

Future project archives must be complete install bundles intended to be
extracted under:

- `H:\#Install`

Expected extracted directory:

- `H:\#Install\MedicationStockManager-v<version>`

The root-level installer must load source files from:

- `<install folder>\homeassistant\custom_components`
- `<install folder>\homeassistant\packages`
- `<install folder>\homeassistant\automations`
- `<install folder>\homeassistant\www`

It must include and install every required project file, not only files changed
in that iteration.

Dynamic Bubble popup requirements:

- Auto-Entities dynamically generates one vertical-stack card per item.
- The Bubble popup is the first card in that vertical stack.
- Each popup includes Received Box, Ordered Box, -1 and +1 controls.
- The existing Bubble visual style and calendar cards remain intact.

Default Stock page:

- Felicia stock table
- Celine stock table
- one all-owner configuration card
- one create-item card
- notification switches

Scroll behavior:

- Do not use the summary sensor's `last_updated` value as a render signature.
- Render only when the serialized manager content changes.
- Preserve page scroll and table scroll during required renders.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.1.2`


---

## Responsive stock table and stable form rows — version 1.1.3

Default `stock_table` behavior:

- no horizontal scrollbar;
- long medication names and units wrap;
- the standard Name, Stock, Supply and Status columns fit the card width;
- `horizontal_scroll: true` remains available for custom wide tables.

Item-configuration and create-item layouts must use stable explicit rows:

- stock, threshold, package size and usage share one aligned row;
- schedule type and times are the only fields on their row;
- selected weekdays or interval fields appear on the next row;
- the two checkboxes appear below schedule-specific options;
- reminder title and reminder description each use a separate full-width row;
- calendar entity and product URL remain separate full-width rows.

Metric labels reserve equal height so all inputs on the stock/usage row align.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.1.3`

The complete project remains an `H:\#Install` bundle and must include every
required project file.


---

## Real per-item entities for dynamic Bubble dashboards — version 1.1.4

Do not generate the Felicia/Celine Bubble pages through a complex
`filter.template` that returns nested card JSON.

Medication Stock Manager exposes one real sensor per active item:

- `sensor.medication_stock_item_<item_id>`

The sensors must contain these attributes:

- `item_id`
- `manager_item`
- `owner`
- `category`
- `item_type`
- `display_order`
- `stock_text`
- `unit`
- `manual`
- `schedule_text`
- `days_remaining`
- `order_date`
- `run_out_date`
- `low`
- `ordered`
- `package_size_text`
- `product_url`

Auto-Entities must use normal include filters with `card_param: cards` and
Bubble Card options.

Manager services must resolve either:

- the stored item ID; or
- the generated item sensor entity ID.

The dynamic Bubble popup uses the manager card's `item_detail` view for live
content and actual Bubble buttons for Received Box, Ordered Box, -1 and +1.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.1.4`

The project remains a complete `H:\#Install` bundle containing every required
file.


---

## Auto-Entities domain-filter repair — version 1.1.5

The dynamic Bubble dashboards must not use this filter:

```yaml
entity_id: sensor.medication_stock_item_*
```

Although Auto-Entities supports wildcard matching, Home Assistant's visual
editor treats that value as an entity selector and reports it as unknown.

Use these normal rules instead:

```yaml
domain: sensor
attributes:
  owner: felicia
  category: medication
```

or:

```yaml
domain: sensor
attributes:
  owner: celine
  category: supply
```

Popup filters use owner only. Every filter excludes unavailable entities and
requires an `item_id` attribute.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.1.5`

Keep the complete `H:\#Install` bundle workflow and include every project file.


---

## Generic owners and native stock buttons — version 1.2.0

The integration code must contain no personal medication/item presets.

Fresh installations start with:

- no owners;
- no medication or supply items.

The old Felicia/Celine setup remains in:

- `personal_setup/PERSONAL_SETUP_REFERENCE.yaml`

This reference file is not loaded automatically.

Owner profiles are persisted in integration storage and include:

- ID
- name
- calendar entity
- reminder notification entities
- stock notification entities
- optional tracking/reminder input booleans
- default reminder title
- order title
- check-order title

Required card views:

```yaml
type: custom:medication-stock-manager-card
view: stock_buttons
owner: <owner-id-or-all>
```

```yaml
type: custom:medication-stock-manager-card
view: create_owner
title: New Owner
```

`stock_buttons` must dynamically show rounded medication/supply cards and a
popup with Received Box, Ordered Box, -1, and +1.

The red Delete all items action removes every item and generated calendar entry
but preserves owner profiles.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.2.0`

Complete archives remain designed for extraction under:

- `H:\#Install`


---

## Service registration and frontend hot-upgrade — version 1.2.1

The v1.2.0 service-registration tuple was malformed. Every service must be
registered individually through `(service, handler, schema)` records.

Required services include:

- `add_owner`
- `update_owner`
- `remove_owner`
- `clear_all_items`
- `add_item`
- `update_item`
- `remove_item`
- `set_stock`
- `set_threshold`
- `adjust_stock`
- `receive_box`
- `set_ordered`
- `process_now`
- `restore_defaults` as a compatibility alias for `clear_all_items`

Frontend resource updates must support the case where an older resource defines
`medication-stock-manager-card` first. The newer module copies all current
prototype descriptors onto the registered constructor and exposes:

```javascript
customElements.get("medication-stock-manager-card").prototype.msmVersion
```

Expected version: `1.2.1`.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.2.1`


---

## Performance, Person/mobile discovery, and integration-only setup — v1.2.2

Stock action requirements:

- `-1`, `+1`, Received Box, and Ordered Box update optimistically in the card.
- Backend stock values update in memory before service calls return.
- Legacy helper service calls are non-blocking.
- storage saves are debounced.
- stock calendar replacements are debounced per item.
- Received Box performs one combined stock/ordered update.

Owner requirements:

- link to an existing `person.*` entity or auto-match by name;
- create a Home Assistant Person through the Person integration when missing;
- inspect the Person's `device_trackers` and use entity-registry device IDs to
  find `notify.*` entities on the same mobile device;
- auto-fill reminder and stock notification targets when fields are empty;
- create a Local Calendar through the Local Calendar config flow when missing.

The integration directly manages CalendarEntity events. It must not require
`medication_order_calendar:` or any other `configuration.yaml` key. Personal
legacy packages/automations are reference-only under `personal_setup` and are
not installed for generic users.

Frontend resource:

- `/local/medication-stock-manager-card.js?v=1.2.2`


Installer migration: back up/remove the legacy `medication_order_calendar`
component and strip only its YAML declaration from the personal reminder
controls package. Preserve the existing input booleans.


---

## Fully integration-owned architecture — version 1.3.0

The user removed every old project helper/entity and emptied the project
package/automation files before taking a clean Home Assistant backup.

Future iterations must preserve this architecture:

- no `configuration.yaml` key;
- no package YAML;
- no automation YAML;
- no input_number/input_boolean helpers;
- no Local Calendar dependency;
- no required `/config/www` file;
- no manually required dashboard JavaScript resource.

Medication Stock Manager owns these entity platforms:

- sensor
- number
- switch
- button
- calendar

Registry structure:

- one service device for Medication Stock Manager;
- one owner device per stored owner;
- one item device per stored medication/supply.

Owner device entities:

- managed item count sensor;
- read-only dynamically generated medication calendar;
- Stock Warnings switch;
- Medication Reminders switch.

Item device entities:

- stock/status sensor;
- stock, threshold, package-size and daily-usage number entities;
- automatic-management, reminder and ordered switches;
- Received Box, Add One, Subtract One and Mark Ordered buttons.

The calendar platform expands recurring schedules directly from integration
storage. It also returns computed order and run-out events. Item edits/removal
therefore require no external event mutation.

Frontend module:

- stored under `custom_components/medication_stock_manager/frontend`;
- served using `StaticPathConfig`;
- loaded using `frontend.add_extra_js_url`;
- old `/local/medication-stock-manager-card.js` resource is obsolete.

The complete install archive remains intended for extraction under:

- `H:\#Install\MedicationStockManager-v<version>`

Every later archive must include every integration platform and
`PROJECT_CONTEXT.md`.


---

## Fresh setup and frontend resource registration - version 1.3.1

The integration must work from a completely empty Home Assistant project state. No package files, automation files, legacy helpers, Local Calendar entries, `/config/www` card file, or `configuration.yaml` keys are required.

Config flow requirements:

- Offer **Create the first owner now**.
- Offer **Start empty and create owners from the card**.
- An initial owner is bootstrapped exactly once from config-entry data.
- Creating an owner dynamically creates its integration device, switches, and `calendar.medication_stock_<owner-id>`.
- Creating an item dynamically creates all item entities and controls under the integration.

Frontend loading requirements:

- Serve the bundled JavaScript with `async_register_static_paths`.
- Register it through `add_extra_js_url`.
- In Lovelace storage mode, safely lazy-load the resource collection and create or update exactly one module resource.
- Never overwrite or remove unrelated Lovelace resources.
- Resource URL: `/medication-stock-manager/medication-stock-manager-card.js?v=1.3.1`.

Dashboard requirements:

- Generic setup view starts with `view: create_owner`.
- Generic setup view contains no hard-coded owner calendar entity.
- Personalized calendar cards must be conditional so a missing owner/calendar does not generate API 400 errors.


---

## Config-entry migration and frontend self-repair - version 1.3.2

ConfigFlow uses major version 2 and minor version 1. The integration must keep
an `async_migrate_entry()` function in `__init__.py` for entries created by
versions that used config-entry version 1.

Migration requirements:

- preserve entry data;
- preserve integration `.storage` owner/item data;
- infer `bootstrap_complete` for old entries;
- update the entry through `hass.config_entries.async_update_entry`;
- return `True` on successful migration.

Frontend requirements:

- serve the integration-owned JavaScript from the static integration path;
- register it through `add_extra_js_url`;
- ensure one Lovelace module resource exists;
- explicitly load the Lovelace resource collection before modifying it;
- retry after `homeassistant_started`;
- do not remove the module during ordinary reload/unload;
- remove it only when the integration config entry is deleted.

Frontend URL:

- `/medication-stock-manager/medication-stock-manager-card.js?v=1.3.2`

The project remains a complete bundle for `H:\#Install`.


---

## Calendar, notification, owner folding, and sidebar panel — version 1.3.3

Calendar dashboard requirements:

- Bubble Card calendar remains `days: 3`.
- Restore the full auto-height styles used before v1.3.0.
- Disable the internal calendar scroller/fade and allow event text to wrap.

Notification requirements:

- `notify.send_message` entity calls contain only `message` and optional `title`.
- Do not send mobile-app `data` through the notify-entity action schema.
- If a configured target is a legacy notify action such as `notify.mobile_app_phone`, call that action directly and include the tag in `data`.
- Notification calls are blocking for reliable error logging.
- Re-detect Person-linked notify entities at send time when stored targets are empty or unavailable.
- A newly created item that is already low triggers its first order warning immediately.

Owner card requirements:

- Existing owners remain folded by default.
- New Owner is also a folded `<details>` menu by default.
- Its summary contains a visible plus icon that rotates when opened.
- Preserve open owner menus across manager renders.

Sidebar requirements:

- Optional admin-only sidebar path: `medication-stock-manager`.
- Sidebar title: `Medication Stock`.
- Sidebar page contains Owners/New Owner, New Medication / Item, and Medication & Item Configuration.
- The same custom cards remain usable on normal dashboards.
- Enable/disable through a config-entry options flow.
- No YAML `panel_custom` configuration is used.

Frontend resource/version:

- `/medication-stock-manager/medication-stock-manager-card.js?v=1.3.3`


---

## Sidebar panel component mapping and options — version 1.3.4

Home Assistant built-in panel registration uses:

```text
component_name: medication-stock-manager
```

The frontend module must define:

```text
ha-panel-medication-stock-manager
```

Compatibility aliases remain registered:

```text
ha-panel-medication-stock-manager-panel
medication-stock-manager-panel
```

Do not use `medication-stock-manager-panel` as the backend component name.

The config entry stores these settings:

- `show_sidebar_panel`
- `sidebar_title`
- `sidebar_icon`
- `sidebar_require_admin`

They must be configurable:

1. in the initial integration setup flow;
2. through the integration options flow reached by **Configure**.

The panel must be registered with:

- `frontend_url_path="medication-stock-manager"`
- `config_panel_domain="medication_stock_manager"`
- configurable title, icon, and admin requirement.

The integration-owned sidebar page contains:

- Owners and New Owner
- New Medication / Item
- Medication & Item Configuration

The custom cards remain usable independently on normal dashboards.

Frontend version:

- `1.3.4`


---

## Sidebar state preservation and settings access — version 1.3.5

The custom sidebar panel must not rebuild when Home Assistant supplies a new
panel object containing identical metadata.

The panel stores a stable signature containing:

- component name
- URL path
- title
- icon
- admin requirement
- config-entry ID

Only a real signature change may rebuild the panel. A required rebuild must
capture and restore window, document, and scrollable-ancestor positions.

Sidebar visibility must be accessible through all three methods:

1. integration-owned entity:
   `switch.medication_stock_manager_sidebar_panel`
2. manager card:
   `view: sidebar_settings`
3. integration options flow

The `sidebar_settings` view supports:

- `show_sidebar_panel`
- `sidebar_title`
- `sidebar_icon`
- `sidebar_require_admin`

The blank-safe Medication Stock dashboard and the integration-owned sidebar
page both contain this card.

Frontend version:

- `1.3.5`


---

## HACS repository migration - version 1.4.0

Canonical repository:

- `https://github.com/feliciacos/medication-tracker`

Distribution structure:

- repository root contains `hacs.json`, `README.md`, `LICENSE`,
  `CHANGELOG.md`, `.github`, `docs`, `examples`, and `custom_components`;
- the only directory below `custom_components` is `medication_stock_manager`;
- every file required at runtime is inside
  `custom_components/medication_stock_manager`;
- documentation, dashboards, and personal reference data are outside the
  installed integration directory and are not runtime dependencies.

Version synchronization requirements:

- manifest version: `1.4.0`;
- `const.py` VERSION: `1.4.0`;
- frontend `MSM_CARD_VERSION`: `1.4.0`;
- Git tag/release: `v1.4.0`;
- changelog release: `1.4.0`.

Backward compatibility requirements remain unchanged:

- preserve domain `medication_stock_manager`;
- preserve storage key, config entry, migrations, entity unique IDs, services,
  frontend path, and sidebar path;
- existing manually installed users must be able to switch to HACS without
  removing their config entry;
- all frontend runtime files remain bundled inside the integration folder.

Future deliverables should include one complete repository ZIP with files at
its archive root, plus an updated `PROJECT_CONTEXT.md`. Do not return only a
partial patch.
