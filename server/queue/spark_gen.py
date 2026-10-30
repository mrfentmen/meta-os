"""spark_gen.py — the resident agent's generation transport.

One pluggable module, two transports, chosen by environment:

  (a) PRODUCTION (default): SPARK_API_KEY is read from the process
      environment ONLY — never from a file, a request, or a job
      envelope — and the call goes direct to
      POST https://api.meta.ai/v1/chat/completions, model
      muse-spark-1.3, with OpenAI-style content parts (a text prompt
      plus an image_url part carrying the JPEG as a data URL). That
      is the exact shape Rowan's SPARK-TRANSPORT-1 uses in
      server/model.mjs; the prompt text below mirrors
      buildSparkPrompt() there, fed by the product profiles in
      js/products.js (loaded via trio_repo). Every direct call passes
      through spark_guardrail ($75 hard stop). The key value is never
      printed, logged, or written anywhere by this module.

  (b) DEV (TRIO_SPARK_VIA_HELPER=1): delegate to the connector
      helper ~/workspace/custom-connectors/custom.meta-model-api/bin/
      spark_call.py `assess`, which reaches the vaulted key through
      the credential surrogate. This is the only transport reachable
      from the Pax sandbox (the raw key never enters it), and it is
      the path the 2026-10-30 live proofs ran on. The helper's own
      guardrail_state.json counts those calls; this module's
      guardrail is not double-applied on that path.

generate() returns (assessment_dict, model_reported, latency_ms) and
raises on any failure — callers turn that into a failed result
envelope, never a fabricated assessment.
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spark_guardrail  # noqa: E402
import trio_repo  # noqa: E402

SPARK_ENDPOINT = "https://api.meta.ai/v1/chat/completions"
SPARK_MODEL = "muse-spark-1.3"
SPARK_CALL = os.path.expanduser(
    "~/workspace/custom-connectors/custom.meta-model-api/bin/spark_call.py")
MODEL_FALLBACK = SPARK_MODEL


def via_helper():
    return os.environ.get("TRIO_SPARK_VIA_HELPER") == "1"


# -- shared text handling (mirrors server/model.mjs) --------------------

def unwrap_model_text(text):
    """extractJson() from model.mjs: tolerate a ``` fence and prose
    around the object; a parse failure later still raises instead of
    inventing a value."""
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.split("\n")
        lines = lines[1:]
        t = "\n".join(lines).strip()
        if t.endswith("```"):
            t = t[:-3].strip()
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start:end + 1]
    return t


def _message_content(data):
    try:
        content = data["choices"][0]["message"]["content"]
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


def build_prompt(product, timestamp, correction=None):
    """buildSparkPrompt() from server/model.mjs, verbatim lines, fed
    by the js/products.js profile for this product. When `correction`
    is given (the resident agent's bounded self-correction retry), it
    carries the validateAssessment errors the previous reply failed;
    they are appended as a final instruction to return corrected
    JSON only."""
    p = trio_repo.product_profile(product)
    categories = ", ".join(p["categories"])
    lines = [
        f"You are the visual assessment model for {p['displayName']} "
        f"({p['department']}).",
        "Look at the attached image and return JSON ONLY, no prose, no "
        "markdown fences, matching this shape exactly:",
        "{",
        f'  "product": "{product}",',
        f'  "timestamp": "{timestamp}",',
        '  "observations": [{"category": "<one of the categories below>", '
        '"description": "<what is visible>", "evidence": "<where in the '
        'frame>", "confidence": <0..1 or null>}],',
        '  "assessment": {"category": "<one of the categories below>", '
        '"summary": "<one or two sentences>", "uncertainty": ["<anything '
        'unclear>"], "requires_human_review": <true|false>},',
        f'  "processing": {{"model": "{SPARK_MODEL}", "latency_ms": null}}',
        "}",
        f"Categories (assessment.category and every observation category "
        f"must be one of these): {categories}.",
        f"Limits: {p['limitations']}",
        "Describe only what is visible in the image. This is supplementary "
        "awareness only: never dispatch, never claim certainty beyond "
        "what is visible. When unsure, use indeterminate and set "
        "requires_human_review to true.",
    ]
    if correction:
        lines += [
            "CORRECTION: a previous reply for this same frame failed "
            "these contract checks: " + str(correction),
            "Return corrected JSON only, matching the shape above "
            "exactly. Do not repeat the failed checks.",
        ]
    return "\n".join(lines)


