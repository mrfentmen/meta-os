# `agenthost` — Layer 4, service 20

**Status: RUNS** — reached by `tests/t59_agenthost` (48 checks), `tests/t97_agent_surface` (quota, channel, lifecycle, the down line) and `tests/t104_agenthost_r11` (capacity, all refusals, handle reuse), all exit 0 in the native host corpus on 2026-11-02. Not booted on the kernel.

## What it does

The host-side table of agent processes: name, lifecycle state, pid and capability mask. An agent is addressed by a handle carrying slot and generation, so a stale handle resolves to nothing rather than to whichever agent took the slot next.

## Contract

- **Entry:** none yet. No file here exports `svc_entry`; the units are functions a `service_main` will call once the spawn signature is fixed (Q-B-L1-4, `os-build/layer1/SERVICE_CONTRACT.md` §2). That is a deviation, stated in `Deviations` below.
- **Kernel surface:** none. This unit reaches the kernel only through other services.
- **Needs from Layers 1–3:** see `os-build/layer1/BOUNDARIES.md`; the binding milestone is K6 for anything that calls a syscall, and nothing here needs K2/K3 directly unless the kernel surface line above says so.
- **Offers to Layers 5–6:** the functions listed below in the source. They run as host processes today; nothing may treat them as kernel services until the layer is booted.

## Dependencies

- **Libraries:** `common.err.err`
- **Services:** none resolved by name from this unit; the caller resolves names through the supervisor's registry (B-L1-22).
- **Data it owns:** The agent table (24 slots, compiled in), including each agent's grant mask. Volatile: it is rebuilt by the supervisor at start-up and nothing outside this process may read it directly.

## Failure behaviour

- `E_INVAL` for a bad name or an undefined capability bit, `E_BUSY` for a duplicate name, `E_NO_SPACE` when the table is full, `E_STATE` for an illegal lifecycle move, `E_NOTFOUND` for an unknown handle. Refuses to start without the supervisor (no table owner).
- Missing dependency at start-up: refuses to start (non-zero exit), rather than running with a hole it cannot report.
- Every failure path returns a code from `common/err` or a trailing `false`; none of them is silent.

## Limits

`AH_CAP` (24 agents) is the fixed table: the 25th spawn returns `E_NO_SPACE`, driven by `t97` and `t104`. `CH_SLOTS` (16 queued messages) is driven by `t79_limit_drivers`. The generated limit table with the test behind each row is `os-build/layer1/LIMITS.md`.

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

- Boot. The table has never been instantiated by the kernel; every run is a host process.
- Restart continuity. The table is process memory: a supervisor restart loses every handle, grant and queued message. Named in `os-build/layer1/r11/agenthost.md` §3.
- More than one CPU. The table has no lock; it assumes the scheduler runs it on one core.

## Deviations

- No `svc_entry`. The spawn signature is not published (Q-B-L1-4), so a `service_main` would be guessing at its own arguments. The functions are the body a `service_main` will wrap.
