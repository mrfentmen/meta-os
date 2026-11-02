# `callmatrix` — Layer 4, service 26

**Status: RUNS.** `tests/t69_callmatrix` (28 checks, exit 0) proves every id has a row, the twelve
previously-missing edges are allowed, and the table denies by default. `tests/t109_callmatrix_r11`
adds the bound (`cm_bit(32)` is 0), the self-call rules, the `E_DENIED`/`E_INVAL` split, and the
mask/check agreement. Host runs only; nothing has booted.

## What it does

The service-to-service permission table, and the single check `cm_allows`/`cm_check` the registry
consults. Deny by default: an unlisted pair, an unknown caller or an unknown callee is refused.

The table is 31 rows of `i64` bitmasks — one bit per callee — so a check is a shift and a mask: no
search, no allocation, and no way to have a partially-written row. `cm_row` also denies a row whose
`caller` field does not match its index, so an uninitialised table fails closed.

## Contract

- **Entry:** none. No file here exports `svc_entry`; the units are functions a `service_main` will
  call once the spawn signature is fixed (Q-B-L1-4, `SERVICE_CONTRACT.md` §2), stated in
  `Deviations` below.
- **Kernel surface:** none. This unit reaches the kernel only through other services.
- **Needs from Layers 1–3:** nothing directly.
- **Offers to Layers 5–6:** `cm_allows`, `cm_check`, `cm_mask`, `cm_row`, `cm_bit`, `cm_init`.

## Dependencies

- **Libraries:** `common.err.err`
- **Services:** none resolved by name; the supervisor's registry calls this table.
- **Data it owns:** the matrix itself (31 × 64-bit rows). Static data, no file.

## Failure behaviour

- `E_DENIED` for a refused pair, `E_INVAL` for an out-of-range service id. The split is testable
  and tested: one is policy and belongs to the table's owner, the other is a caller bug and
  belongs to the caller's author.
- No failure path is silent; `cm_allows` answers `false`, `cm_check` answers a code.

## Deviations and gaps

- **No `svc_entry`.** The spawn signature is not published (Q-B-L1-4); a `service_main` here would
  be guessing at its own arguments.
- **No row for itself.** `callmatrix` has no `SVC_*` id: it is the permission function, not a
  participant, so it cannot be called through the registry it answers for. Recorded as a finding
  in `os-build/layer1/r11/callmatrix.md`; adding an id is an append-only decision, not a cleanup.

## What is not verified

- That the freestanding link works; host runs use `host_shim.c`.
- A kernel-hosted start: nothing has run this module under the supervisor, and `cm_init` ordering
  is a registry responsibility, not something this unit can enforce.
