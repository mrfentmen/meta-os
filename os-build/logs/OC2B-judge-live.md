# OC2B-411 Judge v2 live re-proof — DEGRADED (single attempt, no retry)

Setup: staged crew review end to end with `TRIO_JUDGE_MODEL=1` and the
real key. Staged assess/fetch/dispatch seams (assess returns staged
`visible flame` readings; dispatch is an injected stub returning a
`sim-` receipt); records in scratch dir `/tmp/oc2b17/judge-live-records`
(kept out of the repo). `server/queue` NOT edited. Receipt: scratch
file `receipts-judgelive.jsonl` (copied into
`OC2B-model-receipts-index.md`).

Timeline excerpt (incident `incident-e3f900a5fe68661b`, review step):

- `verdict: confirmed`, `judge_mode: deterministic` (NOT `model`)
- `judge_reasons[0]: "model judge unavailable (muse-spark-1.3 response
  carried no message content); deterministic ruling used"`
- `judge_reasons[1]: "two independent readings agree on 'visible flame'"`
- outcome: `dispatched-simulated` (stub receipt
  `sim-oc2b-judge-live-001`)

Exact error: the judge's prompted Spark call reached the API and came
back (receipt: `chat:muse-spark-1.3`, 389 prompt + 1200 completion
tokens with 1198 reasoning, 5567 ms, est $0.005586) but the payload
carried no message content, so `models.chat_text` raised
`RuntimeError: muse-spark-1.3 response carried no message content`.
Same signature as the OC2B-408 Wonder failure (reasoning tokens spent,
no message) — the account flaked on 2 of 8 calls this session. One
attempt per the fence; no retry; moving on.

What this still proves: the v2 wiring works live — the judge ATTEMPTED
its prompted call under the flag and the named deterministic fallback
decided instead of guessing. Prior art: Pax's sandbox judge smoke
(MODEL_INTEGRATION.md) returned "confirm / visible flame" with
`judge_mode: model` semantics verified; this run did not reproduce the
`model` branch. `judge_mode: model` on this Mac: UNPROVEN this run.

ADDENDUM — `judge_mode: model` WAS proven live later the same session
by the OC2B-419 patrol dry run (same `TRIO_JUDGE_MODEL=1` wiring, real
Spark judge call over two real Spark vision readings): verdict
`confirmed`, `judge_mode: model`, with model reasons quoting both
readings ("vehicle fire with 0.97-0.98 confidence"). Timeline excerpt
and receipt: `os-build/logs/OC2B-patrol-live/incident.json` (review
step) and `OC2B-model-receipts-index.md` (receipts-patrol group).
The standalone minimal-harness attempt above stays recorded as the
flaked single attempt it was.
