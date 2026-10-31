"""orchestrator.py — the Meta Imperium autonomous orchestrator.

LANE B (2026-10-30): the crew stops being a fixed pipeline. This
module is a DETERMINISTIC decision engine — it makes no model
calls and spends nothing. Given an incident record (crew_records.py)
it emits ONE decision contract, and it is consulted again after
every crew result lands, so the sequence of work on an incident is
chosen from the incident's current state, never pre-scripted:

    {"incident_id": ..., "decision": ..., "reason": ...,
     "actions": [{"agent": ..., "task": ...}, ...],
     "stop_conditions": {"max_actions": 8, "max_model_calls": 12,
                         "max_cost_usd": 0.50}}

Decisions:
  investigate        order the next evidence step: the independent
                     Review of a fresh flag, or the bounded
                     Investigation of a review-confirmed flag.
  reconcile          assessments conflict (the review's flagged
                     category differs from Patrol's), or an
                     investigation ran without covering a division
                     lens — order a re-review or the missing lens.
  close_candidate    Review returned a baseline (look-alike)
                     category: close the incident as a false
                     positive. The record is closed, never erased —
                     the full timeline stays on file.
  prepare_response   flag + review survived + investigation done:
                     build the brief and submit it to the SIMULATED
                     dispatch endpoint (crew.py's existing path —
                     loopback-only, labelled simulated).
  continue_monitoring
                     evidence is insufficient (review could not
                     confirm or clear, or the loop guard tripped):
                     the incident stays open, nothing is spent.
  stop               a stop condition hit, or the lifecycle is
                     already complete. The reason names the limit.

Limits are enforced HERE, in code, before any spending decision is
emitted — never in a prompt:
  * prior actions / model calls are counted from the incident's own
    timeline (see counts());
  * the guardrail status (spark_guardrail.status) is read: a
    decision that would spend is refused when the $75 test budget
    is exhausted;
  * loop guard: an evidence frame hash that has already been
    investigated twice is never investigated again.

Every decision an Orchestrator bound to a CrewRecords store emits
is appended to the incident's append-only timeline (step
"decision") and to events.jsonl (type "orchestrator",
agent "orchestrator") — the Command LOOP FEED renders them.

Lifecycle statuses (carried on decision timeline steps, so the
status history IS the timeline): candidate, under_review,
investigating, response_prepared, dispatched-simulated,
closed-false-positive, monitoring, stopped. (The dispatch step in
crew.py still sets dispatched-simulated itself; the legacy
"flagged" / "reported" / "cleared-by-review" values from the
fixed-pipeline era remain readable everywhere they were readable.)
"""
import crew_common
import spark_guardrail

STOP_CONDITIONS = {"max_actions": 8, "max_model_calls": 12,
                   "max_cost_usd": 0.50}

# Planned model calls for one investigation batch, matching the
# crew's planned use (crew.py: 2 cross-division lenses + up to 3
# neighbour cameras = 5, under its MAX_INVESTIGATION_CALLS cap of
# 6). Used only to project spend BEFORE a batch is ordered.
PLANNED_INVESTIGATION_CALLS = 5

# Planning estimate for one assessment call when neither the
# record nor the guardrail history carries a measured cost. Cost
# accounting prefers, in order: est_cost_usd sums on the record's
# own timeline steps; the guardrail ledger's measured average
# (est_cost_usd / calls); this constant. It is an estimate used for
# limit projection, never a claim about actual spend.
EST_COST_PER_CALL_USD = 0.01

DIVISIONS = ("vigiles", "ignis", "medicus")
TERMINAL_STATUSES = ("dispatched-simulated", "closed-false-positive",
                     "cleared-by-review", "stopped")
ACTION_STEPS = ("review", "investigation", "brief", "dispatch")
CALL_STEPS = ("flag", "review", "investigation")


# -- counting (the code the limits are enforced from) -------------------

def _steps(record, name):
    return [s for s in record.get("timeline") or []
            if isinstance(s, dict) and s.get("step") == name]


