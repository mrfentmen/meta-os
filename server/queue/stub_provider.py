"""stub_provider.py — deterministic stub model provider for tests.

No network, ever: every function is pure computation over its inputs, so
the same (model, prompt) always yields the same text and usage. The JS
side (agents/providers.mjs stubCall) mirrors this contract; this module
gives Python tests the same deterministic seam without importing live
transports (models.py / spark_gen.py are never touched here). Live calls
bill to SPARK_API_KEY (the single model key; see agents/providers.mjs
PROVIDERS); this stub needs no key and spends nothing.

Usage shape mirrors the live receipts: prompt/completion token counts
plus a Spark-rate estimate where a published rate exists, else None
(never invented — see agents/providers.mjs estimateCost).
"""

STUB_TEXT_PREFIX = "STUB"
STUB_COMPLETION_TOKENS = 16

SPARK_RATE_IN_PER_M = 1.25
SPARK_RATE_OUT_PER_M = 4.25
SPARK_MODEL = "muse-spark-1.3"


def stub_usage(prompt):
    """Deterministic usage for a prompt string."""
    text = prompt if isinstance(prompt, str) else ""
    return {
        "prompt_tokens": max(1, (len(text) + 3) // 4),
        "completion_tokens": STUB_COMPLETION_TOKENS,
    }


def stub_text(model, prompt):
    """Deterministic reply text: same inputs, same output, always."""
    text = prompt if isinstance(prompt, str) else ""
    return "%s %s :: prompt-chars=%d :: reply-ok" % (
        STUB_TEXT_PREFIX, model, len(text))


def stub_estimate_usd(model, usage):
    """Spark-rate estimate, or None when the model has no published rate."""
    if model != SPARK_MODEL or not isinstance(usage, dict):
        return None
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    return (prompt_tokens / 1e6 * SPARK_RATE_IN_PER_M
            + completion_tokens / 1e6 * SPARK_RATE_OUT_PER_M)


def stub_chat(model, prompt):
    """(text, usage, latency_ms) — deterministic, transport always stub."""
    usage = stub_usage(prompt)
    return stub_text(model, prompt), usage, 0


def stub_receipt(model, prompt):
    """One receipt-shaped record, transport labeled stub."""
    text, usage, latency_ms = stub_chat(model, prompt)
    return {
        "kind": "stub-call",
        "model": model,
        "transport": "stub",
        "usage": usage,
        "latency_ms": latency_ms,
        "est_cost_usd": stub_estimate_usd(model, usage),
        "text": text,
    }
