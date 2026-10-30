# The Meta Imperium agent crew

How the autonomous crew works: patrol → review → investigation →
records → response, on the existing OS queue, visible live in the
Command view's LOOP FEED panel. Every claim below names the file
that backs it. Where a mechanism is bounded or simulated, this
document says so in plain terms.

## The loop

1. **PATROL** — `server/queue/patrol.py`. Cycles the public NYCTMC
   camera list (live API when reachable; otherwise the verbatim
   offline subset from `js/camera-fallback.js`, and the status
   names which source is in use). One snapshot per visit, filed as
   a `trio-assessment` v1 job on the existing queue
   (`server/queue/crew.py` `QueueAssessor` — the same deterministic
   envelope `server/queue.mjs` builds), answered by the resident
   agent (`trio_agent.py`) with a real Muse Spark assessment
   through the existing $75 guardrail. The lens rotates per visit
   (Vigiles → Ignis → Medicus → …) so every camera is checked under
   every division over time.
   **Adaptive priority:** cameras at or near an open incident
   (within 1500 m) and cameras flagged in the last hour are visited
   first; the rest follow round-robin (`patrol_order`,
   `compute_priority_ids` in `patrol.py` — pure, unit-tested).
   **Budget governor:** before every visit, patrol reads the
   existing guardrail state (`spark_guardrail.status()`); at or
   below a $5 reserve (env `TRIO_CREW_BUDGET_RESERVE_USD`) — or if
   the guardrail itself refuses — patrol pauses, writes
   `paused-budget` to its heartbeat and the event feed, and files
   nothing until the state changes.

2. **REVIEW** — `crew.py` `_handle_flag`. A category outside the
   division's baseline set (the flag rule lives in
   `js/command-flag.js`; the crew loads those tables from that
   file, never a copy) earns an adversarial second look: an
   **independent second assessment of the same frame** — a fresh
   job with a distinct timestamp, so a distinct job id, answered
   independently. The flag survives only if the second reading
   *also* lands outside baseline. A baseline second reading clears
   the flag as a look-alike (the steam-or-fog problem). A failed
   second reading leaves the flag **unconfirmed**: recorded, held
   for human review, and no investigation or dispatch spend follows
   it. Honest limit: the second reading uses the standard
   assessment prompt — the adversarial part is its independence and
   the survival rule, not a special prompt.

3. **RECORDS** — `server/queue/crew_records.py`. A surviving flag
   becomes an incident record *before* anything else happens:
   durable JSON under the crew data directory (`TRIO_CREW_DATA_DIR`,
   default `server/queue/crew-data/`). The record's timeline is
   **append-only** — every step (flag, review verdict,
   investigation entries, brief, dispatch) is appended with its
   timestamp, camera, division, categories, model, and latency; no
   step is ever edited or removed. The same directory holds the
   append-only event feed (`events.jsonl`) the loop feed renders,
   the simulated dispatch log (`dispatches.jsonl`), and the patrol
   heartbeat (`crew-status.json`).

4. **INVESTIGATION** — `crew.py` `_investigate`. For a reported
   incident: the other two divisions' lenses on a fresh snapshot of
   the incident camera, then up to 3 nearest neighbour cameras
   (haversine over the loaded list) under the origin division.
   **Bound: `MAX_INVESTIGATION_CALLS = 6` extra assessments per
   incident, hard-capped in code**, all through the same guardrail.
   Findings append to the incident record; they never spawn further
   incidents — recursion stops at one level.

5. **RESPONSE** — `crew.py` (brief + package) and the simulated
   endpoint in `queue_service.py`. The crew builds an incident
   brief in the v2 contract shape (observations only,
   `requires_human_review: true` — always) plus per-division
   **recommended actions**: recommendations for a human
   decision-maker, in observation language. Nothing states that an
   incident or offense occurred; nothing directs a dispatch.

## The dispatch boundary — read this before demoing

The response step "dispatches" the package **only** to the stack's
own SIMULATED endpoint: `POST /dispatch-simulated` on the local
queue service, which logs the package to `dispatches.jsonl` and
returns a receipt (`sim-…`). It contacts nothing outside this
stack.

This is a hard boundary, enforced in code, not a setting:

- `crew.check_dispatch_url` refuses any dispatch URL whose host is
  not loopback (`127.0.0.1` / `localhost` / `::1`) — there is **no
  configuration that points dispatch at a real endpoint**.
- There is no phone, 911, or external-notification integration
  anywhere in the crew, and none may be added as an "option".
- The endpoint accepts only packages labelled `"simulated": true`,
  and the label travels with the package, the log line, the
  receipt, and the loop-feed copy ("Dispatch (SIMULATED) … no real
  service contacted").

What the crew replaces is the *watching* — the human who falls
asleep, turns away, misses the frame. The judgement calls stay
where the v2 contract has always put them: the system flags,
records, investigates, and prepares; `requires_human_review` is
true on every brief.

## Surfacing

- **Loop feed** (Command view, left rail): polls
  `GET /api/crew/status` (`server/server.mjs` +
  `server/crew-status.mjs` — a read-only projection of the crew
  records) every 5 s and renders patrol checks, review verdicts,
  incident reports, investigation runs, and dispatch receipts,
  formatted by the pure module `js/command-loop.js`. If the
  endpoint does not answer, the panel says UNAVAILABLE and keeps
  polling; it never invents activity.
- **Patrol heartbeat**: `crew-status.json` — state
  (running / paused-budget / idle), camera-list source, counts
  (checks, baseline, flagged, reported, feed errors, job errors),
  and the guardrail numbers behind any pause.

## Running it

```sh
# alongside the existing stack (queue service + resident agent up):
cd server/queue
python3 patrol.py --interval 20        # or --once for a single visit
```

Patrol and the resident agent must both run for checks to be
answered; if no agent answers, a check ends as a recorded
`job-error` (bounded poll timeout), never a fabricated result.

Environment: `TRIO_CREW_DATA_DIR` (records location),
`TRIO_CREW_DISPATCH_URL` (default `http://127.0.0.1:8935/dispatch-simulated`;
loopback-checked), `TRIO_CREW_BUDGET_RESERVE_USD` (default 5),
plus the queue's own variables (`TRIO_JOB_NS`, `TRIO_STORE`,
`TRIO_LOCAL_DB`, and the generation transport's).

## Tests

- Python: `tests/queue-python/test_crew.py` — offline, stubbed
  assess/fetch/dispatch seams: envelope identity with the real
  `buildQueueJob`, flag tables loaded from the real
  `js/command-flag.js`, baseline/flight paths, review
  cleared/confirmed/inconclusive, the investigation bound, the
  brief passing the real `validateAssessment`, append-only records,
  patrol ordering/priority, the budget pause, the loopback dispatch
  guard, and the HTTP simulated-dispatch route end to end.
- Web: `tests/command-loop.test.mjs` (feed formatting, incl. the
  SIMULATED label and loud-degradation states) and
  `tests/server-crew-status.test.mjs` (the read-only endpoint over
  real record files, plus the empty-state answer).

## Status (honest labels, 2026-10-30)

- **Pipeline logic — UNIT-VERIFIED** offline against stubbed seams
  and the real contract validator, flag tables, and envelope
  builder (test counts in the delivery report).
- **Live end-to-end — NOT run in the sandbox.** NYCTMC image
  fetches are refused by the sandbox egress (the same block the
  Command view hit), so a patrol visit here ends as a recorded
  feed error — the degradation path, exercised for real. The full
  live loop (real snapshots → guarded Spark answers → reported
  incident → simulated dispatch receipt) first runs where the
  feeds are reachable: Del's Mac, with the stack up.
