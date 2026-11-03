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
from datetime import datetime

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


VALID_PRODUCTS = frozenset(SERVICES)


def _reading_product(reading):
    if not isinstance(reading, dict):
        return None
    product = reading.get("product")
    if product is None:
        assessment = reading.get("assessment")
        if isinstance(assessment, dict):
            product = assessment.get("product")
    return product


def validate_reading(reading):
    """Return a named error for a malformed judge reading, or None.
    Product ids are checked against the three divisions. A region,
    when present, must be an x/y/w/h box on the 0-1000 contract
    scale. Missing optional fields are allowed; invented ones are
    not part of the prompt payload."""
    if not isinstance(reading, dict):
        return "reading is not an object"
    product = _reading_product(reading)
    if product is not None and product not in VALID_PRODUCTS:
        return f"unknown product in reading: {product!r}"
    assessment = reading.get("assessment")
    observations = []
    if isinstance(assessment, dict):
        observations = assessment.get("observations") or []
    for obs in observations:
        if not isinstance(obs, dict):
            continue
        region = obs.get("region")
        if region is None:
            continue
        if not isinstance(region, dict):
            return "region is not an x/y/w/h object"
        for axis in ("x", "y", "w", "h"):
            value = region.get(axis)
            if isinstance(value, bool) or not isinstance(
                    value, (int, float)):
                return f"region {axis} is not a number"
            if value < 0 or value > 1000:
                return f"region {axis} is outside the 0-1000 scale"
    return None


def incident_start(*readings):
    """The earliest parseable timestamp across the readings, as the
    original string. Returns None when none carries a timestamp."""
    best = None
    best_epoch = None
    for reading in readings:
        if not isinstance(reading, dict):
            continue
        stamp = reading.get("timestamp")
        assessment = reading.get("assessment")
        if stamp is None and isinstance(assessment, dict):
            stamp = assessment.get("timestamp")
        if not isinstance(stamp, str) or not stamp:
            continue
        text = stamp[:-1] + "+00:00" if stamp.endswith("Z") else stamp
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            continue
        epoch = parsed.timestamp()
        if best_epoch is None or epoch < best_epoch:
            best_epoch, best = epoch, stamp
    return best


def build_verdict_record(*, at, verdict, category, judge_mode,
                         judge_reasons, job_id, model, latency_ms,
                         error, summary, first_timestamp=None,
                         review_timestamp=None):
    """One verdict-record builder for both the deterministic and the
    model path. The two paths emit the identical key set; judge_mode
    is limited to the two implemented values."""
    if judge_mode not in ("deterministic", "model"):
        raise ValueError(f"unknown judge_mode: {judge_mode!r}")
    return {
        "at": at, "step": "review", "verdict": verdict,
        "category": category, "judged_by": "imperium-judge",
        "judge_mode": judge_mode, "judge_reasons": judge_reasons,
        "job_id": job_id, "model": model, "latency_ms": latency_ms,
        "error": error, "summary": summary, "status": None,
        "started_at": incident_start(
            {"timestamp": first_timestamp},
            {"timestamp": review_timestamp}),
    }


def _normalise_category(category):
    if not isinstance(category, str):
        return category
    return category.strip().lower()


def combine(division, first_category, review_category, review_ok,
            is_flagged):
    """The judge's ruling on two readings. is_flagged(division,
    category) is the caller's flagged-category check (crew_common).
    Returns (verdict, reasons) — reasons are plain strings the
    caller records on the incident timeline."""
    review_category = _normalise_category(review_category)
    first_category = _normalise_category(first_category)
    if not review_ok or review_category is None:
        return "inconclusive", [
            "the review reading failed or carried no category; "
            "the judge does not confirm on a missing reading"]
    if first_category is None:
        return "inconclusive", [
            "the patrol reading carried no category; the judge does "
            "not confirm on a missing reading"]
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


def _prompt_payload(reading):
    """Only the fields the judge needs: product, timestamp, and the
    assessment block. Other incident data is never copied into the
    prompt."""
    if not isinstance(reading, dict):
        return reading
    payload = {}
    for key in ("product", "timestamp", "assessment"):
        if key in reading:
            payload[key] = reading[key]
    return payload


def build_judge_prompt(division, first_result, review_result):
    """The adjudication prompt for the judge job kind: the judge
    reads BOTH agents' assessments of the same frame and rules.
    JSON only, the verdict shape parse_verdict accepts."""
    for reading in (first_result, review_result):
        error = validate_reading(reading)
        if error:
            raise ValueError(error)
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
        f"First reading: {json.dumps(_prompt_payload(first_result))[:1200]}",
        f"Second reading: {json.dumps(_prompt_payload(review_result))[:1200]}",
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
