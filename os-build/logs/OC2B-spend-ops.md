# OC2B-251..254/261/262 — Spend sources, caps, ops (no key this session)

## Sources (251) → guardrail coverage (252)

| source | reports to guardrail? |
|---|---|
| `spark_gen` direct transport (`generate` → `estimate` → `log`) | YES — `spark_gen.py` calls `spark_guardrail` before/after each call |
| `trio_agent` model path (`generate` per served job) | YES — same transport |
| `livehunt` bounded flags | YES — via crew→models path |
| patrol governor reserve ($5) | YES — pauses before sending, no silent spend |
| DEV helper path (`TRIO_SPARK_VIA_HELPER=1`) | NO (by design) — counted by the helper's own `guardrail_state.json`, out of scope for the ISO transport |

## Caps (253/254) — enforced, not advisory

- Hard stop $75 (`spark_guardrail.py`: `TEST_BUDGET_USD`, `GuardrailStop`
  raised refuse-before-send). Verified in-process by
  `test_spark_guardrail_refusal` (green in 629-suite).
- Patrol reserve $5 (`patrol.py` governor; `paused-budget` state).
- Enforcement = code raise before any POST (no post-hoc accounting).

## Ops (261/262) — check/raise/lower caps, who may raise

- Check: read `spark_guardrail_state.json` (`calls`, `est_cost_usd`).
- Lower: edit cap constants, reinstall (units are code, not config).
- Raise: BOSS ONLY, requires a logged decision
  (`OC2B-spend-raise.txt` — no raises logged this session).
- Alerts fire BEFORE the cap (refuse-before-send), delivery = the
  raised exception + journal line (no pager in tree).

## This-session totals (257/258/270)

Spend: $0.00 — zero live model calls (no key in env; 402 stands).
Unattributable spend: $0.00 (nothing spent, nothing unattributed).
Totals labelled ESTIMATE-at-Spark-rates per-call when calls resume.
