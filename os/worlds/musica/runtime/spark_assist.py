"""musica Spark assist (HN-034).

Structure/lyric prompts built the way the repo's Spark builder
builds them (server/model.mjs buildSparkPrompt): a tight brief,
a JSON-only reply shape, and the product's limitations in the
prompt itself. Every assist attempt is recorded in the take log's
spark_assist field ({status, prompt_sha256}) -- and in this
sandbox every attempt records "held" or "not_configured" and NO
call is sent, because:

  1. Unless ASSESS_LIVE_MODEL=1 is set, the attempt is "held"
     (the same gate as server/model.mjs).
  2. With the gate open but no key, it is "not_configured"
     (SPARK_API_KEY lives in the Mac server env only, never here).
  3. The actual send path is server/model.mjs on the Mac, behind
     the shared $75 spend guardrail (server/budget.mjs). This
     module never implements the HTTP call, so it can never leak
     a key or fabricate a model reply: a "sent" record can only
     come from the Mac-side path, in the same format.

The loop records the attempt per take (compose.py --spark-assist
structure|lyrics); the prompt text itself is never stored in the
log, only its sha256.
"""

import hashlib
import os

LIMITATIONS = ("Generated material only: never reproduce copyrighted "
               "lyrics, never imitate a named artist's voice or style, "
               "never claim a human performance.")


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_structure_prompt(brief_id, brief_text, bars):
    """Prompt for a section structure for one take. Returns prompt text."""
    return "\n".join([
        "You are the structure assistant for Meta Musica, a studio "
        "that generates its own music from written briefs.",
        "Brief (%s): %s" % (brief_id, brief_text),
        "The take is %d bars. Return JSON ONLY, no prose, no markdown "
        "fences, matching this shape exactly:" % bars,
        '{"sections": [{"name": "<intro|verse|chorus|bridge|outro>", '
        '"bars": <int>}]}',
        "Rules: sections must sum to %d bars; keep it simple enough "
        "for a loop to render." % bars,
        "Limits: %s" % LIMITATIONS,
    ])


def build_lyric_prompt(theme, bars):
    """Prompt for short original lyric lines. Returns prompt text."""
    return "\n".join([
        "You are the lyric assistant for Meta Musica, a studio that "
        "generates its own music from written briefs.",
        "Theme: %s" % theme,
        "The take is %d bars. Return JSON ONLY, no prose, no markdown "
        "fences, matching this shape exactly:" % bars,
        '{"lines": ["<one short original line per section>"]}',
        "Rules: every line must be original; no quoted lyrics, no "
        "named artists, no real people's names.",
        "Limits: %s" % LIMITATIONS,
    ])


def request_assist(prompt_text, env=None):
    """Record an assist attempt. Never sends from this module.

    Returns {"status": "held"|"not_configured", "prompt_sha256": ...}.
    """
    env = os.environ if env is None else env
    if env.get("ASSESS_LIVE_MODEL") != "1":
        status = "held"
    elif not env.get("SPARK_API_KEY"):
        status = "not_configured"
    else:
        # Gate open and key present: the send still belongs to the
        # Mac-side server/model.mjs path behind the spend guardrail.
        # This module records the attempt as held rather than
        # sending from the sandbox.
        status = "held"
    return {"status": status, "prompt_sha256": _sha(prompt_text)}