def counts(record, guardrail_status=None):
    """Prior spend on this incident, counted from its timeline.

    model_calls: every assessment job filed for the incident —
    the flag (Patrol), each review, each investigation step.
    actions: crew work already done, counted two ways and taken
    as the larger, so neither representation can hide spend —
    (a) the actions the orchestrator has emitted on prior decision
    steps, (b) the executed action steps (review / investigation /
    brief / dispatch) on the timeline.
    est_cost_usd: est_cost_usd sums recorded on timeline steps when
    present; otherwise model_calls x the per-call estimate (the
    guardrail ledger's measured average when a status is supplied,
    else EST_COST_PER_CALL_USD).
    """
    timeline = record.get("timeline") or []
    model_calls = sum(1 for s in timeline
                      if isinstance(s, dict)
                      and s.get("step") in CALL_STEPS)
    emitted = sum(len(s.get("actions") or [])
                  for s in _steps(record, "decision"))
    executed = sum(1 for s in timeline
                   if isinstance(s, dict)
                   and s.get("step") in ACTION_STEPS)
    recorded_cost = sum(s["est_cost_usd"] for s in timeline
                        if isinstance(s, dict)
                        and isinstance(s.get("est_cost_usd"),
                                       (int, float)))
    if guardrail_status and guardrail_status.get("calls"):
        per_call = guardrail_status["est_cost_usd"] / \
            guardrail_status["calls"]
    else:
        per_call = EST_COST_PER_CALL_USD
    return {"model_calls": model_calls,
            "actions": max(emitted, executed),
            "est_cost_usd": recorded_cost if recorded_cost else
            round(model_calls * per_call, 6),
            "per_call_usd": per_call}


def lifecycle_status(decision):
    """The incident status a decision moves the record to, or None
    when the decision itself does not move it."""
    name = decision.get("decision")
    agents = [a.get("agent") for a in decision.get("actions") or []]
    if name == "close_candidate":
        return "closed-false-positive"
    if name == "prepare_response":
        return "response_prepared"
    if name == "continue_monitoring":
        return "monitoring"
    if name == "stop":
        return "stopped"
    if name == "reconcile":
        return "investigating"
    if name == "investigate":
        if "review" in agents:
            return "under_review"
        return "investigating"
    return None


# -- the engine -----------------------------------------------------------

def _contract(record, decision, reason, actions, stop_conditions):
    return {"incident_id": record.get("id"), "decision": decision,
            "reason": reason, "actions": actions,
            "stop_conditions": dict(stop_conditions)}


def _limit_breach(record, planned_calls, cnt, guardrail_status,
                  stop_conditions):
    """A stop reason naming the limit a spending decision would
    breach, or None when the spend is within every limit."""
    if cnt["actions"] >= stop_conditions["max_actions"]:
        return (f"stop condition reached: max_actions "
                f"({stop_conditions['max_actions']}) — the incident "
                f"already has {cnt['actions']} actions on its "
                f"timeline; no further action is ordered")
    if cnt["model_calls"] + planned_calls > \
            stop_conditions["max_model_calls"]:
        return (f"stop condition reached: max_model_calls "
                f"({stop_conditions['max_model_calls']}) — the "
                f"incident already has {cnt['model_calls']} model "
                f"calls and the next step would add {planned_calls}")
    projected = cnt["est_cost_usd"] + planned_calls * cnt["per_call_usd"]
    if projected > stop_conditions["max_cost_usd"]:
        return (f"stop condition reached: max_cost_usd "
                f"({stop_conditions['max_cost_usd']:.2f}) — the "
                f"incident's estimated cost is "
                f"${cnt['est_cost_usd']:.4f} and the next step "
                f"would take it to about ${projected:.4f}")
    if planned_calls and guardrail_status is not None and \
            guardrail_status.get("remaining_usd", 1) <= 0:
        return (f"stop condition reached: the spark guardrail "
                f"reports no budget remaining "
                f"(${guardrail_status.get('est_cost_usd')} of "
                f"${guardrail_status.get('test_budget_usd')} test "
                f"budget spent); no further model call is ordered")
    return None


def missing_lenses(record):
    """Division lenses with no cross-lens investigation step on
    the record — the gap a reconcile decision orders filled. The
    crew uses this same function to execute a reconcile order, so
    the lens executed is the lens the decision named."""
    covered = {s.get("division")
               for s in _steps(record, "investigation")
               if s.get("kind") == "cross-lens"}
    return [d for d in DIVISIONS
            if d != record.get("division") and d not in covered]


