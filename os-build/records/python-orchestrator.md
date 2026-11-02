# Python orchestrator — behaviour record (B231)

Source: `server/queue/orchestrator.py` (read at 544 lines). A
deterministic decision engine: no model calls, no spend. Given an
incident record it emits one decision contract
(`orchestrator.py:312-491`).

## Inputs

- `decide(record, guardrail_status=None, evidence_hash=None,
  stop_conditions=None)` (`orchestrator.py:312-491`): an incident
  record with `status`, `division`, `category`, `timeline`; optional
  guardrail status dict and evidence hash.
- `Orchestrator(records=None, guardrail_status=None)`
  (`orchestrator.py:493-544`): optional records store and either a
  status dict, a callable returning one, or `None`.
- `counts(record, guardrail_status=None)` (`orchestrator.py:187-226`).
- `tier_for(division, category)` (`orchestrator.py:153-180`).

## Outputs

The contract (`orchestrator.py:253-257`):

```
{"incident_id", "decision", "reason",
 "actions": [{"agent", "task"}],
 "stop_conditions": {"max_actions": 8, "max_model_calls": 12,
                     "max_cost_usd": 0.50}}
```

Decisions: `investigate`, `reconcile`, `close_candidate`,
`prepare_response`, `continue_monitoring`, `record_for_review`,
`stop` (`orchestrator.py:1-90`, `312-491`).

`counts` returns `model_calls`, `actions`, `est_cost_usd`,
`per_call_usd` (`orchestrator.py:187-226`):

- `model_calls` counts `flag`, `review` and `investigation` timeline
  steps.
- `actions` is the larger of (a) actions emitted on prior `decision`
  steps and (b) executed `review`/`investigation`/`brief`/`dispatch`
  steps, so neither representation can hide spend.
- `est_cost_usd` prefers the sum of `est_cost_usd` fields on the
  timeline; otherwise it is `model_calls * per_call_usd`.
- `per_call_usd` is the guardrail ledger's `est_cost_usd / calls`
  when `calls` is positive, else `EST_COST_PER_CALL_USD` (0.01).

`lifecycle_status(decision)` maps a decision to the status it moves
the record to, or `None` (`orchestrator.py:227-251`):
`close_candidate -> closed-false-positive`,
`prepare_response -> response_prepared`,
`continue_monitoring -> monitoring`,
`record_for_review -> yellow-review`, `stop -> stopped`,
`reconcile -> investigating`,
`investigate + review agent -> under_review`,
`investigate + other agent -> investigating`.

## Limits (enforced here, before any spend)

`STOP_CONDITIONS` (`orchestrator.py:88-89`). `_limit_breach`
(`orchestrator.py:259-289`) refuses with a named reason when:

- actions >= `max_actions`;
- model calls + planned calls > `max_model_calls`;
- projected cost > `max_cost_usd`;
- the guardrail reports `remaining_usd <= 0` and the step would spend.

The loop guard refuses a third investigation of the same evidence
hash (`orchestrator.py:435-449`). The tier gate runs before any review
or investigation: a yellow flag returns `record_for_review` with no
actions (`orchestrator.py:355-365`). The display tier table wins over
the priority mapping; a category in neither table is not gated
(`orchestrator.py:153-180`).

## Refusals

| Situation | Behaviour | Source |
|---|---|---|
| Status is terminal (`dispatched-simulated`, `closed-false-positive`, `cleared-by-review`, `stopped`, `yellow-review`) | `stop`, no actions | `orchestrator.py:120-123`, `324-331` |
| A dispatch receipt already exists | `stop`, no actions | `orchestrator.py:332-338` |
| Yellow tier | `record_for_review`, no actions | `orchestrator.py:355-365` |
| Review cleared the flag | `close_candidate`, records action only | `orchestrator.py:377-387` |
| Review inconclusive / failed | `continue_monitoring`, no actions | `orchestrator.py:388-397` |
| Conflicting patrol/review categories, not yet reconciled | `reconcile`, one re-review | `orchestrator.py:399-417` |
| Same evidence investigated twice | `continue_monitoring`, no actions | `orchestrator.py:435-449` |
| Any limit breached | `stop` with the limit named in `reason` | `orchestrator.py:259-289` |

## What it writes

`Orchestrator.step` appends a `decision` timeline step carrying the
decision, reason, actions, action count and the lifecycle status, and
an `orchestrator` event to the feed (`orchestrator.py:509-544`).
Without a records store the decision is returned unrecorded
(`orchestrator.py:509-513`).

## Findings (reported, not fixed)

1. **A reconcile can be ordered repeatedly.** `reconciled` is true
   once any `decision == "reconcile"` step exists, so a second
   conflict is not re-ordered; the category conflict then falls
   through to the investigation path (`orchestrator.py:399-417`).
2. **`counts` trusts `est_cost_usd` fields.** A timeline step with a
   negative or zero cost is treated as recorded spend; there is no
   validation (`orchestrator.py:187-226`).
3. **The tier gate fails open for unknown categories.** Not gated is
   deliberate, but it means a new taxonomy string runs the red chain
   until both tables are updated (`orchestrator.py:153-180`).
4. **`Orchestrator._status` swallows every exception** and returns
   `None`, so a broken guardrail ledger silently disables the
   remaining-budget check (`orchestrator.py:493-508`).
5. **`decide` does not validate the record.** A missing `timeline`
   is treated as empty; a missing division/category is not refused
   (`orchestrator.py:312-324`).

## Tests

Missing cases are in
`tests/queue-python/test_orchestrator_missing.py` (counting rules,
lifecycle mapping, tier normalisation, limit overrides, unrecorded
step, missing lenses, loop-guard count).
