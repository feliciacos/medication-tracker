# Releasing Medication Stock Manager

The project uses semantic versioning. The first HACS-ready release was
`1.4.1`. The current release is `1.4.1` and the Git tag is `v1.4.1`.

## Before a release

1. Update `VERSION` in `custom_components/medication_stock_manager/const.py`.
2. Update `MSM_CARD_VERSION` in the bundled frontend JavaScript.
3. Update `version` in `custom_components/medication_stock_manager/manifest.json`.
4. Add the release to `CHANGELOG.md`.
5. Run local syntax validation.
6. Push the branch and wait for both **HACS** and **Hassfest** jobs to pass.

## Publish the release

```bash
git tag -a v1.4.1 -m "Medication Stock Manager v1.4.1"
git push origin v1.4.1
gh release create v1.4.1 \
  --title "Medication Stock Manager v1.4.1" \
  --notes "See CHANGELOG.md for the full release notes."
```

A tag by itself is not enough for release-based HACS updates. Publish a
GitHub release from the tag. HACS installs the integration directly from
`custom_components/medication_stock_manager`; no release ZIP asset is needed.

For later updates, increment the semantic version in all three runtime
locations before creating the next tag and release.
