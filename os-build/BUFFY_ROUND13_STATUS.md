# Buffy — Round 13 status

Branch `buffy/round13`, cut from `origin/main` at `c5a80252`. Task list:
`BUFFY_TASKS_ROUND13_500.md` (500). One line per section; details in the evidence path.

| section | state | counts | evidence |
|---|---|---|---|
| A — services contract depth | **COMPLETE** | 25 / 25 audited; 39 gaps | `os-build/round13/SECTION_A.md` |
| B — services failure paths | **COMPLETE** | 25 / 25; 23 gaps, 2 observed | `os-build/round13/failures/SECTION_B.md` |
| C — services restart/state | **COMPLETE** | 10 / 10; 1 drilled, 9 gaps | `os-build/round13/restarts/SECTION_C.md` |
| D — services third ring | **COMPLETE** | 25 / 25; **0 pairs exist**, 1 live permission (dhcp→net, unused) | `os-build/round13/pairs/SECTION_D.md` |
| E — Aegis OSV sweeps | **COMPLETE** | 25 / 25; 10 real manifests, 15 missing, 107 refs, **0 findings**, control passed | `os-build/round13/aegis/SECTION_E.md` |
| F — Aegis KEV cross-check | **COMPLETE** | 25 / 25; 0 findings to check, feed 2026.10.30 (1,766 entries), control passed | `os-build/round13/aegis/SECTION_F.md` |
| G — secret hygiene counts | **COMPLETE** | 25 / 25; 241 matches (240 env mentions, **1 bearer review item**), self-check passed | `os-build/round13/aegis/SECTION_G.md` |
| H — surface/unicode | **COMPLETE** | 25 / 25; 16 scanned (1.9 M chars), 9 missing artifacts, **0 findings** | `os-build/round13/aegis/SECTION_H.md` |
| I — Aegis OSINT | **COMPLETE** | 25 / 25; 15 passes run, 9 not implementable, 1 unavailable; **2 findings** (NXDOMAIN, soft 404) | `os-build/round13/aegis/SECTION_I.md` |
| J — Aegis OPSEC | **COMPLETE** | 25 / 25; 20 decided, 3 not inspectable, 2 n/a; **4 failures, 6 findings** | `os-build/round13/aegis/SECTION_J.md` |
| K — agent runtime: supervisor | **COMPLETE** | 25 / 25; 19 observed, 2 refused, 1 not exercised, 3 gaps; **5 findings** | `os-build/round13/agents/SECTION_K.md` |
| L — baton-pass proofs | **COMPLETE** | 25 / 25; 4 proven by passing tests, **21 gaps** (no per-loop fixture, no tree diff) | `os-build/round13/agents/SECTION_L.md` |
| M–O — agent runtime | NOT STARTED | 0 / 75 | — |
| P — Hands-Free | NOT STARTED | 0 / 25 | — |
| Q–R — Nuntius | NOT STARTED | 0 / 50 | — |
| S — userspace | NOT STARTED | 0 / 25 | — |
| T — federation + closeout | NOT STARTED | 0 / 25 | — |

**Sections A–L:** 300 / 300 addressed — 71 gaps (A–C), 25 pair gaps (D), 15 missing manifests
(E), 9 missing artifacts (H), 9 unimplemented OSINT angles (I), 21 baton gaps (L), 1 review
item (G), 4 real observations (D/E), 2 OSINT findings (I), 6 OPSEC findings (J), 5 runtime
findings (K). Agent suite: 21 tests, 21 pass.

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

## Limits carried forward

- The service layer is **four executables** (bootlog, console, logd, time) and 21 modules.
  Every document that calls the 25 directories "services" describes intent, not artifact.
  Sections C and D reached this independently.
- Sections E and F used the direct `api.osv.dev` route because `osv-mcp` is not installed on
  this host. The route is stated in every record; a reader who does not accept the standing
  exception should read those 50 rows as BLOCKED.
- R13-152 (one bearer-shaped token, history only, no longer in the tree) is filed for human
  review. Counts cannot close it and Aegis does not auto-fix.
