# Molecule viewer — sources (NB-037, NB-030, NB-031)

Viewer: `labs/molecules/index.html`. Three.js r152 UMD vendored at
`labs/molecules/vendor/three.min.js` (downloaded from
`unpkg three@0.152.2`, 633,338 bytes; license in
`vendor/LICENSE-three.txt`). No Three.js copy existed anywhere in this
tree (checked: no film dir, no three.js files), so vendoring fresh was
the only option. Orbit controls and labels are hand-rolled in the page.

## Embedded structures (offline JSON in `data/`)

Converted from PubChem 3D SDF (`SDF?record_type=3d`) with a throwaway
script; JSON validated by `labs/molecules/tests/` (bond endpoints,
element symbols, counts).

| File | Compound | PubChem CID | Atoms | Bonds | Formula | Weight |
|---|---|---|---|---|---|---|
| `caffeine.json` | Caffeine | 2519 | 24 | 25 | C8H10N4O2 | 194.19 |
| `aspirin.json` | Aspirin | 2244 | 21 | 21 | C9H8O4 | 180.16 |
| `glucose.json` | Glucose | 5793 | 24 | 24 | C6H12O6 | 180.16 |
| `water.json` | Water | 962 | 3 | 2 | H2O | 18.015 |
| `ethanol.json` | Ethanol | 702 | 9 | 8 | C2H6O | 46.07 |

Atom/bond counts cross-checked against the SDF counts lines at conversion
time (identical by construction); PubChem's stated counts match the same
records. Formulas and weights from PubChem PUG REST properties, recorded
in `data/meta.json` — never typed by hand.

## Load-by-CID (online only)

`Load CID` fetches `.../compound/cid/<n>/SDF?record_type=3d` from PubChem
at runtime, parses and validates it client-side, and renders it. A failed
fetch (offline, bad CID, HTTP error) shows a plain error and the embedded
five keep working. Proof: offline-equivalent tested with CID 0 and garbage
input (see section report).
