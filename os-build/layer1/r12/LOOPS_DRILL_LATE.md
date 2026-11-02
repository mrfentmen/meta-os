# Hosted loop drills — R12-023 (STOP) and R12-024 (budget)

Pass: **late STOP at 40 ms for single-process loops**.

Run at 2026-11-02T15:12:54.897Z. **FAIL**

STOP poll was **2 ms** for this drill (production default **100 ms**, stated because it changes
what the fast loops can prove).

| loop | stop filed mid-run | outcome | stopped reason | exit | duration | no orphan |
|---|---|---|---|---|---|---|
| `imperium-patrol` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 13 ms | true |
| `watch` | false | **finished-before-stop** | — | 0/null | 42 ms | true |
| `aegis` | false | **finished-before-stop** | — | 0/null | 41 ms | true |
| `aegis-cycle` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 10 ms | true |
| `nervus` | true | **stop-filed-no-halt** | — | 0/null | 42 ms | true |
| `handsfree-intake` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 43 ms | true |
| `handsfree-brief` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 44 ms | true |
| `handsfree-approval` | true | **stopped-mid-run** | stop-file | 0/null | 42 ms | true |

Budget drill: `nervus` capped at **20 ms** against a real run
that costs longer. Runtime receipt: `budget-wall-clock` cap 20; registry cap unchanged at 120000 ms. **PASS**

## What this does not claim

- A loop that finished before the STOP landed did not halt mid-run. Those rows say
  `finished-before-stop`; their guaranteed path is the pre-spawn STOP (`tests/r12-loops`).
- No kernel, no supervisor, no signal delivered by anything but the host runtime.
