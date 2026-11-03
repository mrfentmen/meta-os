# Buffy — Round 13 status

Branch `buffy/round13`, cut from `origin/main` at `c5a80252`. Task list:
`BUFFY_TASKS_ROUND13_500.md` (500). One line per section; details in the evidence path.

| section | state | counts | evidence |
|---|---|---|---|
| A — services contract depth | **COMPLETE** | 25 / 25 audited; 39 gaps | `os-build/round13/SECTION_A.md` |
| B — services failure paths | **COMPLETE** | 25 / 25; 23 gaps, 2 observed | `os-build/round13/failures/SECTION_B.md` |
| C — services restart/state | **COMPLETE** | 25 / 25; 1 drilled, 24 gaps | `os-build/round13/restarts/SECTION_C.md` |
| D — services third ring | **COMPLETE** | 25 / 25; **0 pairs exist**, 1 live permission (dhcp→net, unused) | `os-build/round13/pairs/SECTION_D.md` |
| E — Aegis OSV sweeps | **COMPLETE** | 25 / 25; 10 real manifests, 15 missing, 107 refs, **0 findings**, control passed | `os-build/round13/aegis/SECTION_E.md` |
| F — Aegis KEV cross-check | **COMPLETE** | 25 / 25; 0 findings to check, feed 2026.10.30 (1,766 entries), control passed | `os-build/round13/aegis/SECTION_F.md` |
| G — secret hygiene counts | **COMPLETE** | 25 / 25; 241 matches (240 env mentions, **1 bearer review item**), self-check passed | `os-build/round13/aegis/SECTION_G.md` |
| H — surface/unicode | **COMPLETE** | 25 / 25; 16 scanned (1.9 M chars), 9 missing artifacts, **0 findings** | `os-build/round13/aegis/SECTION_H.md` |
| I — Aegis OSINT | **COMPLETE** | 25 / 25; 15 passes run, 9 not implementable, 1 unavailable; **2 findings** (NXDOMAIN, soft 404) | `os-build/round13/aegis/SECTION_I.md` |
| J — Aegis OPSEC | **COMPLETE** | 25 / 25; 20 decided, 3 not inspectable, 2 n/a; **4 failures, 6 findings** | `os-build/round13/aegis/SECTION_J.md` |
| K — agent runtime: supervisor | **COMPLETE** | 25 / 25; 19 observed, 2 refused, 1 not exercised, 3 gaps; **5 findings** | `os-build/round13/agents/SECTION_K.md` |
| L — baton-pass proofs | **COMPLETE** | 25 / 25; 4 proven by passing tests, **21 gaps** (no per-loop fixture, no tree diff) | `os-build/round13/agents/SECTION_L.md` |
| M — agent runtime: STOP/budget | **COMPLETE** | 25 / 25; 12 observed, 9 observed-gap, 4 gaps | `os-build/round13/agents/SECTION_M.md` |
| N — agent runtime: death/recovery | **COMPLETE** | 25 / 25; 21 observed, 2 observed-gap, 2 gaps | `os-build/round13/agents/SECTION_N.md` |
| O — chaos over the loops | **COMPLETE** | 25 / 25; 11 observed, 9 observed-gap, 5 gaps | `os-build/round13/agents/SECTION_O.md` |
| P — Hands-Free intake | **COMPLETE** | 25 / 25; **25 tests pass**, 14 findings, 3 fences checked | `os-build/round13/handsfree/SECTION_P.md` |
| Q — Nuntius relay | **COMPLETE** | 25 / 25; **25 tests pass**, 8 findings | `os-build/round13/nuntius/SECTION_Q.md` |
| R — Nuntius board | **COMPLETE** | 25 / 25; **25 tests pass**, 4 findings, DOM dumps in `dom/` | `os-build/round13/nuntius/SECTION_R.md` |
| S — userspace | **WRITTEN — CHECK BLOCKED** | 25 / 25 sources; 18 implemented, 1 partial, 6 ABI-blocked; `cargo check` blocked on this host's toolchain | `os-build/round13/userspace/SECTION_S.md` |
| T — federation + closeout | **COMPLETE** | 15 SIMULATED drills + 10 closeout docs; 19 labelled records | `os-build/round13/federation/SECTION_T.md`, `FINISH.md` |

