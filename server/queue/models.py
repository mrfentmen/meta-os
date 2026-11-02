"""models.py — the Meta OS multi-model client (Meta Model API).

One module for every Meta model the platform calls, so no program
grows its own transport. Verified live against the account on
2026-11-02 (Pax probes, recorded in os-build/MODEL_INTEGRATION.md):

  muse-spark-1.3            POST /v1/chat/completions   (reasoning,
                            vision assessment — spark_gen's lane)
  muse-wonder-1.0           POST /v1/chat/completions   (multimodal
                            second reader)
  sam-3.1                   POST /v1/responses          (segmentation:
                            box + encoded mask per image)
  muse-image-1.0            POST /v1/responses          (image
                            generation; result is base64 in an
                            image_generation_call output item)
  muse-voice-transcribe-1.0 listed by GET /v1/models, but its call
                            surface is NOT resolved: /v1/audio/
                            transcriptions returned 404 and the
                            Responses/chat surfaces returned
                            model_not_found for it (probed
                            2026-11-02). transcribe() below raises
                            EndpointUnresolvedError until a working
                            surface is verified — it never guesses.

Transport mirrors spark_gen.py's production pattern: SPARK_API_KEY
from the process environment ONLY (never a file, a request, or a
job envelope), every call through spark_guardrail ($75 hard stop),
redirects refused, and the key value is never printed or logged.
Every call also appends one JSON receipt line (model, surface,
usage, latency, dollar estimate where a published rate exists) to
the receipts file — METAOS_MODEL_RECEIPTS if set, else
model_receipts.jsonl beside this module. Only Muse Spark carries a
published rate card ($1.25/M in, $4.25/M out), so only Spark
receipts carry a dollar estimate; the other models' receipts carry
their raw usage with est_cost_usd null.
"""

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spark_guardrail  # noqa: E402

CHAT_ENDPOINT = "https://api.meta.ai/v1/chat/completions"
RESPONSES_ENDPOINT = "https://api.meta.ai/v1/responses"

SPARK = "muse-spark-1.3"
WONDER = "muse-wonder-1.0"
SAM = "sam-3.1"
IMAGE = "muse-image-1.0"
VOICE = "muse-voice-transcribe-1.0"

MODELS = {
    SPARK: {"surface": "chat", "role": "reasoning + vision assessment"},
    WONDER: {"surface": "chat", "role": "multimodal second reader"},
    SAM: {"surface": "responses", "role": "image segmentation"},
    IMAGE: {"surface": "responses", "role": "image generation"},
    VOICE: {"surface": None, "role": "speech transcription (unresolved)"},
}


class EndpointUnresolvedError(RuntimeError):
    """A model is listed on the account but no call surface for it
    has been verified. Raised instead of guessing an endpoint."""


def _key():
    key = os.environ.get("SPARK_API_KEY")
    if not key:
        raise RuntimeError(
            "SPARK_API_KEY is not set in the environment: no model "
            "transport is configured")
    return key


def _receipts_path():
    return os.environ.get("METAOS_MODEL_RECEIPTS") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "model_receipts.jsonl")


def _receipt(kind, model, surface, usage, latency_ms):
    est = None
    if model == SPARK and isinstance(usage, dict):
        est = spark_guardrail.estimate(usage)
    line = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind, "model": model, "surface": surface,
        "usage": usage, "latency_ms": latency_ms, "est_cost_usd": est,
    }
    try:
        with open(_receipts_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
    except OSError:
        pass  # a receipt write failure never fails the model call
    return line


RECEIPT_FIELDS = ("ts", "kind", "model", "surface", "usage",
                  "latency_ms", "est_cost_usd")


def validate_receipt(line):
    """Validate one receipt record. Raises ValueError naming the
    missing field, or naming the model id when it is absent/blank —
    an unattributed model call is a broken receipt, not a record."""
    if not isinstance(line, dict):
        raise ValueError("receipt is not a JSON object")
    missing = [f for f in RECEIPT_FIELDS if f not in line]
    if missing:
        raise ValueError(
            "receipt missing required field(s): " + ", ".join(missing))
    model = line.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("receipt has no model id")
    return line


def validate_receipts(path):
    """Validate every JSONL receipt line. Returns the number of
    records checked; raises ValueError with the line number and the
    failing field on the first bad record."""
    count = 0
    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                line = json.loads(raw)
            except ValueError as exc:
                raise ValueError(
                    f"receipt line {n} is not JSON: {exc}") from exc
            try:
                validate_receipt(line)
            except ValueError as exc:
                raise ValueError(f"receipt line {n}: {exc}") from exc
            count += 1
    return count


def _post(url, body, kind):
    """One guardrailed POST (budget check before the call).
    Returns (payload, latency_ms). Recording happens in
    _record_call, called by each public function once it holds
    the payload."""
    spark_guardrail.check()
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {_key()}",
                 "User-Agent": "MetaOS-Models/1.0"})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args):
            raise RuntimeError("redirect refused, verify the endpoint")

    started = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect()).open(
                req, timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"model request ({kind}) failed with HTTP {e.code}")
    latency_ms = round((time.monotonic() - started) * 1000)
    return payload, latency_ms


def _record_call(kind, payload, fallback_model, surface, latency_ms):
    model = payload.get("model") or fallback_model
    spark_guardrail.record(kind, model, payload.get("usage"), latency_ms)
    _receipt(kind, model, surface, payload.get("usage"), latency_ms)


def _chat_content(payload):
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part["text"] for part in content
            if isinstance(part, dict) and part.get("type") == "text"
            and isinstance(part.get("text"), str))
    return None


