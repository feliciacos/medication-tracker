# Branding

Home Assistant reads local custom-integration branding from:

```text
custom_components/medication_stock_manager/brand/
```

Included files:

| File | Size | Status |
| --- | ---: | --- |
| `icon.png` | 256 x 256 | Existing project icon |
| `icon@2x.png` | 512 x 512 | Existing high-resolution icon |
| `logo.png` | 256 x 256 | Placeholder copy of the icon |
| `logo@2x.png` | 512 x 512 | Placeholder copy of the high-resolution icon |

The logo files deliberately reuse the existing icon; no new artwork was
invented. Replace `logo.png` and `logo@2x.png` later with final rectangular
artwork if desired. Keep transparent PNG files, use matching artwork for
both resolutions, and do not commit proprietary font files.