**Sections A–T:** 500 / 500 addressed (S is written and committed; its `cargo check` is a host-toolchain gap, so nothing in S is called compiled or booted) — 71 gaps (A–C), 25 pair gaps (D), 15 missing manifests
(E), 9 missing artifacts (H), 9 unimplemented OSINT angles (I), 21 baton gaps (L), 1 review
item (G), 4 real observations (D/E), 2 OSINT findings (I), 6 OPSEC findings (J), 5 runtime
findings (K), 4 loop findings (M–O: no restart supervisor, a missing cwd kills the caller,
no singleton guard, no injectable env/clock seam). Agent suite: 21 tests, 21 pass.

## Method

Every section uses the same rule: an input that does not exist is a gap record, never a
simulated pass. Four tools were written for this round and are committed, so each count can
be regenerated:

| tool | what it decides |
|---|---|
| `os-build/layer1/pair_audit.py` | bootability, imports and the callmatrix bit for 25 named pairs |
| `os-build/layer1/manifest_sweep.py` | OSV over every real dependency manifest, with a positive control |
| `os-build/layer1/kev_crosscheck.py` | KEV flags per finding, feed hash, positive control |
| `os-build/layer1/secret_counts.py` | secret-shape counts over commit ranges and trees, with a self-check |
| `os-build/layer1/surface_passes.mjs` | surface + confusable passes over named artifacts |
| `os-build/layer1/osint_passes.py` | OSINT angles parsed from the task list, counts only |
| `os-build/layer1/opsec_checks.py` | 25 OPSEC checks, mechanical where a command can decide |
| `os-build/layer1/agent_drills.mjs` | 25 runtime drills with real spawns, budgets, STOP files and ledgers |
| `os-build/layer1/loop_drills.mjs` | 75 loop drills: STOP/budget arms, real watchman deaths, chaos faults |
| `handsfree/intake_cases.test.mjs` | 25 intake cases; asserts no line is silently dropped, records the rest |
| `relay/relay.round13.test.mjs` | 25 relay cases against the live loopback service and its CLI |
| `board/board.round13.test.mjs` | 25 board cases, with the served HTML + render JSON dumped as evidence |
| `os-build/userspace/user/src/bin/*.rs` | 25 kernel userspace programs; compile proof is the Mac gate's |

## Limits carried forward

- The service layer is **four executables** (bootlog, console, logd, time) and 21 modules.
  Every document that calls the 25 directories "services" describes intent, not artifact.
  Sections C and D reached this independently.
- Sections E and F used the direct `api.osv.dev` route because `osv-mcp` is not installed on
  this host. The route is stated in every record; a reader who does not accept the standing
  exception should read those 50 rows as BLOCKED.
- R13-152 (one bearer-shaped token, history only, no longer in the tree) is filed for human
  review. Counts cannot close it and Aegis does not auto-fix.

- Only four loops are runnable: aegis, nervus and three handsfree roles. **There is no cadence
  loop in this repo**, and `imperium-patrol` is a draft registry entry whose command is `true`.
  The Imperium drills used the real `server/queue/patrol.py`, which **never terminates**
  (`--once --max-checks 1`, still running at 15 s), so its budget rows measure a 4 s ceiling,
  not a run cost.
- Nothing restarts the watchman. Detection exists (`agents/watchdog.mjs` alarms once, exit 2);
  recovery does not. Every Section N restart is a manual respawn by the drill.
- A missing working directory kills the process that called `spawnAgent`: `runtime.mjs` attaches
  no `'error'` listener to `spawn()`. Proved in a child probe (R13-374), exit 7, uncaught ENOENT.

- The refusal catalogue (`handsfree/refusals.mjs`) is **not wired into `intake.mjs`**: a dispatch
  order that the catalogue refuses is still filed as a job (R13-394). The fence exists as data
  and is never consulted by the path that turns text into work.
- Intake has no size cap, no case normalisation, no verb check and no duplicate check. A pasted
  log, a pasted error and a timestamped line each become orders whose "agent" is `12`, `Error`
  and `2026-11-02 14` (R13-397..399). A spoken `STOP` is filed as work, not as a stop (R13-389).

- `cargo check` for the userspace crate cannot pass on this host: the installed cargo is Homebrew
  1.99.1 with no `x86_64-unknown-none` core, and `rustup run nightly` still resolves a stable rustc
  that refuses `-Z build-std`. Both attempts are in `os-build/round13/userspace/CARGO_CHECK.txt`.
  Nothing in Section S is compiled, and no boot behaviour is claimed.
- Six Section S programs name syscalls the ABI does not have (argv, spawn, wait, kill, mmap,
  process list). They are committed as executable gap records; `PROPOSALS.md` carries the proposal.
