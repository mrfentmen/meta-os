# Python crew seam — behaviour record (B229)

Source: `server/queue/crew.py` (read at 835 lines). The crew is the
patrol-to-response pipeline; every external effect is an injected seam
(`crew.py:46-60` module docstring, `332-366` constructor).

## Inputs

- `check_camera(camera, division, at=None)` (`crew.py:368-412`): a
  camera dict with `id`, `name`, optional `area`/lat/lon; a division
  string; optional ISO timestamp.
- `Crew(records, assess, fetch_snapshot, dispatch, cameras=(), ...)`
  (`crew.py:332-366`): four injected callables plus camera metadata.
- `QueueAssessor(jobs, poll_attempts=90, poll_interval=1.0, sleep=...)`
  (`crew.py:173-203`): a `JobStore`-shaped object.
- `build_brief(record, results)` (`crew.py:279-330`): one incident
  record and the assessment result envelopes.
- `check_dispatch_url(url)` (`crew.py:114-126`) and `dispatch_url()`
  (`crew.py:128-130`): a dispatch target.

## Outputs

`check_camera` returns one outcome dict with `outcome` in
`baseline`, `feed-error`, `job-error`, `assessment-failed`,
`flagged-unconfirmed`, `cleared-by-review`, `stopped`,
`flagged-yellow-review`, `dispatched-simulated`, `reported`
(`crew.py:368-412`, `461-678`). Every step is also appended to the
incident timeline and the events feed.

- `baseline` — the reading is inside the division's baseline set; no
  incident is created (`crew.py:404-412`).
- `feed-error` / `job-error` / `assessment-failed` — the failure is
  recorded with the error truncated to 200 chars; no incident is
  created (`crew.py:368-402`).
- `cleared-by-review` — the orchestrator ordered `close_candidate`;
  evidence files are purged with a receipt (`crew.py:510-522`).
- `flagged-unconfirmed` — the review was inconclusive; the incident
  stays open in monitoring and no further model call is spent
  (`crew.py:523-531`).
- `dispatched-simulated` — the judge-confirmed package was accepted
  by the loopback dispatch seam; otherwise `reported` carries the
  dispatch error (`crew.py:626-662`).

`build_brief` returns the v2 contract shape: origin division's
observations only, union of uncertainties, the last non-empty
summary, summed measured latencies, last model name, and
`requires_human_review: True` (`crew.py:279-330`).

## Refusals

| Situation | Behaviour | Source |
|---|---|---|
| Dispatch host is not loopback | `DispatchBoundaryError`; no configuration can point at a real emergency service | `crew.py:110-126` |
| `TRIO_CREW_DISPATCH_URL` points off-loopback | refused when `dispatch_url()` reads it | `crew.py:128-138` |
| Routed dispatch path leaves loopback | refused per route | `crew.py:156-171` |
| Queue result never arrives | `TimeoutError` after `poll_attempts`; never a fabricated assessment | `crew.py:173-203` |
| Envelope built for a queue call is invalid | `ValueError("crew-built envelope refused: ...")` before submit | `crew.py:173-203` |
| Evidence cap reached | `([], None, "evidence file cap reached")`, recorded as `evidence-error`; the flag pipeline continues | `crew.py:414-459`, `493-501` |
| Frame save fails | no entries, error recorded; detection is skipped | `crew.py:414-459` |
| Face detection/crop fails | the frame entry stays; the error is returned and recorded | `crew.py:414-459` |
| Review assessment raises | a failed review envelope (`status: failed`) is recorded; the verdict is then `inconclusive` | `crew.py:680-724` |
| Dispatch raises | the timeline step carries the error, outcome is `reported`, never a fake receipt | `crew.py:626-662` |

## The decision loop

After a flag the sequence is not hardcoded: the crew asks the
orchestrator after every result (`crew.py:502-620`). It executes
`review`, `investigation` (including a reconcile's named missing
lens) and stops on `close_candidate`, `continue_monitoring`, `stop`,
`record_for_review` or `prepare_response`. Investigation is bounded by
`MAX_INVESTIGATION_CALLS = 6` (`crew.py:98-99`, `741-835`);
cross-division lenses run first, then up to three nearest neighbours,
and every attempt is recorded even when the feed or job fails.

## What it writes

Incident records and timeline steps through the injected
`CrewRecords` store; evidence files under the incident's evidence
directory; events (`patrol-check`, `flag`, `review`, `incident`,
`investigation`, `dispatch`) to the events feed
(`crew.py:368-412`, `461-678`, `680-739`). The BOLO is filed on the
timeline and carried in the dispatch package (`crew.py:600-625`).

## Findings (reported, not fixed)

1. **`build_brief` drops cross-division observations by design.** The
   brief is a single-product v2 document; other lenses live on the
   timeline and in recommended actions (`crew.py:279-330`).
2. **`_distinct_timestamp` assumes the ISO shape.** A timestamp that
   does not match `%Y-%m-%dT%H:%M:%S.%fZ` raises instead of falling
   back (`crew.py:232-245`). Production callers always pass the
   `crew_common.now_iso()` shape.
3. **The evidence cap counts entries, not bytes.** Twelve small
   crops and twelve large frames cost the same budget
   (`crew.py:103`, `414-459`).
4. **`QueueAssessor` polls synchronously.** A slow agent holds the
   calling thread for up to `poll_attempts * poll_interval` seconds
   (`crew.py:173-203`).
5. **Dispatch defaults to the local simulated endpoint.** There is no
   "real" branch to enable (`crew.py:105-107`, `114-126`).

## Tests

Missing cases are in `tests/queue-python/test_crew_seam_missing.py`
(dispatch boundary, timestamp bump, poll timeout, brief filtering,
evidence cap).
