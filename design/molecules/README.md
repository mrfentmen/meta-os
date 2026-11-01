# Molecule viewer — data provenance

Viewer: `design/meta-scientia-molecules.html` (Three.js r152 vendored at
`design/vendor/three.min.js`; all other assets are same-origin files, so the
page works with the network off — verified: every request it makes is
127.0.0.1).

## PubChem records (real measured/curated 3D, verbatim downloads)

| File | What | Source |
|---|---|---|
| `caffeine.sdf` | Caffeine 3D conformer, 24 atoms / 25 bonds | PubChem CID 2519, `SDF?record_type=3d` |
| `aspirin.sdf` | Aspirin 3D conformer | PubChem CID 2244, `SDF?record_type=3d` |
| `glucose.sdf` | Glucose 3D conformer, 24 atoms / 24 bonds | PubChem CID 5793, `SDF?record_type=3d` |
| `meta.json` | Formula + molar mass + source per compound | Formulas/weights from PubChem PUG REST properties; cross-checked |

## RDKit-generated (NOT measurements)

Five Delaney ESOL solubility-set members, coordinates generated locally:

- `esol-benzene.sdf` (c1ccccc1), `esol-toluene.sdf` (Cc1ccccc1),
  `esol-phenol.sdf` (Oc1ccccc1), `esol-aniline.sdf` (Nc1ccccc1),
  `esol-benzoic-acid.sdf` (O=C(O)c1ccccc1)
- Method: RDKit 2025.09.2, ETKDGv3 (randomSeed 42, useRandomCoords) + MMFF
  cleanup (maxIters 200). All embedded cleanly on the first attempt.
- The page and its footer label these "generated, not measured" wherever
  they appear. Formula/weight in meta.json computed by RDKit, not typed.
- Caveat: the exact five "gate set" molecules from the science lab work are
  not in this checkout (the scaffold branch was never pushed), so these are
  five canonical ESOL members, not the archived gate CSV rows. Do not claim
  otherwise.

## Vendored library

- `design/vendor/three.min.js`: three.js r152 UMD build, downloaded from
  unpkg (`three@0.152.2/build/three.min.js`, 633,338 bytes). Only the core is
  vendored; orbit controls and label helpers are hand-rolled in the page
  (no examples/jsm code), so there is nothing else to license-track.
