"""judge.py — the Imperium judge: the second agent that decides.

Boss directive (2026-11-02): no human sits in the Imperium loop.
The patrol agent watches and flags; a SECOND agent — the judge —
weighs the flag and rules on it; a confirmed ruling sends the
package to the service that owns the scene (police for Vigiles,
fire for Ignis, hospital/EMS for Medicus). Every destination is
the local SIMULATED endpoint for that service — the loopback
guard in crew.py still refuses every non-loopback target, and no
configuration anywhere in this stack names a real emergency
service.

The judge's verdicts:

  confirmed     the flag stands; the incident proceeds to the
                response step and the package is dispatched.
  cleared       the flag was a look-alike; the incident closes
                as a false positive and its person evidence is
                purged (the caller's existing path).
  inconclusive  the judge cannot rule on what it has; the flag
                stays in monitoring and NO dispatch is spent.
                An unreadable or failed judgement lands here —
                the judge never confirms on a guess.

v1 (this module): the judge weighs the patrol reading and the
independent review reading — two agents' readings, one ruling,
with the reasons recorded on the incident timeline. The ruling
function is deterministic so it is testable end to end; the
adjudication prompt below is the judge's own voice for the
judge job kind (see os-build/IMPERIUM_JUDGE.md for the wiring
step that gives the judge its own prompted call).

v2 (wired 2026-11-02): rule_with_model() below gives the judge
its own prompted call. crew.py uses it only when TRIO_JUDGE_MODEL=1
is set in the environment; the deterministic combine() remains
the default ruling and the fallback when the model call fails,
and the timeline step records which mode ruled (judge_mode).
"""

import json

# Division -> the service that owns its scenes, and the path
# suffix its packages route to on the crew's SIMULATED dispatch
# endpoint (the receiver records the suffix as the service
# route). The guard checks the full URL before any send.
SERVICES = {
    "vigiles": {"service": "police",
                "path": "/police"},
    "ignis": {"service": "fire department",
              "path": "/fire"},
    "medicus": {"service": "hospital (EMS receiving)",
                "path": "/hospital"},
}


def service_route(division):
    """The service a division's confirmed packages route to.
    Unknown division: no route (None) — never guess a service."""
    return SERVICES.get(division)


def combine(division, first_category, review_category, review_ok,
            is_flagged):
    """The judge's ruling on two readings. is_flagged(division,
    category) is the caller's flagged-category check (crew_common).
    Returns (verdict, reasons) — reasons are plain strings the
    caller records on the incident timeline."""
    if not review_ok or review_category is None:
        return "inconclusive", [
            "the review reading failed or carried no category; "
            "the judge does not confirm on a missing reading"]
    if not is_flagged(division, review_category):
        return "cleared", [
            f"the review reading landed on the baseline category "
            f"{review_category!r}; the flag reads as a look-alike"]
    if review_category == first_category:
        return "confirmed", [
            f"two independent readings agree on {review_category!r}"]
    return "confirmed", [
        f"the patrol reading was {first_category!r} and the review "
        f"reading independently flagged {review_category!r}; two "
        f"flagged readings stand over one"]


def build_judge_prompt(division, first_result, review_result):
    """The adjudication prompt for the judge job kind: the judge
    reads BOTH agents' assessments of the same frame and rules.
    JSON only, the verdict shape parse_verdict accepts."""
    route = service_route(division) or {"service": "unknown"}
    return "\n".join([
        f"You are the Imperium judge for {division}. Two agents "
        "have independently assessed the same camera frame. Your "
        "job is to rule on the flag — you are the second agent, "
        "and no human sits between your ruling and the response.",
        "Return JSON ONLY, no prose, no markdown fences:",
        '{',
        '  "verdict": "<confirm|reject|investigate>",',
        '  "category": "<the category you rule the scene to be>",',
        '  "reasons": ["<what in the two readings decides it>"],',
        '  "confidence": null',
        '}',
        f"First reading: {json.dumps(first_result)[:1200]}",
        f"Second reading: {json.dumps(review_result)[:1200]}",
        "confirm = the flag stands and the package goes to the "
        f"{route['service']}; reject = the flag is a look-alike "
        "and the incident closes; investigate = the readings "
        "conflict in a way more looking could settle. When the "
        "evidence does not decide it, rule investigate — never "
        "confirm on a guess. Set confidence to null.",
    ])


_VERDICTS = {"confirm": "confirmed", "reject": "cleared",
             "investigate": "inconclusive"}


def _extract_json_object(text):
    """The documented prose tolerance: a judge reply may wrap its
    JSON object in prose or a markdown fence. Parse the first `{`
    through the last `}`; anything else returns None. This never
    guesses a verdict — it only unwraps one object."""
    if not isinstance(text, str):
        return None
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def parse_verdict(text):
    """Parse a judge reply into (verdict, category, reasons).
    A JSON object wrapped in prose or a markdown fence is accepted
    (the documented tolerance). Anything unparseable, a non-object,
    or a verdict word outside the three raises ValueError: a garbled
    judgement is refused at the parser, never silently turned into a
    ruling."""
    try:
        data = json.loads(text)
    except Exception:
        data = _extract_json_object(text)
        if data is None:
            raise ValueError("the judge's reply was not JSON") from None
    if not isinstance(data, dict):
        raise ValueError("the judge's reply was not an object")
    verdict = _VERDICTS.get(str(data.get("verdict") or "").strip().lower())
    if verdict is None:
        raise ValueError(
            f"the judge returned an unknown verdict {data.get('verdict')!r}")
    reasons = data.get("reasons")
    if not isinstance(reasons, list):
        reasons = []
    return verdict, data.get("category"), [str(r) for r in reasons]


def rule_with_model(division, first_result, review_result, chat_fn):
    """The judge's own prompted ruling (v2). chat_fn(prompt) must
    return the model's reply text (models.chat_text does, over
    Muse Spark). Returns (verdict, category, reasons) from
    parse_verdict — a garbled reply rules inconclusive, never a
    guess. A transport failure raises to the caller, whose job it
    is to fall back to combine() and say so on the timeline."""
    prompt = build_judge_prompt(division, first_result, review_result)
    text = chat_fn(prompt)
    try:
        verdict, category, reasons = parse_verdict(text)
    except ValueError as err:
        return "inconclusive", None, [
            f"model judge ruling unusable: {err}"]
    return verdict, category, [
        f"model judge ruling: {r}" for r in reasons] or [
        "model judge ruling carried no reasons"]
