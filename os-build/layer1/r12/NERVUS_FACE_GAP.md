# Nervus face feed — gap record (R12-014)

Status: **GAP.** No Hana surface contract exists for the Nervus window, so no feed shape is
written against a guess. This record lists what the feed must carry so the contract has
something concrete to answer.

## What exists to feed it

| source | record |
|---|---|
| `nervus/inspect.mjs` | `model_hash`, `architecture`, `layer_count`, `total_bytes`, per-file sizes |
| `nervus/layermap.mjs` | ordered layers, `completeness` (`shape-only` vs supplied sizes), source |
| `nervus/delta.mjs` | signed delta, before/after hashes, probe name, direction |
| `nervus/stub-runner.mjs` | every record, `stub: true` |

## What the feed must carry

1. **Identity** — the inspection hash and architecture, never a path.
2. **Layer curve** — per-layer values with a marker for "not measured" so a null is not drawn as
   zero.
3. **Completeness** — the layer map's own `completeness` string, displayed, not dropped.
4. **Delta** — before → after with sign, both hashes, and the probe name. No colour that implies
   "better" without the sign and the probe.
5. **Stub banner** — when any record has `stub: true`, the window says STUB in the same visual
   weight as the numbers; the receipt must not be mistakable for a real model result.
6. **Refusals** — a missing contract or an unreadable record renders as an explicit "no data"
   state, not an empty chart.

## What this record is not

- Not a contract. Field names, sizes and refresh cadence are Hana's call.
- Not a claim that a model was read: the inspector reads a directory; the runner is a stub.
