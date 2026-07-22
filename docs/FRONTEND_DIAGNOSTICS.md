# Frontend diagnostics

## Confirm the integration version

Open **Settings -> Devices & services -> Medication Stock Manager**. The
service and owner devices should report software version `1.5.1`.

## Confirm the JavaScript file is served

Run this in the browser developer console:

```javascript
fetch(
  "/medication-stock-manager/medication-stock-manager-card.js?v=1.5.1"
).then(async (response) => ({
  status: response.status,
  contentType: response.headers.get("content-type"),
  version: (await response.text()).match(
    /MSM_CARD_VERSION = "([^"]+)"/
  )?.[1],
}))
```

Expected result:

```text
status: 200
version: 1.5.1
```

## Confirm the custom card is registered

```javascript
customElements.get(
  "medication-stock-manager-card"
)?.prototype?.msmVersion
```

Expected result:

```text
1.5.1
```

## Confirm the sidebar panel is registered

```javascript
customElements.get("ha-panel-medication-stock-manager")
```

Expected result: a class, not `undefined`.

## When the file is served but the custom element is undefined

1. Confirm the integration finished loading without errors.
2. Remove any obsolete manually configured `/local/medication-stock-manager-card.js`
   Lovelace resource.
3. Completely close and reopen the Home Assistant browser tab.
4. Clear the Home Assistant site cache when an older module remains loaded.
5. Reload the integration or restart Home Assistant.
6. Inspect **Settings -> System -> Logs** for frontend registration errors.
