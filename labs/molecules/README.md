# labs/molecules — viewer notes

Viewer: `labs/molecules/index.html`. Three.js r152 UMD, single shared copy
at `vendor/three.min.js` (the only three.js copy in the tree; every 3D page
loads that path). Orbit controls and labels are hand-rolled in the page.

## How to add a structure

Convert the PubChem 3D SDF (`SDF?record_type=3d`) for the new compound's
CID to `data/<id>.json` with atoms `[{x, y, z, sym}]` and bonds
`[{a, b, o}]` (zero-based atom indexes, order 1–3), then append one row to
`data/meta.json` (`id, name, cid, formula, weight, url`) and one caption
line to the `CAPTIONS` map in `index.html`; verify with
`node --test labs/molecules/tests/` (counts the test pins to the expected
atom/bond totals, so add yours there too) and `python3 labs/check_assets.py`.
Formulas and weights come from the PubChem PUG REST record, never typed by
hand — if the JSON atom tally disagrees with the stated formula, the data
wins and the formula gets fixed.
