# `audit` — Layer 4, service 23

**Status: RUNS** — reached by `tests/t60_audit` and `tests/t105_audit_r11` (budget edge, drop accounting, tamper and truncation), both exit 0 in the native host corpus on 2026-11-02. Not booted on the kernel.

## What it does

Append-only, sequenced, chained records of what services and agents did. The reader walks the chain and reports the first sequence that does not link instead of a bare pass/fail.

## Contract

- **Entry:** none yet. No file here exports `svc_entry`; the units are functions a `service_main` will call once the spawn signature is fixed (Q-B-L1-4, `os-build/layer1/SERVICE_CONTRACT.md` §2). That is a deviation, stated in `Deviations` below.
- **Kernel surface:** none. This unit reaches the kernel only through other services.
- **Needs from Layers 1–3:** see `os-build/layer1/BOUNDARIES.md`; the binding milestone is K6 for anything that calls a syscall, and nothing here needs K2/K3 directly unless the kernel surface line above says so.
- **Offers to Layers 5–6:** the functions listed below in the source. They run as host processes today; nothing may treat them as kernel services until the layer is booted.

## Dependencies

- **Libraries:** `common.err.err`
- **Services:** none resolved by name from this unit; the caller resolves names through the supervisor's registry (B-L1-22).
- **Data it owns:** The record buffer itself (4 KiB). Its bytes are the log; `audit_bytes()` exposes them for flush to storage, and `audit_verify_buf()` verifies records read back.

## Failure behaviour

- `E_CORRUPT` for a record that does not parse, `E_NOROOM`-style refusal (`AUD_NO_REC`) when the buffer is full -- counted in `audit_dropped_count()`, never silently truncated.
- Missing dependency at start-up: refuses to start (non-zero exit), rather than running with a hole it cannot report.
- Every failure path returns a code from `common/err` or a trailing `false`; none of them is silent.

## Limits

`AUD_REC_BUDGET` (4096 bytes) is the whole buffer: a record whose head plus body would pass 4096 is refused with `AUD_NO_REC`, never truncated. `t105` lands a record exactly on the budget and refuses the next. An oversize body does **not** move `audit_dropped_count` (nothing was lost); a full buffer does. The row is in `os-build/layer1/LIMITS.md`.

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

- Boot. The buffer has never been written by a kernel-booted service; every run is a host process.
- Restart flushing. `audit_bytes()` exposes the buffer for storage, but nothing calls it on shutdown, so a restart loses records since the last explicit flush (`os-build/layer1/r11/audit.md` §3).
- Cryptographic tamper evidence. The chain digest is a mixing function, documented as such; it detects a changed byte, not a determined forger.

## Deviations

- No `svc_entry`. The spawn signature is not published (Q-B-L1-4), so a `service_main` would be guessing at its own arguments. The functions are the body a `service_main` will wrap.
