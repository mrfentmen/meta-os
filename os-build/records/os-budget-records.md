# `crates/os-budget` — record shapes, worked examples (B066)

Each block is one record the crate actually produces, with the code
that builds it and a field-by-field reading. Values are from the
crate's own fixtures and pinned tests, not invented.

## 1. Hold entry — `hold_entry` (`lib.rs:331-345`)

```json
{"lane": "spark", "spent": 100, "cap": 100, "held": true}
```

| Field | Meaning | Where it comes from |
|---|---|---|
| `lane` | the budget lane the figures belong to | caller argument |
| `spent` | units spent in the period | caller argument, copied |
| `cap` | the lane's cap for the period | caller argument, copied |
| `held` | new claims are refused | `at_cap(spent, cap)` (`lib.rs:275-282`) |

At 80 of 100 the same builder returns `held: false` — one builder for
both states (test at `lib.rs:2515-2524`).

## 2. Budget-warning alert — `budget_warning_alerts` (`lib.rs:1866-1920`)

```json
{
  "kind": "budget-warning",
  "severity": "warning",
  "lane": "spark",
  "spent": 80,
  "cap": 100,
  "remaining": 20,
  "explanation": "The spark lane has spent 80 of its 100 budget (20 remaining): it is past the 80% warning threshold, so the next claims could hit the cap and stop the lane silently.",
  "suggested_fix": "Slow new spark claims, raise the lane cap, or let the lane finish its current work before posting more — at cap, new claims are held and the job stays open.",
  "dedupe_key": "budget-warning:spark",
  "created_at": 100000
}
```

| Field | Meaning |
|---|---|
| `kind` | alert class; the drill filters on this value |
| `severity` | always `warning`; a cap is a hold, not an alert |
| `lane` / `spent` / `cap` | the figures the detector read |
| `remaining` | `cap - spent`, computed once (`lib.rs:1889`) |
| `explanation` | plain sentence naming lane, spent, cap, remaining, threshold |
| `suggested_fix` | the three options the Python drill prints |
| `dedupe_key` | `budget-warning:<lane>`; one per lane per tick |
| `created_at` | the tick time the caller passed |

Two entries for the same lane in one snapshot yield one alert
(`lib.rs:2612-2620`). At 100/100 the list is empty: the hold replaces
the warning.

## 3. Spend line — `budget_spend_line` (`lib.rs:1922-1964`)

Input:

```json
{"lane": "spark", "spent": 100, "cap": 100, "held": true}
```

with `age_label = " (snapshot time not reported)"`.

Output:

```
Spend: spark lane: 100 of 100 budget (0 remaining) — new claims held (snapshot time not reported)
```

| Part | Rule |
|---|---|
| `Spend: <lane> lane:` | lane must be a non-empty string, else no line |
| `100 of 100 budget (0 remaining)` | spent+cap present |
| `90 remaining of 200 cap` | remaining+cap, no spent |
| `75 remaining` | remaining alone |
| ` — new claims held` | only when `held` is exactly `true` |
| age suffix | caller-supplied; the ET formatter is not ported |

## 4. Forecast entry and line — `forecast_entry` / `forecast_lines` (`lib.rs:419-511`)

```json
{
  "lane": "spark",
  "spent": 80,
  "cap": 100,
  "projected": 240.0,
  "over_cap": true,
  "confidence": "medium",
  "basis": "based on 8 hours of ledger in a 24-hour day"
}
```

| Field | Rule |
|---|---|
| `projected` | `spent * day / elapsed`; at/past the day it is `spent` |
| `over_cap` | `projected > cap`, strict |
| `confidence` | low <4, medium 4–11.99, high ≥12, unknown otherwise |
| `basis` | names the elapsed and day hours verbatim |

Rendered line:

```
Budget forecast for lane spark: 80 spent of 100 cap, projected 240 by end of day, based on 8 hours of ledger in a 24-hour day (medium confidence) - breach expected before end of day.
```

Projected spend is truncated to a whole number (`as i64`, `lib.rs:497`).

## 5. Preempt journal record — `preempt_record` (`lib.rs:536-546`)

```json
{"job": "job-low", "lane": "spark", "action": "paused", "reason": "lane at warning, low priority"}
```

| Field | Rule |
|---|---|
| `job` | job id the decision applied to |
| `lane` | the lane whose state drove it |
| `action` | caller writes `paused` or `resumed`; the helper only records |
| `reason` | plain words for the next brief |

The helper performs no pause. The decision itself is
`preempt_decision` (`lib.rs:513-534`), which returns only
`pause`/`resume`/None.

## 6. Template brief record — `template_brief_record` (`lib.rs:1790-1808`)

```json
{
  "text": "TEMPLATE\nWindow: not stated in this snapshot\n\nDecisions\n...",
  "model": "template",
  "spend_id": null,
  "kind": "morning"
}
```

| Field | Meaning |
|---|---|
| `text` | the composed brief; first line is always `TEMPLATE` |
| `model` | literal `template`; no Spark call was made |
| `spend_id` | `null`; there is no spend to point at (FND-032) |
| `kind` | passed through from the caller |

Body sections for `demo_snapshot` (`lib.rs:1178-1218`):