# -- transport (a): direct, SPARK_API_KEY from the environment ----------

def _generate_direct(product, image_bytes, timestamp, correction=None):
    key = os.environ.get("SPARK_API_KEY")
    if not key:
        raise RuntimeError(
            "SPARK_API_KEY is not set in the environment and "
            "TRIO_SPARK_VIA_HELPER is not 1: no generation transport "
            "is configured")
    spark_guardrail.check()
    data_url = "data:image/jpeg;base64," + \
        base64.b64encode(image_bytes).decode()
    body = {
        "model": SPARK_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text",
                 "text": build_prompt(product, timestamp, correction)},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
    }
    req = urllib.request.Request(
        SPARK_ENDPOINT, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}",
                 "User-Agent": "MetaTrio-QueueAgent/1.0"})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args):
            raise RuntimeError("redirect refused, verify the endpoint")

    started = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect()).open(
                req, timeout=240) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Spark request failed with HTTP {e.code}")
    latency_ms = round((time.monotonic() - started) * 1000)
    spark_guardrail.record(f"assess:{product}",
                           payload.get("model", SPARK_MODEL),
                           payload.get("usage"), latency_ms)
    content = _message_content(payload)
    if not content:
        raise RuntimeError("Spark response carried no message content")
    assessment = json.loads(unwrap_model_text(content))
    if not isinstance(assessment, dict):
        raise RuntimeError("model text did not parse to a JSON object")
    return assessment, payload.get("model") or MODEL_FALLBACK, latency_ms


# -- transport (b): DEV helper subprocess (guardrail lives there) -------

def _generate_via_helper(product, image_path, timestamp, correction=None):
    if correction:
        # The helper's fixed CLI (spark_call.py assess) takes only
        # --product/--image/--timestamp: there is no channel for the
        # correction text on this transport. The retry still happens
        # (a counted second call through the helper's own guardrail);
        # it re-sends the standard prompt. The correction text itself
        # reaches the model only on the direct transport above.
        print("spark_gen: correction retry on the DEV helper transport "
              "re-sends the standard prompt (helper CLI has no "
              "correction channel)", file=sys.stderr)
    env = dict(os.environ)
    env["PYTHONPATH"] = "/opt/muse/skills/custom-connector-setup/bin"
    p = subprocess.run(
        [sys.executable, SPARK_CALL, "assess", "--product", product,
         "--image", image_path, "--timestamp", timestamp],
        capture_output=True, text=True, timeout=300, env=env)
    if p.returncode != 0:
        raise RuntimeError(
            f"spark_call exited {p.returncode}: "
            f"{(p.stderr or p.stdout).strip()[-300:]}")
    wrapper = json.loads(p.stdout)
    if not wrapper.get("ok"):
        raise RuntimeError(f"spark_call not ok: {p.stdout[:300]}")
    assessment = json.loads(unwrap_model_text(wrapper.get("raw_model_text")))
    if not isinstance(assessment, dict):
        raise RuntimeError("model text did not parse to a JSON object")
    return (assessment, wrapper.get("model_returned") or MODEL_FALLBACK,
            wrapper.get("latency_ms"))


# -- entry point ----------------------------------------------------------

def generate(product, image_path, timestamp, correction=None):
    """(assessment, model, latency_ms) for one frame. Raises on any
    failure; never fabricates an assessment. `correction`, when
    given, is the bounded self-correction text (the validateAssessment
    errors a previous reply failed); each call — first or retry —
    passes through the active transport's guardrail and is counted."""
    if via_helper():
        return _generate_via_helper(product, image_path, timestamp,
                                    correction)
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    if image_bytes[0:2] != b"\xff\xd8":
        raise RuntimeError("image is not a JPEG (magic bytes missing)")
    return _generate_direct(product, image_bytes, timestamp, correction)
