"""musica take-log schema (HN-028).

Every composition attempt is recorded: prompt, seed/params, duration,
verdict, reason. This module follows the repo's validator convention
(worlds/validate_pack.py, intel/brief.py validate_brief_record):
validate_take is a pure function, no I/O, errors as strings; the
append/read helpers are the only I/O.

A take record:
  take_id: "take-001" style id, unique within its session
  session_id: non-empty string
  timestamp: ISO-8601 with a T separator and a timezone (Z or offset)
  brief_id: genre brief token, e.g. "chipsynth"
  prompt: non-empty string, the brief text the loop rendered from
  seed: int >= 0 (the loop is deterministic: same seed + params
    renders byte-identical audio)
  params: object with tempo (bpm), key, mode, waveform, bars
  duration_s: number > 0, measured from the rendered file
  file: non-empty string path to the rendered audio (relative to
    the session dir when the file is committed alongside the log)
  sha256: 64 lowercase hex of the rendered file
  verdict: "keeper" | "reject" | "pending"
  reason: non-empty string for keeper/reject; may be "" for pending
  spark_assist: null, or an object {status, prompt_sha256} where
    status is "held" | "not_configured" | "sent" (never a fabricated
    model reply: in this sandbox there is no key, so every attempt
    records "not_configured" and no call is sent)
  human_verdict: null, or an object {pick, timestamp} from the
    blind A/B harness (HN-039)
"""

import hashlib
import json
import os
import re

TAKE_ID_RE = re.compile(r"^take-\d{3,}$")
BRIEF_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# ISO-8601 with T separator and timezone, real calendar shape.
TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
VERDICTS = ("keeper", "reject", "pending")
SPARK_STATUSES = ("held", "not_configured", "sent")

PARAM_FIELDS = {
    "tempo": (int, float),
    "key": str,
    "mode": str,
    "waveform": str,
    "bars": int,
}


def _nonempty_str(value):
    return isinstance(value, str) and bool(value.strip())


def validate_take(record):
    """Return a list of contract errors for one take record."""
    errors = []
    if not isinstance(record, dict):
        return ["take record is not a JSON object"]
    if not isinstance(record.get("take_id"), str) or not TAKE_ID_RE.match(
        record["take_id"]
    ):
        errors.append("take_id must look like take-001")
    if not _nonempty_str(record.get("session_id")):
        errors.append("session_id must be a non-empty string")
    ts = record.get("timestamp")
    if not isinstance(ts, str) or not TIMESTAMP_RE.match(ts):
        errors.append("timestamp must be ISO-8601 with T and timezone")
    if not isinstance(record.get("brief_id"), str) or not BRIEF_ID_RE.match(
        record["brief_id"]
    ):
        errors.append("brief_id must be a lowercase token")
    if not _nonempty_str(record.get("prompt")):
        errors.append("prompt must be a non-empty string")
    seed = record.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        errors.append("seed must be an int >= 0")
    params = record.get("params")
    if not isinstance(params, dict):
        errors.append("params must be an object")
    else:
        for field, types in PARAM_FIELDS.items():
            if not isinstance(params.get(field), types) or isinstance(
                params.get(field), bool
            ):
                errors.append("params.%s has the wrong type" % field)
        tempo = params.get("tempo")
        if isinstance(tempo, (int, float)) and not 40 <= tempo <= 240:
            errors.append("params.tempo must be 40..240 bpm")
        bars = params.get("bars")
        if isinstance(bars, int) and bars < 1:
            errors.append("params.bars must be >= 1")
    duration = record.get("duration_s")
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or duration <= 0
    ):
        errors.append("duration_s must be a number > 0")
    if not _nonempty_str(record.get("file")):
        errors.append("file must be a non-empty string path")
    if not isinstance(record.get("sha256"), str) or not SHA256_RE.match(
        record["sha256"]
    ):
        errors.append("sha256 must be 64 lowercase hex")
    verdict = record.get("verdict")
    if verdict not in VERDICTS:
        errors.append("verdict must be one of %s" % ", ".join(VERDICTS))
    reason = record.get("reason")
    if not isinstance(reason, str):
        errors.append("reason must be a string")
    elif verdict in ("keeper", "reject") and not reason.strip():
        errors.append("reason must be non-empty for keeper/reject")
    spark = record.get("spark_assist")
    if spark is not None:
        if not isinstance(spark, dict):
            errors.append("spark_assist must be null or an object")
        else:
            if spark.get("status") not in SPARK_STATUSES:
                errors.append("spark_assist.status must be one of %s"
                              % ", ".join(SPARK_STATUSES))
            if not isinstance(spark.get("prompt_sha256"), str) or not SHA256_RE.match(
                spark["prompt_sha256"]
            ):
                errors.append("spark_assist.prompt_sha256 must be 64 lowercase hex")
    human = record.get("human_verdict")
    if human is not None:
        if not isinstance(human, dict):
            errors.append("human_verdict must be null or an object")
        else:
            if not _nonempty_str(human.get("pick")):
                errors.append("human_verdict.pick must be a non-empty string")
            if not isinstance(human.get("timestamp"), str) or not TIMESTAMP_RE.match(
                human["timestamp"]
            ):
                errors.append("human_verdict.timestamp must be ISO-8601 with T and timezone")
    return errors


def append_take(log_path, record):
    """Validate and append one take record as a JSON line. Returns record."""
    errors = validate_take(record)
    if errors:
        raise ValueError("invalid take record: %s" % "; ".join(errors))
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return record


def read_log(log_path):
    """Read a take log (JSONL) into a list, validating every entry."""
    takes = []
    if not os.path.exists(log_path):
        return takes
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            errors = validate_take(record)
            if errors:
                raise ValueError("invalid take in log: %s" % "; ".join(errors))
            takes.append(record)
    return takes


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
