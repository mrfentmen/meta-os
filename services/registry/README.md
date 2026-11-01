# `registry` — Layer 4, service 5

**Status: WRITTEN** (not COMPILED). Source exists; nothing in it has been compiled or run.

## What it does

NOT A SEPARATE SERVICE. The name-to-handle registry was implemented inside the supervisor (`services/supervisor/supervisor.goose`: `sup_register`, `sup_lookup`, `sup_release`, `sup_resolve`), because every caller already goes through the supervisor and a second table would be a second answer. This directory exists so the MANIFEST row is not a dead link.

## Contract

- **Entry:** none. NOT A SEPARATE SERVICE. The name-to-handle registry was implemented inside the supervisor (`services/supervisor/supervisor.goose`: `sup_register`, `sup_lookup`, `sup_release`, `sup_resolve`), because every caller already goes through the supervisor and a second table would be a second answer. This directory exists so the MANIFEST row is not a dead link.
- **Kernel surface:** none. This unit reaches the kernel only through other services.
- **Needs from Layers 1–3:** see `os-build/layer1/BOUNDARIES.md`; the binding milestone is K6 for anything that calls a syscall, and nothing here needs K2/K3 directly unless the kernel surface line above says so.
- **Offers to Layers 5–6:** the functions listed below in the source. Nothing may rely on them until the layer is COMPILED.

## Dependencies

- **Libraries:** none
- **Services:** none resolved by name from this unit; the caller resolves names through the supervisor's registry (B-L1-22).
- **Data it owns:** See the supervisor.

## Failure behaviour

- See the supervisor.
- Missing dependency at start-up: refuses to start (non-zero exit), rather than running with a hole it cannot report.
- Every failure path returns a code from `common/err` or a trailing `false`; none of them is silent.

## Verification

Checked against the Goose docs served by the language MCP (goose-mcp@1.1.0 `lookup_symbol` / `overview`):

| Symbol / form | Source |
|---|---|
| struct with typed fields | `tutorial` §3, `samples/01_tour.goose` |
| fixed arrays `T[..N]`, `u8[..N]` | `samples/03_strings.goose` |
| growable builder `u8[>..]`, `.push`, `.len` | `samples/03_strings.goose` |
| `while` / `if` / `return` | `list_keywords` |
| trailing-bool and multi-value returns | `samples/04_errors.goose` |
| reference parameter `T&` | `reference` #46 |
| bitwise `&` `|` `~` `<<` `>>` | `list_keywords` |

## Not verified

- Compilation. There is no Goose toolchain on this machine.
- Execution. No assertion in this unit has run; the test programs in `services/tests/` are where it will be exercised.
- Any kernel behaviour assumed: the syscall shapes in `common/sys/sys.goose` are this layer's request, not a published kernel interface.

## Deviations

- See the note above: this directory does not hold the implementation.
