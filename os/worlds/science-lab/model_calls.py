"""Science Lab model-call transport (Section 3, tasks 31-40).

One wrapper for every Meta-model call the lab makes, mirroring the
verified client in server/queue/models.py (SPARK_API_KEY from the
environment only, one guardrailed POST per call, no invented replies):

  director (Muse Spark, chat) .... plans cycle 3's approach (task 31)
  figure reader (Muse Wonder, chat) reads a cycle plot (task 33)
  critic (Muse Wonder, chat) ...... second-model objection (task 35)
  segment (SAM 3.1, responses) .... specimen/molecule mask (task 34)

Key rule (task list): the Mac key flakes. Each call below is tried
ONCE; any failure (bad key, network, timeout, guardrail) is logged
once in the returned receipt and the caller falls back to a
documented OFFLINE mode. Never retry-loops, never fabricates a
model reply, never prints/logs the key.

Receipts are plain JSON dicts the pack files under
labs/cycles/cycle-003/model_calls/ (task 36, Bond-verifiable).
Stdlib only.
"""

import hashlib
import json
import os
import queue
import sys
import threading
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    sys.path.insert(0, os.path.join(
        os.path.dirname(BASE_DIR), "..", "..", "server", "queue"))
    import models as _models  # noqa: E402
except Exception:  # pragma: no cover - import failure is an offline cause
    _models = None

SPARK = "muse-spark-1.3"
WONDER = "muse-wonder-1.0"
SAM = "sam-3.1"

SURFACES = {SPARK: "chat", WONDER: "chat", SAM: "responses"}


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def prompt_sha256(prompt):
    """Stable id for a prompt (saved in receipts, never the key)."""
    return hashlib.sha256(str(prompt).encode("utf-8")).hexdigest()


def offline_receipt(kind, model, prompt, error):
    """Build the documented OFFLINE receipt for one failed call."""
    return {
        "ts": _utcnow(),
        "kind": kind,
        "model": model,
        "surface": SURFACES.get(model),
        "usage": None,
        "latency_ms": None,
        "est_cost_usd": None,
        "mode": "OFFLINE",
        "prompt_sha256": prompt_sha256(prompt),
        "error": str(error)[:200],
        "note": ("OFFLINE: no live model call succeeded (tried once; "
                 "failure logged once; never retried). No model text "
                 "was produced; callers use the deterministic template "
                 "marked OFFLINE."),
    }


def live_receipt(kind, model, usage, latency_ms, prompt):
    """Build the LIVE receipt for one succeeded call."""
    est = None
    if model == SPARK and isinstance(usage, dict):
        try:
            est = float(usage.get("prompt_tokens", 0)) / 1e6 * 1.25 + \
                float(usage.get("completion_tokens", 0)) / 1e6 * 4.25
            est = round(est, 6)
        except (TypeError, ValueError):
            est = None
    return {
        "ts": _utcnow(),
        "kind": kind,
        "model": model,
        "surface": SURFACES.get(model),
        "usage": usage,
        "latency_ms": latency_ms,
        "est_cost_usd": est,
        "mode": "LIVE",
        "prompt_sha256": prompt_sha256(prompt),
        "error": None,
        "note": ("LIVE: one guardrailed call via server/queue/models.py; "
                 "reply saved verbatim."),
    }


def _run_once(fn, timeout_s):
    """Run fn() once, bounded by timeout_s. Returns (ok, value, error).

    The worker is a daemon thread: on timeout the attempt is abandoned
    (counted as the single try, never retried) without stalling exit.
    """
    if _models is None:
        return (False, None, "model transport unavailable "
                "(server/queue/models.py did not import)")
    if not os.environ.get("SPARK_API_KEY"):
        return (False, None, "SPARK_API_KEY not set in the environment")
    out = queue.Queue()

    def _work():
        try:
            out.put((True, fn(), None))
        except Exception as exc:  # noqa: BLE001 - any failure is offline
            out.put((False, None, "%s: %s"
                     % (type(exc).__name__, str(exc)[:160])))

    worker = threading.Thread(target=_work, daemon=True)
    worker.start()
    try:
        return out.get(timeout=timeout_s)
    except queue.Empty:
        return (False, None,
                "timeout after %ss (tried once; abandoned, "
                "never retried)" % (timeout_s,))


