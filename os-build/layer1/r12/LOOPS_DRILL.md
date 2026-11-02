# Hosted loop drills — R12-023 (STOP) and R12-024 (budget)

Pass: **early STOP at 5 ms for every loop**.

Run at 2026-11-02T15:12:54.558Z. **PASS**

STOP poll was **2 ms** for this drill (production default **100 ms**, stated because it changes
what the fast loops can prove).

| loop | stop filed mid-run | outcome | stopped reason | exit | duration | no orphan |
|---|---|---|---|---|---|---|
| `imperium-patrol` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 12 ms | true |
| `watch` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 8 ms | true |
| `aegis` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 7 ms | true |
| `aegis-cycle` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 8 ms | true |
| `nervus` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 7 ms | true |
| `handsfree-intake` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 8 ms | true |
| `handsfree-brief` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 7 ms | true |
| `handsfree-approval` | true | **stopped-mid-run** | stop-file | null/SIGTERM | 7 ms | true |

Budget drill: `nervus` capped at **20 ms** against a real run
that costs longer. Runtime receipt: `budget-wall-clock` cap 20; registry cap unchanged at 120000 ms. **PASS**

## What this does not claim

- A loop that finished before the STOP landed did not halt mid-run. Those rows say
  `finished-before-stop`; their guaranteed path is the pre-spawn STOP (`tests/r12-loops`).
- No kernel, no supervisor, no signal delivered by anything but the host runtime.
