# Spark-down drill: INT-008 (Pax, 2026-10-27)

Script: `intel/spark_down_drill.py`. Transcript:
`intel/evals/spark_down.log`. Tests:
`tests/test_intel_spark_down.py`.

Run it (from the repo root):

```
python3 intel/spark_down_drill.py
```

The drill, in order: it points the shipped SparkClient
over the shipped HTTP transport at a closed localhost
port, then runs every Spark-touching feature against that
dead endpoint on one fixture snapshot (2 messages, 1
stalled claimed job, 1 blocked job, clock 10000).

## Results from the landing run

| Feature | Endpoint down gives | Engaged |
| --- | --- | --- |
| Brief, normal path | Template brief, TEMPLATE first line, 54 words inside the 220-word morning budget, blocked job named | Yes |
| Brief, Spark-only path | The canned BRF-026 spark_down line, verbatim | Yes |
| Brief record | Dry-run record model is template, not spark, because the template wrote the text | Yes |
| Dispatch | FALLBACK plan: one job, raw goal in the spec, endpoint-down warning on stderr and in the result, endpoint called exactly once, nothing posted, $0 spent | Yes |
| Watchdog | 1 alert (progress-stall), template explanation identical with the down polish client and with no polish client | Yes |
| CLI | intel.py brief --morning exits 0 with a template brief, no traceback | Yes |

## What changed to make the drill pass

Dispatch did not fall back before this batch: DSP-017
pinned a transport error to propagate unchanged, so an
endpoint-down dispatch raised instead of falling back.
INT-008 amends that rule: a transport error from the
completion callable now returns the same FALLBACK plan
with an endpoint-down warning. A structured plan that
fails a guard still raises PlanError with no retry and
no fallback; only the no-answer case falls back. The
fallback still needs DSP-007 human approval before
anything posts, so the outage is visible to the
approver instead of silent.

The brief record change is the same honesty fix on the
brief side: generate_brief used to record model spark
whenever a client was passed, even when the call failed
and the template wrote the text. It now records
template when the text carries the TEMPLATE first line,
so the stored record cannot label template text as
Spark-composed.

## What it proves, and what it does not

- Proved: with the endpoint dead, no feature crashes,
  no feature posts anything, no feature spends anything,
  and every user-visible surface says the honest thing
  (template marker, canned down line, FALLBACK marking).
- Proved: the failure itself is real, not stubbed. The
  precondition stage raises SparkError from the shipped
  transport against a closed port (connection refused).
- Not proved: a live endpoint failing in other ways
  (slow responses, 500s, malformed bodies). The HTTP
  transport retries 429/5xx per FND-006 and raises
  SparkResponseError on a non-JSON body; those paths
  feed the same fallbacks (brief catches any exception,
  dispatch catches any exception from the callable,
  polish keeps the template), but this drill exercises
  only the unreachable case. The Redis-outage drill is
  INT-009, landed in intel/evals/redis_down.md, and is
  a separate failure from this one: this drill never
  touches Redis except through the in-memory fake
  surface for the record and CLI stages.
- Not proved: dashboard rendering in a browser. The
  honest states asserted here are the exact strings
  the dashboard renders verbatim (template text, canned
  line, FALLBACK marking); the viewer panels that
  render them are Rowan's lane, not this drill.