def chat_text(model, prompt, max_tokens=1200):
    """One text chat call (Spark or Wonder). Returns
    (text, model_reported, latency_ms); raises on any failure —
    callers never receive a fabricated reply."""
    if MODELS.get(model, {}).get("surface") not in ("chat",):
        raise EndpointUnresolvedError(
            f"{model} is not a chat-surface model in the verified "
            f"registry: {MODELS.get(model)}")
    payload, latency_ms = _post(CHAT_ENDPOINT, {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        }, f"chat:{model}")
    _record_call(f"chat:{model}", payload, model, "chat", latency_ms)
    text = _chat_content(payload)
    if text is None:
        raise RuntimeError(f"{model} response carried no message content")
    return text, payload.get("model") or model, latency_ms


def chat_image(model, prompt, image_bytes, max_tokens=1600):
    """One chat call carrying a JPEG frame (Spark or Wonder): the
    same content shape spark_gen's direct transport uses (a text
    part plus an image_url part with the JPEG as a data URL).
    Returns (text, model_reported, latency_ms); raises on any
    failure — callers never receive a fabricated reply."""
    if MODELS.get(model, {}).get("surface") not in ("chat",):
        raise EndpointUnresolvedError(
            f"{model} is not a chat-surface model in the verified "
            f"registry: {MODELS.get(model)}")
    data_url = "data:image/jpeg;base64," + \
        base64.b64encode(image_bytes).decode()
    payload, latency_ms = _post(CHAT_ENDPOINT, {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}],
        "max_tokens": max_tokens,
        }, f"chat-image:{model}")
    _record_call(f"chat-image:{model}", payload, model, "chat",
                 latency_ms)
    text = _chat_content(payload)
    if text is None:
        raise RuntimeError(f"{model} response carried no message content")
    return text, payload.get("model") or model, latency_ms


def _responses_text(payload):
    for item in payload.get("output") or []:
        if item.get("type") == "message":
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    return part.get("text")
    return None


_SAM_BOX = re.compile(
    r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")
_SAM_MASK = re.compile(r"<\|mask;x=(\d+);y=(\d+);data=(.*?)\|>", re.DOTALL)


def parse_sam_text(text):
    """Parse SAM 3.1's output text into a region record.

    Verified live format (2026-11-02):
      <|box;x1=8;y1=0;x2=599;y2=354;w=600;h=470|><|mask;x=0;y=0;data=...|>
    The box is in image pixels; `region` is the same box on the
    platform's 0-1000 contract scale. Raises ValueError when no box
    is present — a segmentation without a box is not a region, and
    this function never invents one."""
    m = _SAM_BOX.search(text or "")
    if not m:
        raise ValueError("SAM output carried no <|box;...|> segment")
    x1, y1, x2, y2, w, h = (int(g) for g in m.groups())
    if w <= 0 or h <= 0 or x2 < x1 or y2 < y1:
        raise ValueError(f"SAM box is malformed: {m.group(0)}")
    region = {
        "x": round(x1 / w * 1000), "y": round(y1 / h * 1000),
        "w": round((x2 - x1) / w * 1000), "h": round((y2 - y1) / h * 1000),
    }
    mask = None
    mm = _SAM_MASK.search(text or "")
    if mm:
        mask = {"x": int(mm.group(1)), "y": int(mm.group(2)),
                "data": mm.group(3)}
    return {"box_px": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "image_size": {"w": w, "h": h},
            "region": region, "mask": mask}


def segment(image_bytes, prompt_text):
    """SAM 3.1 segmentation of one JPEG. Returns the parse_sam_text
    record plus the reporting fields. Raises on any failure."""
    data_url = "data:image/jpeg;base64," + \
        base64.b64encode(image_bytes).decode()
    payload, latency_ms = _post(RESPONSES_ENDPOINT, {
        "model": SAM,
        "input": [{"role": "user", "content": [
            {"type": "input_text", "text": prompt_text},
            {"type": "input_image", "image_url": data_url}]}],
        }, "segment:sam-3.1")
    _record_call("segment:sam-3.1", payload, SAM, "responses", latency_ms)
    text = _responses_text(payload)
    if text is None:
        raise RuntimeError("SAM response carried no output text")
    record = parse_sam_text(text)
    record["model"] = payload.get("model") or SAM
    record["latency_ms"] = latency_ms
    record["raw_text_len"] = len(text)
    return record


def detect_image_format(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:2] == b"\xff\xd8":
        return "jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return "unknown"


def generate_image(prompt_text):
    """Muse Image generation. Returns (image_bytes, format,
    model_reported, latency_ms). The base64 result rides in the
    image_generation_call output item (verified 2026-11-02).
    Raises on any failure — never returns a placeholder image."""
    payload, latency_ms = _post(RESPONSES_ENDPOINT, {
        "model": IMAGE, "input": prompt_text,
        }, "image:muse-image-1.0")
    _record_call("image:muse-image-1.0", payload, IMAGE, "responses",
                 latency_ms)
    for item in payload.get("output") or []:
        if item.get("type") == "image_generation_call" and \
                item.get("result"):
            data = base64.b64decode(item["result"])
            return data, detect_image_format(data), \
                payload.get("model") or IMAGE, latency_ms
    raise RuntimeError("Muse Image response carried no image result")


def transcribe(audio_bytes, audio_format="mp3"):
    """Muse Voice Transcribe — NOT WIRED. The model is listed on
    the account (GET /v1/models, 2026-11-02) but every probed call
    surface failed: POST /v1/audio/transcriptions -> 404,
    /v1/responses and /v1/chat/completions with input audio ->
    model_not_found. Until a working surface is verified, this
    raises instead of guessing."""
    raise EndpointUnresolvedError(
        "muse-voice-transcribe-1.0: no verified call surface yet "
        "(probed 2026-11-02: /v1/audio/transcriptions 404; "
        "Responses and chat surfaces returned model_not_found)")
