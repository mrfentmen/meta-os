# HANA — Layer 2 work order: shell and apps (Lobster)

The boss's order 2026-11-01 (~08:18): the OS build goes parallel by
layer. **Your layer is Layer 2 — the user-facing shell and apps, in
Lobster.** Milo is your pairing (agent process model, gate-1); Pax
merges — no self-merge. Branch: `hana/layer2-shell` in
`mrfentmen/meta-os`. Report to crew room 1 at stage boundaries.
Everyone's layer index: `os-build/LAYERS.md`.

State at this writing: your Layer 2 shell work is spec-only until
real OS state exists (your own reports), and your `hana/ui-fix-list`
branch is still unmerged because it has no Milo gate yet — that gate
is Milo's immediate queue item (his ML-L2-02).

## Your tools — fixed today

The MCP gateway is now committed in this repo at `mcp-gateway/` (it
previously existed only on Pax's VM, which is why you could not
connect). Its README has the setup: run your own instance, and the
boss's `lobster__*` (16 tools, v1.1.0) and `goose__*` (17 tools) are
the language authorities for this layer. Ground every Lobster claim
in `lobster__*` or the upstream repo (aardappel/lobster).

## Tasks

- **HN-L2-01 — Shell spec.** The home surface reads REAL OS state
  only: the Layer 1 service list from `services/MANIFEST.md` (Buffy's
  B-L1-01, when it lands) and kernel milestone state from
  `os-build/SCOREBOARD.md` (Milo's ML-L2-03). Every value the shell
  shows names its source; a value with no source is not shown. Spec
  first, in `os-build/layer2/`.
- **HN-L2-02 — App model.** How programs (Imperium, Musica, Scientia,
  Officina) appear and launch in the shell. Design only until K6
  exists: a program is not the OS, and the shell must not present a
  program as an OS feature.
- **HN-L2-03 — First Lobster source.** The shell's data layer (state
  reading, no rendering claims) written against Milo's agent process
  model (his ML-L2-01) when it lands; every Lobster symbol verified
  against `lobster__*`. Status target: WRITTEN, honestly labeled.
- **HN-L2-04 — HN-077: science-lab Swift mirror.** Standing follow-up
  from the science-lab merge: `js/products.js` is the source of truth
  and the Swift `ProductConfig.swift` mirror has zero science-lab
  references. Bring the mirror into agreement and prove it with the
  existing web/native agreement tests.

## Rules

1. **NO MOCKS**: no fake OS state in any surface, ever — a shell that
   displays invented state is the exact failure this layer exists to
   avoid.
2. Status words exactly: DESIGNED / WRITTEN / VERIFIED / NOT BUILT.
3. Milo gate-1 before Pax merges anything from this lane.
