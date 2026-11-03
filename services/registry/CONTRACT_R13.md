# Contract note — R13-025, registry upgrade note

Status: **AUDITED — 2 gaps filed**.
Facet: the upgrade note for `registry` — what changes across versions, how a running system
migrates, and what an operator must do.

## Evidence

Commands:

```sh
ls -la services/registry
grep -RIn 'registry' services/MANIFEST.md services/callmatrix/callmatrix.goose os-build/layer1/r11/registry.md
```

Relevant output:

```text
services/registry/:
README.md       1686 bytes
```

```text
MANIFEST.md:62  | 7 | `registry` | Name → service id lookup | K-ipc | `lookup(name)` for L5–6 | B-L1-22 | NOT BUILT |
r11/registry.md:3  Source: none — `services/registry/` holds a README only · Test: none
```

## Corrected contract

`registry` has no implementation and therefore no upgrade path to document. The README is a
pointer: the name-to-handle table lives in `services/supervisor/supervisor.goose` as
`sup_register`, `sup_lookup`, `sup_release` and `sup_resolve`. There is no `SVC_REGISTRY` id, no
`svc_entry` and no persistence.

The only migration statement in the tree is in the README's “What is not proven”: a supervisor
restart loses every name and handle, and boot re-registration is specified in
`services/supervisor/bootorder.goose` but has not been shown to produce equivalent handles. That
is a restart caveat, not an upgrade note.

## Mismatches

- **R13-025-G1** — no upgrade note exists for a service that has no implementation.
- **R13-025-G2** — the only close artefact, the Round 11 record, documents restart loss but no
  version-to-version migration. See `services/registry/GAPS_R13.md`.
