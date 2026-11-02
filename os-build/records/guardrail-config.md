# crates/guardrail — config surface (B164)

The crate is a library: no CLI flags, no config file of its own. What it
reads comes from the caller and, in one place, the environment.

## Environment variables read by the crate

| Variable | Read at | Meaning | Default | When wrong |
|---|---|---|---|---|
| `TRIO_SPARK_VIA_HELPER` | `lib.rs:162-164` (`via_helper`) | `"1"` selects the DEV helper transport; any other value (including `"true"`, `"0"`, unset) means the direct transport | unset (direct) | No refusal: a typo silently selects the direct transport, which then needs `SPARK_API_KEY` (that refusal lives in `spark_gen.py:164-168`, not here) |

No other environment variable is read by `crates/guardrail`.

## Environment variables read by the caller (the practical config)

These are not crate inputs, but they decide how the crate is used:

| Variable | Caller | Meaning | Default | Wrong-value behaviour |
|---|---|---|---|---|
| `SPARK_GUARDRAIL_STATE` | `crates/assess-server/src/main.rs:524-525` | ledger path passed to `load_state`/`record` | `spark_guardrail_state.json` | Any path is accepted. A missing/unreadable/corrupt file reads as a zero ledger (gap G1), not a refusal |
| `SPARK_API_KEY` | `server/queue/spark_gen.py:163-168` | direct-transport key | none | Raises "no generation transport is configured" before guardrail or network |
| `TRIO_SPARK_VIA_HELPER` | `server/queue/spark_gen.py:57-58` | transport switch (same literal rule) | unset | Falls back to direct transport |

## Files

| File | Direction | Shape | Notes |
|---|---|---|---|
| ledger path supplied by the caller | read (`load_state`, 57-62) and written (`save_state`, 64-68) | `GuardrailState` JSON, pretty-printed | no default path in the crate; the file is runtime state, never committed (`OPENCODE_MAC_PROMPT.md:48-51`) |

## Constants (not configurable)

| Constant | Value | Source | Consequence if edited |
|---|---:|---|---|
| `TEST_BUDGET_USD` | 75.0 | `lib.rs:13` | the hard stop moves; Python and Node keep 75.0 until changed in all three |
| `RATE_IN_PER_M` | 1.25 | `lib.rs:14` | estimates drift from the published card |
| `RATE_OUT_PER_M` | 4.25 | `lib.rs:15` | same |
| `SPARK_ENDPOINT` | `https://api.meta.ai/v1/chat/completions` | `lib.rs:16` | wrong host; endpoint is redirect-refusing in the Python transport |
| `SPARK_MODEL` | `muse-spark-1.3` | `lib.rs:17` | prompt and request body name a different model |

## Refusals that depend on config

- Ledger path unset: the crate cannot choose one; the caller must pass
  a path. No panic, no default.
- Ledger unreadable/malformed: **no refusal** — zero state (finding 1).
- Budget reached: the only refusal, exact text at `lib.rs:71-76`.
