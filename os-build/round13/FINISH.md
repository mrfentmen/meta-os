# Round 13 — finish record

500 tasks, one branch (`buffy/round13`), one line per section. This file separates what is
**proven**, what is a **record**, and what is still a **gap**.

| section | state | counts |
|---|---|---|
| services contract depth | **COMPLETE** | 25 / 25 audited; 39 gaps |
| services failure paths | **COMPLETE** | 25 / 25; 23 gaps, 2 observed |
| services restart/state | **COMPLETE** | 10 / 10; 1 drilled, 9 gaps |
| services third ring | **COMPLETE** | 25 / 25; **0 pairs exist**, 1 live permission (dhcp→net, unused) |
| Aegis OSV sweeps | **COMPLETE** | 25 / 25; 10 real manifests, 15 missing, 107 refs, **0 findings**, control passed |
| Aegis KEV cross-check | **COMPLETE** | 25 / 25; 0 findings to check, feed 2026.10.30 (1,766 entries), control passed |
| secret hygiene counts | **COMPLETE** | 25 / 25; 241 matches (240 env mentions, **1 bearer review item**), self-check passed |
| surface/unicode | **COMPLETE** | 25 / 25; 16 scanned (1.9 M chars), 9 missing artifacts, **0 findings** |
| Aegis OSINT | **COMPLETE** | 25 / 25; 15 passes run, 9 not implementable, 1 unavailable; **2 findings** (NXDOMAIN, soft 404) |
| Aegis OPSEC | **COMPLETE** | 25 / 25; 20 decided, 3 not inspectable, 2 n/a; **4 failures, 6 findings** |
| agent runtime: supervisor | **COMPLETE** | 25 / 25; 19 observed, 2 refused, 1 not exercised, 3 gaps; **5 findings** |
| baton-pass proofs | **COMPLETE** | 25 / 25; 4 proven by passing tests, **21 gaps** (no per-loop fixture, no tree diff) |
| agent runtime: STOP/budget | **COMPLETE** | 25 / 25; 12 observed, 9 observed-gap, 4 gaps |
| agent runtime: death/recovery | **COMPLETE** | 25 / 25; 21 observed, 2 observed-gap, 2 gaps |
| chaos over the loops | **COMPLETE** | 25 / 25; 11 observed, 9 observed-gap, 5 gaps |
| Hands-Free intake | **COMPLETE** | 25 / 25; **25 tests pass**, 14 findings, 3 fences checked |
| Nuntius relay | **COMPLETE** | 25 / 25; **25 tests pass**, 8 findings |
| Nuntius board | **COMPLETE** | 25 / 25; **25 tests pass**, 4 findings, DOM dumps in `dom/` |
| userspace | **WRITTEN — CHECK BLOCKED** | 25 / 25 sources; 19 implemented, 1 partial, 6 ABI-blocked; `cargo check` blocked on this host's toolchain |
| federation + closeout | NOT STARTED | 0 / 25 |

## Proven (ran here, output exists)

- 130 test assertions across the P/R/K–L suites, 0 failing (`FULL_LANE_TEST_RUN.md`).
- 75 loop drills with real processes and ledgers; every budget cap below cost fired and left no orphan.
- 50 Nuntius cases against the live services; 25 Hands-Free cases against the real intake path.
- A watchman death is detected by `checkBeat()` in ~250–350 ms, measured from the kill.

## Record (a gap written down, not a pass)

- 0 of 25 cross-service pairs exist; 4 services are executable.
- 0 findings from the OSV and KEV sweeps over what does exist, with positive controls proving the sweeps work.
- 25 userspace programs, none compiled here; 6 name a syscall the ABI does not have.
- 15 federation drills, all SIMULATED; there is no federation module.

## Gap (no artifact, no run)

- There is no cadence loop and no federation module in this repo.
- Nothing restarts the watchman.
- `patrol.py` does not terminate.
- Nothing in this round was compiled or booted. The Mac gate owns both.
