"""Named-field validation for the v2 judge verdict record.

`judge.build_verdict_record` is the single builder both the
deterministic and the model path use, so the key set below is exact,
not a guess: at, step, verdict, category, judged_by, judge_mode,
judge_reasons, job_id, model, latency_ms, error, summary, status,
started_at.

Task CB2-373 names the fields "outcome" and "tier". The record the
judge ships has neither. The ruling is `verdict` (confirmed / cleared /
inconclusive, from judge._VERDICTS) and the deciding path is
`judge_mode` (deterministic | model). This validator checks the real
fields and says so rather than accepting a shape nothing writes.

Returns a list of named errors; [] when the record is valid. Never
mutates, repairs, or fills a field.

Zero dependencies: stdlib datetime only.
"""

from datetime import datetime

VERDICTS = ("confirmed", "cleared", "inconclusive")
JUDGE_MODES = ("deterministic", "model")
REQUIRED_KEYS = (
    "at", "step", "verdict", "category", "judged_by", "judge_mode",
    "judge_reasons", "job_id", "model", "latency_ms", "error",
    "summary", "status", "started_at",
)


def _is_text(value):
    return isinstance(value, str) and value.strip() != ""


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_timestamp(value):
    if not _is_text(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_verdict_record(record):
    """Return named errors for one v2 verdict record; [] when valid."""
    if not isinstance(record, dict):
        return ["record: must be an object"]
    errors = []
    for key in REQUIRED_KEYS:
        if key not in record:
            errors.append("missing required field: " + key)
    for key in record:
        if key not in REQUIRED_KEYS:
            errors.append("unexpected field: " + key)

    if "step" in record and record["step"] != "review":
        errors.append("step: must be review")
    if "verdict" in record and record["verdict"] not in VERDICTS:
        errors.append(
            "verdict: must be one of " + ", ".join(VERDICTS))
    if "judge_mode" in record and record["judge_mode"] not in JUDGE_MODES:
        errors.append(
            "judge_mode: must be one of " + ", ".join(JUDGE_MODES))
    if "category" in record and not _is_text(record["category"]):
        errors.append("category: must be a non-empty string")
    if "judged_by" in record and record["judged_by"] != "imperium-judge":
        errors.append("judged_by: must be imperium-judge")
    if "judge_reasons" in record:
        reasons = record["judge_reasons"]
        if not isinstance(reasons, list):
            errors.append("judge_reasons: must be a list")
        else:
            for i, reason in enumerate(reasons):
                if not _is_text(reason):
                    errors.append(
                        "judge_reasons[" + str(i) + "]: must be a non-empty string")
    if "job_id" in record and not _is_text(record["job_id"]):
        errors.append("job_id: must be a non-empty string")
    if "model" in record:
        if record["model"] is not None and not _is_text(record["model"]):
            errors.append("model: must be a non-empty string or null")
    if "latency_ms" in record:
        latency = record["latency_ms"]
        if latency is not None and (not _is_number(latency) or latency < 0):
            errors.append("latency_ms: must be a number >= 0 or null")
    if "error" in record:
        if record["error"] is not None and not _is_text(record["error"]):
            errors.append("error: must be a non-empty string or null")
    if "summary" in record:
        if record["summary"] is not None and not _is_text(record["summary"]):
            errors.append("summary: must be a non-empty string or null")
    if "status" in record:
        if record["status"] is not None and not _is_text(record["status"]):
            errors.append("status: must be a non-empty string or null")
    if "at" in record and not _is_timestamp(record["at"]):
        errors.append("at: must be an ISO-8601 string")
    if "started_at" in record:
        value = record["started_at"]
        if value is not None and not _is_timestamp(value):
            errors.append("started_at: must be an ISO-8601 string or null")
    return errors
