# Buffy — Round 12 status

Branch `buffy/round12`, based on main `77e0a10` with the finished round-11 branch merged
(`fb98bba`). Task list: `BUFFY_TASKS_ROUND12.md` (44 tasks).

| section | state | counts | evidence |
|---|---|---|---|
| A — the 14 | **DONE** | 14 / 14 | `os-build/layer1/r12/SECTION_A.md` |
| B — Aegis live fire | **NOT STARTED** | 0 / 6 | — |
| C — loops hardened | **PARTIAL** | 1 done, 1 partial / 6 | R12-026 done, R12-023 pre-spawn only; `CHAOS_COVERAGE.md` |
| D — services second ring | **NOT STARTED** | 0 / 9 | — |
| E — Nervus + Hands-Free | **NOT STARTED** | 0 / 5 | — |
| F — proof and closeout | **NOT STARTED** | 0 / 4 | — |

## Section A numbers

- OSV sweep: 23 manifests, 108 versioned refs, 2 batches, **0 findings** (direct API under Pax's exception).
- KEV: **0 sweep findings** checked, 0 flagged; 7 non-sweep OSINT records excluded.
- Second sweep: 108 refs, 0 findings; diff **0 added / 0 removed / 7 unchanged**.
- OSINT: 4 domains, CT certs 0/2/0/8, distinct names 0/2/0/5, **3 findings**; clipraiders.com does not resolve.
- Watch targets: **169** (165 repos + 4 pages), all `UNVERIFIED`.
- Hosted loops: Imperium **PASS** (queue up, agent exit 0, dispatch HTTP 201), Cadence exit 0.

## Tests on this branch tip

```
node --test (r12-loops, agents-r11, chaos, aegis-r11, aegis-sweep, aegis-findings,
             handsfree-r11, nervus-r11)
54 tests, 54 pass, 0 fail
```

## Not claimed

- No kernel or boot proof: `hog` and `quitter` compile, they are not in `BINS`, and nothing was booted.
- No assessment from Imperium: no model key exists here; the receipt says exactly that.
- No mid-run STOP proof for the fast hosted loops (50 ms runs cannot outlive the 100 ms poll); the
  pre-spawn STOP is the proven path for every loop.
