# OC2B-417/418 receipts index + §17 spend total

Receipts were written to scratch files via `METAOS_MODEL_RECEIPTS`
(one per call group), then indexed here. Source files (in
`/tmp/oc2b17/`, held with the runner scripts; contents indexed
verbatim below):

- `receipts-sam.jsonl` (3 lines) — OC2B-401/403/404
- `receipts-wiring.jsonl` (1 line) — OC2B-406
- `receipts-wonder.jsonl` (3 lines) — OC2B-407/408/409
- `receipts-judgelive.jsonl` (1 line) — OC2B-411
- `receipts-image.jsonl` (2 lines) — OC2B-413/414
- `receipts-patrol.jsonl` (2 lines) — OC2B-419
- `receipts-judgefallback.jsonl` — 0 lines (correct: the forced-401
  call failed before any payload arrived, so no receipt; no spend)

| # | model | purpose | est cost |
|---|---|---|---|
| 1 | sam-3.1 | OC2B-401 frame1 segment (no-box) | null (images_processed: 1) |
| 2 | sam-3.1 | OC2B-403 frame2 segment (box) | null (images_processed: 1) |
| 3 | sam-3.1 | OC2B-404 frame3 segment (no-box) | null (images_processed: 1) |
| 4 | sam-3.1 | OC2B-406 patrol wiring segment (no-box) | null (images_processed: 1) |
| 5 | muse-wonder-1.0 | OC2B-407 agree-case judge ruling | null (738 tokens) |
| 6 | muse-wonder-1.0 | OC2B-408 disagree-case judge ruling (no message content — failure, usage still recorded) | null (1533 tokens) |
| 7 | muse-wonder-1.0 | OC2B-409 emergency-tier judge ruling | null (1079 tokens) |
| 8 | muse-spark-1.3 | OC2B-411 judge-live prompted ruling (no message content — failure, usage still recorded) | $0.005586 |
| 9 | muse-image-1.0 | OC2B-413 lab scene GENERATED | null (11,388 tokens, 7,936 cached) |
| 10 | muse-image-1.0 | OC2B-414 workshop scene GENERATED | null (11,485 tokens, 7,936 cached) |
| 11 | muse-spark-1.3 | OC2B-419 patrol dry-run judge ruling (judge_mode: model) | $0.004200 |
| 12 | sam-3.1 | OC2B-419 patrol dry-run segment (no-box) | null (images_processed: 1) |
| 13 | muse-spark-1.3 | OC2B-419 patrol assess (vision, direct transport — recorded in guardrail state, not a models receipt line) | ≈ $0.027 (half of the $0.058133 pass delta minus receipted judge/SAM) |
| 14 | muse-spark-1.3 | OC2B-419 review assess (vision, direct transport — same note) | ≈ $0.027 |

Only Muse Spark carries a published rate card, so only Spark rows
carry dollar estimates; all other rows carry raw usage (recorded in
each receipt line). Transcribe probes (OC2B-416) produced no receipts
(direct HTTP probes + a local raise; no model spend).

## §17 spend total (OC2B-418)

- §17-attributable Spark estimate: **≈ $0.064** ($0.005586 + $0.004200
  receipted + ≈ $0.053933 for the two vision assessments, derived from
  the patrol pass's $0.058133 guardrail delta).
- Guardrail-wide cumulative after §17: $0.151912 of the $75 budget
  ($74.8481 remaining) — shared with parallel lanes; §17 is a small
  fraction of it.
- Verdict: **under Del's cap with headroom of ~$74.85.**

Full receipt lines (verbatim copies from the scratch files above):

```
{"kind": "segment:sam-3.1", "model": "sam-3.1", "surface": "responses", "usage": {"images_processed": 1, ...}, "latency_ms": 643, "est_cost_usd": null}
{"kind": "segment:sam-3.1", "model": "sam-3.1", "surface": "responses", "usage": {"images_processed": 1, ...}, "latency_ms": 1412, "est_cost_usd": null}
{"kind": "segment:sam-3.1", "model": "sam-3.1", "surface": "responses", "usage": {"images_processed": 1, ...}, "latency_ms": 572, "est_cost_usd": null}
{"kind": "segment:sam-3.1", "model": "sam-3.1", "surface": "responses", "usage": {"images_processed": 1, ...}, "latency_ms": 1468, "est_cost_usd": null}
{"kind": "chat:muse-wonder-1.0", "model": "muse-wonder-1.0", "surface": "chat", "usage": {"prompt_tokens": 339, "completion_tokens": 399, "total_tokens": 738, ...}, "est_cost_usd": null}
{"kind": "chat:muse-wonder-1.0", "model": "muse-wonder-1.0", "surface": "chat", "usage": {"prompt_tokens": 333, "completion_tokens": 1200, "total_tokens": 1533, ...}, "est_cost_usd": null}
{"kind": "chat:muse-wonder-1.0", "model": "muse-wonder-1.0", "surface": "chat", "usage": {"prompt_tokens": 389, ...}, "est_cost_usd": null}
{"kind": "chat:muse-spark-1.3", "model": "muse-spark-1.3", "surface": "chat", "usage": {"prompt_tokens": 389, "completion_tokens": 1200, "total_tokens": 1589}, "latency_ms": 5567, "est_cost_usd": 0.00558625}
{"kind": "image:muse-image-1.0", "model": "muse-image-1.0", "surface": "responses", "usage": {"input_tokens": 10239, "output_tokens": 1149, "total_tokens": 11388}, "latency_ms": 11870, "est_cost_usd": null}
{"kind": "image:muse-image-1.0", "model": "muse-image-1.0", "surface": "responses", "usage": {"input_tokens": 10296, "output_tokens": 1189, "total_tokens": 11485}, "latency_ms": 12347, "est_cost_usd": null}
{"kind": "chat:muse-spark-1.3", "model": "muse-spark-1.3", "surface": "chat", "usage": {"prompt_tokens": 902, "completion_tokens": 723, "total_tokens": 1625}, "latency_ms": 4018, "est_cost_usd": 0.00420025}
{"kind": "segment:sam-3.1", "model": "sam-3.1", "surface": "responses", "usage": {"images_processed": 1, ...}, "latency_ms": 1072, "est_cost_usd": null}
```

(Usage objects abridged to the token counts that carry the audit
signal; full lines live in the scratch files above. Receipt count:
12 lines.)
