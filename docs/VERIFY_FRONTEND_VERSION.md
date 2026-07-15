# Verify frontend version 1.4.0

Open the browser developer console and run:

```javascript
customElements.get(
  "medication-stock-manager-card"
)?.prototype?.msmVersion
```

Expected:

```text
1.4.0
```

Verify the served source too:

```javascript
fetch(
  "/medication-stock-manager/medication-stock-manager-card.js?v=1.4.0"
)
  .then((response) => response.text())
  .then((text) =>
    text.match(/MSM_CARD_VERSION = "([^"]+)"/)?.[1]
  )
```

Expected:

```text
1.4.0
```