def _investigations_of(record, evidence_hash):
    """Prior investigation steps taken on one evidence frame."""
    if not evidence_hash:
        return 0
    return sum(1 for s in _steps(record, "investigation")
               if (s.get("frame_sha256") or s.get("evidence_hash"))
               == evidence_hash)


def decide(record, guardrail_status=None, evidence_hash=None,
           stop_conditions=None):
    """The NEXT decision for an incident, from its current record
    alone — a replanning step, not a script: call it after each
    crew result lands and it returns what should happen next."""
    sc = dict(stop_conditions or STOP_CONDITIONS)
    cnt = counts(record, guardrail_status)
    status = record.get("status")
    division = record.get("division")
    category = record.get("category")

    if status in TERMINAL_STATUSES:
        return _contract(
            record, "stop",
            f"the incident lifecycle is already complete "
            f"(status: {status}); nothing further is ordered", [], sc)
    dispatches = _steps(record, "dispatch")
    if any(s.get("receipt_id") for s in dispatches):
        return _contract(
            record, "stop",
            "a simulated dispatch receipt is already on the "
            "timeline; nothing further is ordered", [], sc)

    reviews = _steps(record, "review")
    if not reviews:
        breach = _limit_breach(record, 1, cnt, guardrail_status, sc)
        if breach:
            return _contract(record, "stop", breach, [], sc)
        return _contract(
            record, "investigate",
            f"flagged category \"{category}\" is outside the "
            f"{division} baseline set and no independent review "
            f"has been recorded yet",
            [{"agent": "review",
              "task": "Independent second assessment of the "
                      "flagged frame (review survival rule: the "
                      "flag stands only if this reading also lands "
                      "outside the baseline set)"}], sc)

    review = reviews[-1]
    verdict = review.get("verdict")
    if verdict == "cleared":
        return _contract(
            record, "close_candidate",
            f"review returned the baseline category "
            f"\"{review.get('category')}\" — the flag is a "
            f"look-alike; the incident closes as a false positive "
            f"and its record is kept, not erased",
            [{"agent": "records",
              "task": "Close the incident as a false positive in "
                      "the append-only record (status "
                      "closed-false-positive); retain the full "
                      "timeline"}], sc)
    if verdict != "confirmed":
        return _contract(
            record, "continue_monitoring",
            f"review was {verdict or 'unrecorded'} — the flag is "
            f"neither confirmed nor cleared, so the evidence is "
            f"insufficient; the incident stays open for human "
            f"review and no further model call is spent on it",
            [], sc)

    # Review confirmed (survived). Conflicts reconcile before any
    # further spend: the review's flagged category differs from
    # Patrol's, and no reconcile has been ordered yet.
    flags = _steps(record, "flag")
    patrol_category = flags[-1].get("category") if flags else category
    review_category = review.get("category")
    reconciled = any(s.get("decision") == "reconcile"
                     for s in _steps(record, "decision"))
    investigations = _steps(record, "investigation")
    if review_category and patrol_category and \
            review_category != patrol_category and not reconciled:
        breach = _limit_breach(record, 1, cnt, guardrail_status, sc)
        if breach:
            return _contract(record, "stop", breach, [], sc)
        return _contract(
            record, "reconcile",
            f"conflicting assessments: Patrol flagged "
            f"\"{patrol_category}\" but the confirming review "
            f"returned \"{review_category}\"; a re-review is "
            f"ordered before any response is prepared",
            [{"agent": "review",
              "task": "Re-review the flagged frame against the "
                      "conflicting categories "
                      f"(\"{patrol_category}\" vs "
                      f"\"{review_category}\")"}], sc)

    # Loop guard, checked before ANY further investigation is
    # ordered (a first investigation, or a reconcile's missing
    # lens): an evidence frame already investigated twice is never
    # investigated again. It does not block prepare_response —
    # when the investigation record is complete, no investigation
    # is being ordered.
    missing = missing_lenses(record) if investigations else []
    if evidence_hash and \
            _investigations_of(record, evidence_hash) >= 2 and \
            (not investigations or missing):
        return _contract(
            record, "continue_monitoring",
            "loop guard: this evidence frame has already been "
            "investigated twice for this incident; it is not "
            "investigated again — the incident stays open in "
            "monitoring with the evidence on record", [], sc)

    if not investigations:
        breach = _limit_breach(record, PLANNED_INVESTIGATION_CALLS,
                               cnt, guardrail_status, sc)
        if breach:
            return _contract(record, "stop", breach, [], sc)
        return _contract(
            record, "investigate",
            "the flag survived review and no investigation has "
            "been recorded; additional evidence is gathered "
            "before any response is prepared",
            [{"agent": "investigation",
              "task": "Assess the incident camera under the other "
                      "divisions' lenses, then up to 3 nearest "
                      "cameras under the origin division (bounded "
                      "by MAX_INVESTIGATION_CALLS)"}], sc)

    # Investigation recorded. A cross-lens gap reconciles first:
    # every other division's lens should have a step on record
    # (missing computed above, before the loop guard).
    covered = {s.get("division") for s in investigations
               if s.get("kind") == "cross-lens"}
    if missing and not reconciled:
        breach = _limit_breach(record, 1, cnt, guardrail_status, sc)
        if breach:
            return _contract(record, "stop", breach, [], sc)
        return _contract(
            record, "reconcile",
            f"the investigation record covers "
            f"{sorted(c for c in covered if c)} but has no "
            f"{missing[0]} lens step; the missing lens is ordered "
            f"before any response is prepared",
            [{"agent": "investigation",
              "task": f"Assess the incident camera under the "
                      f"{missing[0]} lens (the lens missing from "
                      f"the investigation record)"}], sc)

    # Flag + review survived + investigation done: response. The
    # brief build and the simulated submission spend no model
    # calls, so only the action limit can refuse them.
    if cnt["actions"] >= sc["max_actions"]:
        return _contract(
            record, "stop",
            f"stop condition reached: max_actions "
            f"({sc['max_actions']}) — the incident already has "
            f"{cnt['actions']} actions on its timeline; the "
            f"response is not prepared", [], sc)
    return _contract(
        record, "prepare_response",
        "flagged, confirmed by independent review, and "
        "investigated; the response brief is prepared and "
        "submitted to the simulated dispatch endpoint only",
        [{"agent": "response",
          "task": "Build the incident brief from the recorded "
                  "assessments and submit it to the simulated "
                  "dispatch endpoint (loopback-only, labelled "
                  "simulated, requires_human_review stays true)"}],
        sc)


