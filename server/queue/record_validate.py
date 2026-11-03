"""Named-field validation for the v2 assessment-contract record.

The v2 contract is the shape every assessor answers with and the shape
an incident carries on its own timeline: product, timestamp,
observations, assessment, processing (spark_gen.py builds it; a real
record is filed at livecam_records/live-reading.json).

A validator here never mutates, repairs, or fills a record: it returns
a list of named errors, empty when the record is good. Each error is
"<field path>: <what is wrong>", so a caller can log it and point at
the field. The storage record in crew_records.py (id, status,
evidence, ...) is a different shape and keeps its own validator.

Zero dependencies: stdlib datetime only.
"""

from datetime import datetime

REQUIRED_KEYS = ("product", "timestamp", "observations",
                 "assessment", "processing")
OBSERVATION_KEYS = ("category", "description", "evidence",
                    "confidence", "region")
REGION_KEYS = ("x", "y", "w", "h")
REGION_MAX = 1000


def _is_number(value):
    # bool is an int subclass in Python; true must not read as 1.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_text(value):
    return isinstance(value, str) and value.strip() != ""


def _is_timestamp(value):
    if not _is_text(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _validate_region(path, region, errors):
    if not isinstance(region, dict):
        errors.append(path + ": must be an object or null")
        return
    for key in REGION_KEYS:
        if key not in region:
            errors.append(path + "." + key + ": missing")
            continue
        value = region[key]
        if not _is_number(value) or value != int(value):
            errors.append(path + "." + key + ": must be an integer")
        elif not 0 <= value <= REGION_MAX:
            errors.append(path + "." + key + ": must be 0.." + str(REGION_MAX))
    for key in region:
        if key not in REGION_KEYS:
            errors.append(path + "." + key + ": unexpected field")


def _validate_observation(path, obs, errors):
    if not isinstance(obs, dict):
        errors.append(path + ": must be an object")
        return
    for key in ("category", "description"):
        if key not in obs:
            errors.append(path + "." + key + ": missing")
        elif not _is_text(obs[key]):
            errors.append(path + "." + key + ": must be a non-empty string")
    if "evidence" in obs and not _is_text(obs["evidence"]):
        errors.append(path + ".evidence: must be a non-empty string")
    if "confidence" in obs and obs["confidence"] is not None:
        confidence = obs["confidence"]
        if not _is_number(confidence):
            errors.append(path + ".confidence: must be a number or null")
        elif not 0 <= confidence <= 1:
            errors.append(path + ".confidence: must be 0..1")
    if "region" in obs and obs["region"] is not None:
        _validate_region(path + ".region", obs["region"], errors)
    for key in obs:
        if key not in OBSERVATION_KEYS:
            errors.append(path + "." + key + ": unexpected field")


def _validate_assessment(path, assessment, errors):
    if not isinstance(assessment, dict):
        errors.append(path + ": must be an object")
        return
    for key in ("category", "summary"):
        if key not in assessment:
            errors.append(path + "." + key + ": missing")
        elif not _is_text(assessment[key]):
            errors.append(path + "." + key + ": must be a non-empty string")
    if "uncertainty" in assessment:
        notes = assessment["uncertainty"]
        if not isinstance(notes, list):
            errors.append(path + ".uncertainty: must be a list")
        else:
            for i, note in enumerate(notes):
                if not _is_text(note):
                    errors.append(
                        path + ".uncertainty[" + str(i) + "]: must be a non-empty string")
    if "requires_human_review" in assessment:
        if not isinstance(assessment["requires_human_review"], bool):
            errors.append(path + ".requires_human_review: must be a boolean")
    for key in assessment:
        if key not in ("category", "summary", "uncertainty",
                       "requires_human_review"):
            errors.append(path + "." + key + ": unexpected field")


def _validate_processing(path, processing, errors):
    if not isinstance(processing, dict):
        errors.append(path + ": must be an object")
        return
    if "model" not in processing:
        errors.append(path + ".model: missing")
    elif not _is_text(processing["model"]):
        errors.append(path + ".model: must be a non-empty string")
    if "latency_ms" not in processing:
        errors.append(path + ".latency_ms: missing")
    else:
        latency = processing["latency_ms"]
        if latency is not None and (not _is_number(latency) or latency < 0):
            errors.append(path + ".latency_ms: must be a number >= 0 or null")
    for key in processing:
        if key not in ("model", "latency_ms"):
            errors.append(path + "." + key + ": unexpected field")


def validate_v2_incident(record):
    """Return named errors for one v2 incident record; [] when valid."""
    if not isinstance(record, dict):
        return ["record: must be an object"]
    errors = []
    for key in REQUIRED_KEYS:
        if key not in record:
            errors.append("missing required field: " + key)
    for key in record:
        if key not in REQUIRED_KEYS:
            errors.append("unexpected field: " + key)
    if "product" in record and not _is_text(record["product"]):
        errors.append("product: must be a non-empty string")
    if "timestamp" in record and not _is_timestamp(record["timestamp"]):
        errors.append("timestamp: must be an ISO-8601 string")
    if "observations" in record:
        observations = record["observations"]
        if not isinstance(observations, list):
            errors.append("observations: must be a list")
        elif not observations:
            errors.append("observations: must not be empty")
        else:
            for i, obs in enumerate(observations):
                _validate_observation("observations[" + str(i) + "]", obs, errors)
    if "assessment" in record:
        _validate_assessment("assessment", record["assessment"], errors)
    if "processing" in record:
        _validate_processing("processing", record["processing"], errors)
    return errors
