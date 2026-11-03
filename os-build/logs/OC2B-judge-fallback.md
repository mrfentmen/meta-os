# OC2B-412 Judge fallback proof — PASS

Setup: identical staged review to OC2B-411, except the scratch env
carries an invalid placeholder as the key value (a forced transport
failure standing in for "bad endpoint"; `server/queue` NOT edited,
real key never left the key file). `TRIO_JUDGE_MODEL=1` still set, so
the judge first attempts its prompted call.

Timeline excerpt (incident `incident-e96fd45b9139d6d4`, review step):

- `verdict: confirmed`, `judge_mode: deterministic`
- `judge_reasons[0]: "model judge unavailable (model request
  (chat:muse-spark-1.3) failed with HTTP 401); deterministic ruling
  used"`
- `judge_reasons[1]: "two independent readings agree on 'visible flame'"`
- outcome: `dispatched-simulated` (stub receipt
  `sim-oc2b-judge-fallback-001`)

The fallback is NAMED on the timeline (`model judge unavailable ...
deterministic ruling used`), exactly the contract `crew._run_review`
implements. No receipt was written for the failed call (receipts are
written only after a payload arrives), which is itself correct: no
spend on a failed call. Full staged timeline (flag → decision →
review → reported → decision → investigation ×2 → brief → bolo →
dispatch) saved in the run JSON held with the receipts index source.
