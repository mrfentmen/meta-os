# Molecule viewer — sources (NB-037, NB-030, NB-031)

Viewer: `labs/molecules/index.html`. Three.js r152 UMD vendored at
`vendor/three.min.js` (one shared copy for all four 3D pages; the former
per-page copies were byte-identical, md5 cd7f71f8, and were removed
2026-11-03. Originally downloaded from `unpkg three@0.152.2`, 633,338
bytes; license in `vendor/LICENSE-three.txt`). Orbit controls and labels
are hand-rolled in the page.

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

## Round-3 additions (NC-061, NC-066)

Same pipeline (PubChem 3D SDF → JSON, counts == SDF counts lines):

| File | Compound | CID | Atoms | Bonds | Formula (tally-verified) | Weight |
|---|---|---|---|---|---|---|
| `toluene.json` | Toluene | 2768 | 15 | 15 | C7H8 | 92.14 |
| `acetone.json` | Acetone | 180 | 10 | 9 | C3H6O | 58.08 |
| `methanol.json` | Methanol | 887 | 6 | 5 | CH4O | 32.042 |
| `urea.json` | Urea | 1176 | 8 | 7 | CH4N2O | 60.056 |
| `theobromine.json` | Theobromine | 5429 | 21 | 22 | C7H8N4O2 | 180.16 |
| `naphthalene.json` | Naphthalene | 931 | 18 | 19 | C10H8 | 128.17 |

NC-066: every formula above rechecked against the JSON atom tally —
all match, no SOURCES.md fix needed (data wins by default; data won).
