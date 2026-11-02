"""Named-field validation for a livecam record file.

A livecam record is what the camera lane files on disk
(server/queue/livecam_records/live-reading.json): the frame that was
fetched, how it was fetched, and the assessment that came back.

    {"frame": {camera_id, camera_name, area, latitude, longitude,
               source, image_url, fetched_at, image_sha256,
               image_bytes, live},
     "fetch_route": "...",
     "reading": {"result": <v2 record>, "model": "...", "latency_ms": n}}

The reading's outcome is `reading.result.assessment.category`, and it
must be one of the product's categories from js/products.js -- the same
table the assessor's prompt is built from (spark_gen.py), so a category
the model was never offered is reported here rather than filed.

Returns named errors; [] when the record is valid. Never mutates or
repairs a record. The v2 block itself is checked by record_validate.py.

Zero dependencies outside this directory: stdlib + record_validate.
"""

import re

import trio_repo

from record_validate import validate_v2_incident

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FRAME_KEYS = ("camera_id", "camera_name", "area", "latitude", "longitude",
              "source", "image_url", "fetched_at", "image_sha256",
              "image_bytes", "live")
RECORD_KEYS = ("frame", "fetch_route", "reading")
READING_KEYS = ("result", "model", "latency_ms")


def _is_text(value):
    return isinstance(value, str) and value.strip() != ""


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_frame(frame, errors):
    if not isinstance(frame, dict):
        errors.append("frame: must be an object")
        return
    for key in FRAME_KEYS:
        if key not in frame:
            errors.append("frame." + key + ": missing")
    for key in frame:
        if key not in FRAME_KEYS:
            errors.append("frame." + key + ": unexpected field")
    for key in ("camera_id", "camera_name", "area", "source", "image_url"):
        if key in frame and not _is_text(frame[key]):
            errors.append("frame." + key + ": must be a non-empty string")
    for key in ("latitude", "longitude"):
        if key in frame:
            value = frame[key]
            if not _is_number(value):
                errors.append("frame." + key + ": must be a number")
            elif not -180 <= value <= 180:
                errors.append("frame." + key + ": must be -180..180")
    if "fetched_at" in frame:
        from datetime import datetime
        value = frame["fetched_at"]
        try:
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            errors.append("frame.fetched_at: must be an ISO-8601 string")
    if "image_sha256" in frame:
        if not isinstance(frame["image_sha256"], str) or not SHA256_RE.match(
                frame["image_sha256"]):
            errors.append("frame.image_sha256: must be 64 lowercase hex chars")
    if "image_bytes" in frame:
        value = frame["image_bytes"]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append("frame.image_bytes: must be a positive integer")
    if "live" in frame and not isinstance(frame["live"], bool):
        errors.append("frame.live: must be a boolean")


def _validate_reading(reading, categories, errors):
    if not isinstance(reading, dict):
        errors.append("reading: must be an object")
        return
    for key in READING_KEYS:
        if key not in reading:
            errors.append("reading." + key + ": missing")
    for key in reading:
        if key not in READING_KEYS:
            errors.append("reading." + key + ": unexpected field")
    if "model" in reading and not _is_text(reading["model"]):
        errors.append("reading.model: must be a non-empty string")
    if "latency_ms" in reading:
        value = reading["latency_ms"]
        if value is not None and (not _is_number(value) or value < 0):
            errors.append("reading.latency_ms: must be a number >= 0 or null")

    result = reading.get("result")
    for error in validate_v2_incident(result):
        errors.append("reading.result." + error)

    if isinstance(result, dict) and isinstance(result.get("assessment"), dict):
        outcome = result["assessment"].get("category")
        if _is_text(outcome) and outcome not in categories:
            errors.append(
                "reading.result.assessment.category: unknown category "
                + repr(outcome))
    if isinstance(result, dict) and isinstance(result.get("observations"), list):
        for i, obs in enumerate(result["observations"]):
            if not isinstance(obs, dict):
                continue
            category = obs.get("category")
            if _is_text(category) and category not in categories:
                errors.append(
                    "reading.result.observations[" + str(i)
                    + "].category: unknown category " + repr(category))


def categories_for(product):
    """The product's category table, from js/products.js."""
    return frozenset(trio_repo.product_profile(product)["categories"])


def validate_livecam_record(record, categories=None):
    """Return named errors for one livecam record; [] when valid."""
    if not isinstance(record, dict):
        return ["record: must be an object"]
    errors = []
    for key in RECORD_KEYS:
        if key not in record:
            errors.append("missing required field: " + key)
    for key in record:
        if key not in RECORD_KEYS:
            errors.append("unexpected field: " + key)
    _validate_frame(record.get("frame"), errors)
    if "fetch_route" in record and not _is_text(record["fetch_route"]):
        errors.append("fetch_route: must be a non-empty string")

    if categories is None:
        product = None
        reading = record.get("reading")
        if isinstance(reading, dict) and isinstance(reading.get("result"), dict):
            product = reading["result"].get("product")
        if _is_text(product):
            categories = categories_for(product)
        else:
            categories = frozenset()
    _validate_reading(record.get("reading"), categories, errors)
    return errors
