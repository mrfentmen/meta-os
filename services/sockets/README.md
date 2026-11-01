# `sockets` — Layer 4 service

**Status: NOT BUILT.** No source yet. Filled by **B-L1-33**.

This README is the entry from `services/README_TEMPLATE.md`, unfilled. Every
section below is deliberately empty rather than optimistic: a section that says
nothing is honest, a section that guesses is not.

## What it does

socket contract. Not written yet.

## Contract

- **Entry:** none yet. Will be `export "svc_entry" fn service_main(...) -> i32`
  per `os-build/layer1/SERVICE_CONTRACT.md` §2.
- **Kernel surface:** none declared yet. Requirements it will place on Layers 1–3
  are listed in `os-build/layer1/BOUNDARIES.md`.
- **Needs from Layers 1–3:** see `services/MANIFEST.md`, row for `sockets`.
- **Offers to Layers 5–6:** see `services/MANIFEST.md`; nothing may rely on it yet.

## Dependencies

- **Libraries:** not yet decided — B-L1-15's gap audit narrows the candidates.
- **Services:** not yet decided.
- **Data it owns:** not yet decided.

## Failure behaviour

Not yet designed. When it is, the codes come from `common/err` and a failure is
always a log record, never a silence.

## Verification

Nothing to verify: no source.

## Not verified

Everything. There is no Goose toolchain on this machine
(`goose__toolchain_status` → `NOT FOUND`), so even a finished service cannot pass
WRITTEN into COMPILED here.

## Deviations

None — nothing has been written to deviate from.
