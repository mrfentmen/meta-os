# Cost check: INT-007 (Pax, 2026-10-27)

Script: `intel/cost_check.py`. Transcript: `intel/evals/cost.log`.
Tests: `tests/test_intel_cost.py`.

Demo-day call inventory, from plan/DEMO.md: morning brief
(Shot 2, 1 call), dispatch plan (Shot 5, 1 call, 2 in the
worst case because plan_from_spark retries once on
malformed JSON), closing brief (Shot 11, 1 call), alert
polish (Shots 8/8b, 2 calls, 3 in the worst case with the
optional Shot 10 collision alert), boot brief (Shot 0,
only if OS-004 rules go; kept out of the headline total).

Token model: the client's own _estimate_tokens (about 4
chars per token) on the exact text each call would send.
Brief prompts are built exactly as compose_brief builds
them, from the real extractors over a 5-job demo snapshot.
Dispatch input is intel/prompts/dispatch.md plus the locked
demo goal; the caller's exact assembly is not in this repo,
so the documented prompt file plus goal is the measured
proxy, stated here. Expected output for a brief is the
template brief for the same snapshot, measured (same word
budget a Spark brief is trimmed to); dispatch expected
output is a labeled 300-token proxy; polish output is one
sentence, measured. Worst-case output is 1024 tokens per
call, the default max_tokens every call site passes.

| call | base | worst | tokens in | tokens out (expected) | $ expected | $ worst |
| --- | --- | --- | --- | --- | --- | --- |
| morning brief (Shot 2) | 1 | 1 | 244 | 177 | 0.0034 | 0.0161 |
| dispatch plan (Shot 5) | 1 | 2 | 3070 | 300 | 0.0137 | 0.0491 |
| closing brief (Shot 11) | 1 | 1 | 244 | 177 | 0.0034 | 0.0161 |
| alert polish (Shots 8/8b) | 2 | 3 | 54 | 15 | 0.0008 | 0.0466 |
| boot brief (Shot 0, OS-004 go only) | 0 | 1 | 244 | 177 | 0.0000 | 0.0161 |

Totals at the client's estimate rates ($3/Mtok in,
$15/Mtok out): expected demo day $0.0213, worst demo day
$0.1279, worst with boot brief $0.1440. Headroom against
the $75 reserved half (GOV-001: $75 build/testing plus
$75 reserved for the presentation) is $74.8560.

What this proves, and what it does not:

- Proved: the headroom shape. Even the worst case, with
  the boot brief and every retry and optional alert, is
  0.2 percent of the reserved half. Real rates would have
  to exceed the placeholder rates by 520x before the
  reserved half is breached.
- Also proved: on the primary agent transport the API
  spend is $0 by the client's own rule (agent calls carry
  no API cost; est_cost is null unless the agent reports
  counts). The dollar totals above are the HTTP fallback
  case, not the primary path.
- Not proved: that demo day fits the $150 credit as a
  fact. The rates are the client's defaults, which its
  source labels "Planning placeholders for cost estimates
  only, NOT pricing facts." No live Spark call was made,
  no ledger entry exists to project from (the ledger
  holds no live spend because live transport is blocked),
  and GOV-001 (which endpoint and key) stays unnamed.
  This check sizes the contingency; it does not unblock
  GOV-001, and real pricing must be re-checked the day a
  real endpoint and key exist.