- Decisions: `decision: status page goes in intel/status.py`,
  `done: stall drill seeded`,
  `blocked: viewer panel stub waits on intel/status.py`.
- In flight: jobs 1, 2 (claimed), 4, 5 (open).
- Owners: `milo: intel status module`, `mute: status module tests`.
- Blocked and why: job 3, reason `waits on intel/status.py from job 1`.
- Watch items: `presence-stall:milo:1`, `capability-refusal:worker:1`,
  each summary the first line of the explanation.

## 7. Cost row and summary — `build_rows` / `cost_totals` (`lib.rs:1329-1466`)

A `CostRow` carries: `call` (the shot/class name), `count_base` and
`count_worst` (calls in the expected and worst day), `tokens_in`,
`tokens_out_expected`, `tokens_out_worst`, and the two computed dollar
figures. The token figures are measured at run time from
`dispatch.md` and the demo snapshot; they are not constants, so this
record shows the field contract and the pinned summary below rather
than inventing a row's token counts.

Summary at default rates, pinned at `lib.rs:3003-3026`:

```json
{
  "expected_usd": 0.021258,
  "worst_usd": 0.12789,
  "worst_with_boot_usd": 0.143982,
  "reserved_half_usd": 75.0,
  "credit_usd": 150.0,
  "headroom_vs_reserved_usd": 74.856018,
  "breakeven_multiplier_vs_reserved": 520,
  "passed": true
}
```

| Field | Rule |
|---|---|
| `expected_usd` / `worst_usd` | sum over rows with `count_base > 0` |
| `worst_with_boot_usd` | worst + the `count_base == 0` boot row |
| `headroom_vs_reserved_usd` | `75 - worst_with_boot`, rounded 6 |
| `breakeven...` | `floor(75 / worst_with_boot)` |
| `passed` | strictly under both 75 and 150 |

## 8. Busy-brief row — `measure_brief_cost` (`lib.rs:1671-1702`)

```json
{
  "variant": "scored 2-word titles",
  "jobs": 22,
  "template_words": 202,
  "template_actual_usd": 0.0,
  "tokens_in": 416,
  "tokens_out_expected": 266,
  "tokens_out_worst": 1024,
  "cost_expected": 0.005238,
  "cost_worst": 0.016608,
  "rate_sources": {"in": "default", "out": "default"}
}
```

| Field | Rule |
|---|---|
| `variant` | `scored 2-word titles` or `long-title stress` |
| `jobs` | 22 in both variants |
| `template_words` | the trimmed template's word count (≤ 220) |
| `template_actual_usd` | always 0.0: no Spark call |
| `tokens_*` | measured from the real prompt/template |
| `rate_sources` | `default` or `env:<NAME>` per rate |

## 9. Fake-queue job — `FakeQueue::post` (`lib.rs:1820-1830`)

```json
{"id": "1", "lane": "spark", "status": "open"}
```

`claim` changes `status` to `claimed` only when the gate allows it
(`lib.rs:1832-1852`). A refused claim leaves `status` at `open` and
appends the id to `holds`.

## 10. Reconstructed audit job — `audit_job_out` (`lib.rs:2125-2168`)

```json
{
  "id": "job-1",
  "status": "open",
  "title": "Do a thing",
  "spec": "Goal: ship it\nbody",
  "goal": "ship it",
  "progress_notes": ["step 1 done"],
  "remaining_files": ["b.py"],
  "accept": "tests-pass: tests.test_x",
  "artifacts": [],
  "decisions": ["decide-1"]
}
```

| Field | Reconstruction rule |
|---|---|
| `goal` | `goal` key, else the first `Goal:` line of `spec` |
| `progress_notes` | `progress_notes`, else `[note]` |
| `remaining_files` | `files` minus `completed_files`, order kept |
| `artifacts` | only references verified against manifest + bytes |
| `decisions` | only keys found in the shared or agent journal |

## 11. Audit leak and result — `audit` (`lib.rs:2190-2377`)

Leak:

```json
{"job": "job-1", "layer": "artifacts", "detail": "manifest holds v2, record references artifact:job-1/out@v3"}
```

| Layer | Fires when |
|---|---|
| `record` | non-dict, or no id |
| `spec` | missing title or spec |
| `baton` | claimed job with no goal |
| `claim` | claimed job with no claimer |
| `artifacts` | unparseable, missing, wrong version, unreadable bytes, unreadable store |
| `memory` | decision key in no visible journal |
| `memory-journal` | shared or per-agent journal unreadable (once per agent) |

Result:

```json
{"jobs": [...], "decisions": ["decide-1"], "leaks": [], "passed": true}
```

`passed` is exactly `leaks.is_empty()`.

## 12. Capped window record — `cap_snapshot_window` (`lib.rs:830-889`)

```json
{
  "max_messages": 500,
  "max_hours": 24,
  "messages_kept": 3,
  "messages_dropped": 0
}
```

| Field | Rule |
|---|---|
| `max_messages` / `max_hours` | the caps applied |
| `messages_kept` | messages left after time and count caps |
| `messages_dropped` | dropped by time + count + any prior `messages_dropped` |

Messages with no numeric `ts` are kept (they cannot be aged out).