def try_chat(model, prompt, max_tokens=1200, timeout_s=60):
    """One chat call (Spark or Wonder). Returns
    (mode, text_or_None, receipt). Never raises for a model failure;
    never returns a fabricated reply."""
    def _call():
        return _models.chat_text(model, prompt, max_tokens=max_tokens)

    ok, value, error = _run_once(_call, timeout_s)
    if not ok:
        return ("OFFLINE", None,
                offline_receipt("chat:%s" % model, model, prompt, error))
    text, reported, latency_ms = value
    receipt = live_receipt("chat:%s" % model, reported or model,
                           None, latency_ms, prompt)
    # models.chat_text records usage via the guardrail; the reply's
    # usage line lives in the helper receipts file when configured.
    # The pack receipt carries what the transport returned.
    return ("LIVE", text, receipt)


def try_segment(image_bytes, prompt_text, timeout_s=90):
    """One SAM 3.1 call. Returns (mode, record_or_None, receipt)."""
    def _call():
        return _models.segment(image_bytes, prompt_text)

    ok, value, error = _run_once(_call, timeout_s)
    if not ok:
        return ("OFFLINE", None,
                offline_receipt("segment:sam-3.1", SAM, prompt_text, error))
    receipt = live_receipt("segment:sam-3.1", value.get("model") or SAM,
                           {"images_processed": 1}, value.get("latency_ms"),
                           prompt_text)
    return ("LIVE", value, receipt)


# ------------------------------------------------------------------
# Deterministic OFFLINE templates (honest fallbacks, never model text)
# ------------------------------------------------------------------

OFFLINE_MARK = "OFFLINE"


def offline_director_plan(question, expected, inputs):
    """Deterministic director-plan template (task 31 fallback)."""
    return (
        "[OFFLINE director plan - NOT a Muse Spark output. No live "
        "model call succeeded; the failure is logged once in "
        "model_calls/call_log.md. The approach below is the "
        "deterministic template authored by the runner.]\n\n"
        "Question: %s\n"
        "Target: rule-of-mixtures density rho = sum(f_i * rho_i) = %s "
        "at inputs %s.\n"
        "Approach: (1) pre-register plan hash BEFORE any result; "
        "(2) run compute.run_materials once, deterministically, seed "
        "recorded; (3) score with compute.compare_to_prereg against "
        "the pre-registered band; (4) mandatory critic, answered with "
        "evidence; (5) independent clean-dir re-run must agree "
        "bit-for-bit.\n\n"
        "What the model changed about this work: NOTHING. No live "
        "call succeeded, so no model suggestion was adopted, altered, "
        "or rejected. Every step above is the runner's template."
        % (question, expected, json.dumps(inputs, sort_keys=True)))


def offline_critic_objection(target_desc):
    """Deterministic critic-objection template (task 35 fallback)."""
    return (
        "[OFFLINE critic objection - authored by the runner; NOT a "
        "Muse Wonder output. No live second-model call succeeded.]\n\n"
        "Strongest objection to %s: the rule of mixtures is an "
        "idealization - it assumes the phase densities are exact, "
        "the fractions are volume fractions that sum to exactly 1, "
        "and mixing introduces no porosity or interaction volume. "
        "A mass-fraction / volume-fraction slip, or unmodeled voids, "
        "would shift the observed density outside the tolerance band "
        "while the arithmetic still 'matches'. The MATCH verdict is "
        "therefore bounded to 'the runner evaluates the textbook "
        "formula correctly at the stated inputs' - it says nothing "
        "about any real composite coupon."
        % (target_desc,))


def offline_wonder_note(figure_name, numbers_desc):
    """Deterministic figure-reading note (task 33 fallback)."""
    return (
        "[OFFLINE figure note - UNPROVEN. No live Muse Wonder call "
        "succeeded, so no model reading exists. The numbers below "
        "are the runner's own record of what was plotted, NOT a "
        "model's reading of %s: %s. The plot file itself is archived "
        "alongside this note; its agreement with the raw outputs was "
        "checked by the runner's pixel/data comparison in "
        "figure_check.md, which remains UNPROVEN as a model reading.]"
        % (figure_name, numbers_desc))


__all__ = [
    "SPARK", "WONDER", "SAM", "SURFACES", "OFFLINE_MARK",
    "prompt_sha256", "offline_receipt", "live_receipt",
    "try_chat", "try_segment",
    "offline_director_plan", "offline_critic_objection",
    "offline_wonder_note",
]