class Orchestrator:
    """The decision engine bound to the crew's records: each
    decide() call is recorded — appended to the incident's
    timeline as a "decision" step (carrying the lifecycle status
    it moves the record to) and to events.jsonl as an
    "orchestrator" event the LOOP FEED renders."""

    def __init__(self, records=None, guardrail_status=None):
        self.records = records
        # guardrail_status: a callable returning spark_guardrail
        # .status(), a status dict, or None (read the live ledger).
        self.guardrail_status = guardrail_status

    def _status(self):
        try:
            gs = self.guardrail_status
            if gs is None:
                return spark_guardrail.status()
            return gs() if callable(gs) else gs
        except Exception:
            return None

    def step(self, record, evidence_hash=None):
        """One replanning step: decide from the record's current
        state, record the decision (timeline + event feed), and
        return the contract. Recording needs the records store;
        without one the decision is returned unrecorded."""
        decision = decide(record, guardrail_status=self._status(),
                          evidence_hash=evidence_hash)
        if self.records is not None and record.get("id"):
            at = crew_common.now_iso()
            self.records.append_timeline(record["id"], {
                "at": at, "step": "decision", "agent": "orchestrator",
                "decision": decision["decision"],
                "reason": decision["reason"],
                "actions": decision["actions"],
                "actions_count": len(decision["actions"]),
                "status": lifecycle_status(decision),
            })
            camera = record.get("camera") or {}
            self.records.append_event({
                "at": at, "type": "orchestrator",
                "agent": "orchestrator",
                "incident_id": record["id"],
                "camera_id": camera.get("id"),
                "camera_name": camera.get("name"),
                "division": record.get("division"),
                "decision": decision["decision"],
                "reason": decision["reason"],
                "actions": len(decision["actions"]),
            })
        return decision
