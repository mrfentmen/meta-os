# Buffy — Round 13 status

Branch `buffy/round13`, cut from `origin/main` at `c5a80252`. Task list:
`BUFFY_TASKS_ROUND13_500.md` (500). One line per section; details in the evidence path.

| section | state | counts | evidence |
|---|---|---|---|
| A — services contract depth | **COMPLETE** | 25 / 25 audited; 39 gaps | `os-build/round13/SECTION_A.md` |
| B — services failure paths | **COMPLETE** | 25 / 25; 23 gaps, 2 observed | `os-build/round13/failures/SECTION_B.md` |
| C — services restart/state | **COMPLETE** | 10 / 10; 1 drilled, 9 gaps | `os-build/round13/restarts/SECTION_C.md` |
| D — services third ring | NOT STARTED | 0 / 25 | — |
| E–J — Aegis | NOT STARTED | 0 / 150 | — |
| K–O — agent runtime | NOT STARTED | 0 / 75 | — |
| P — Hands-Free | NOT STARTED | 0 / 25 | — |
| Q–R — Nuntius | NOT STARTED | 0 / 50 | — |
| S — userspace | NOT STARTED | 0 / 25 | — |
| T — federation + closeout | NOT STARTED | 0 / 25 | — |

**Sections A–C:** 60 / 60 addressed — 71 gaps filed, 3 observed with evidence
(`t140_r13_failpaths_b` pass=9/0; R13-060 heartbeat kill/restart drill with hashes).

## Method

Section A audits read the README, the source declarations, and a facet-specific grep. A missing
facet is filed as a gap; it is never papered over with a fabricated contract. Gap records live in
the service folder as `GAPS_R13.md`.

Sections B and C apply the same rule to failure inputs and restart state: a condition with no
callable surface or no process is a gap, not a simulated test. The one real restart drill (R13-060)
has before/after SHA-256 values in `os-build/round13/restarts/R13-060.log`.
