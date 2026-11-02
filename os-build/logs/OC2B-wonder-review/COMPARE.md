# OC2B-410 Wonder vs deterministic combine() (OC2B-407–409 inputs)

Model: `muse-wonder-1.0` via `judge.rule_with_model` (`models.chat_text`),
one call per case, no retries. Deterministic column: `judge.combine()`
evaluated locally on the same staged inputs (no model call).

| case | staged readings | model verdict | deterministic verdict | match? |
|---|---|---|---|---|
| case1 agree (visible flame + visible flame) | confirmed / visible flame, tier high | confirmed: "two independent readings agree on 'visible flame'" | YES |
| case2 disagree (visible flame + steam or fog) | TRANSPORT FAILURE — `RuntimeError: muse-wonder-1.0 response carried no message content` (payload arrived, 1200 completion tokens, no message content; single attempt, no retry; full error in `case2/case.json`) | cleared: "the review reading landed on the baseline category 'steam or fog'; the flag reads as a look-alike" | n/a — no model verdict to compare; the deterministic ruling stands as the fallback, exactly as the crew's `_run_review` fallback would use it |
| case3 emergency/flame tier (structure fire + visible flame) | confirmed / structure fire, tier high | confirmed: "the patrol reading was 'structure fire' and the review reading independently flagged 'visible flame'; two flagged readings stand over one" | YES |

Tiers via `crew_common.priority_for_category`: visible flame → high,
structure fire → high (both RED tier).

Takeaway: where Wonder answered (2/3), its verdict agreed with
`combine()` on both the ruling and the flagged category. The case2
failure is itself evidence for the fallback design: a garbled/empty
model reply must never confirm, and `combine()` decides instead.
Receipts: scratch file `receipts-wonder.jsonl` (3 lines, all Wonder,
copied into `OC2B-model-receipts-index.md`).
