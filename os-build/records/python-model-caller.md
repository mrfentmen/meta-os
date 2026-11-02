# Python model caller — behaviour record (B239)

Module: `server/queue/spark_gen.py`. Read 2026-11-02. Every claim cites
the file and line range it comes from.

## What it does

The resident agent's one generation door, two transports chosen at call
time (`spark_gen.py:1-36`):

- Production (default): direct POST to
  `https://api.meta.ai/v1/chat/completions`, model `muse-spark-1.3`,
  with `SPARK_API_KEY` read from the environment only
  (`spark_gen.py:47-51`, `163-214`).
- Dev only: `TRIO_SPARK_VIA_HELPER=1` delegates to an out-of-repo
  helper script (`spark_gen.py:216-255`).

`generate()` returns `(assessment, model_reported, latency_ms)` and
raises on every failure; it never fabricates an assessment
(`spark_gen.py:257-270`).

## Inputs

- `product`, `timestamp` — prompt identity (`spark_gen.py:93-161`).
- `image_path` — a JPEG file (`spark_gen.py:257-270`).
- `correction` — optional list of contract errors from a failed reply
  (`spark_gen.py:93-161`, `212-218`).
- Environment: `SPARK_API_KEY`, `TRIO_SPARK_VIA_HELPER`
  (`spark_gen.py:54-57`, `164-169`).
- Product profiles and categories from `js/products.js` through
  `trio_repo.product_profile` (`spark_gen.py:96-98`).

## Outputs

- `unwrap_model_text(text)` → a JSON-looking string, tolerating a fence
  and surrounding prose (`spark_gen.py:60-76`).
- `_message_content(data)` → the reply text, joining text parts of a
  content list; `None` when the shape is missing
  (`spark_gen.py:78-91`).
- `build_prompt(...)` → the full newline-joined prompt, including the
  exact JSON shape, the product's categories and limits, and the
  visible-marks instruction (`spark_gen.py:93-161`).
- `generate(...)` → `(assessment_dict, model_name, latency_ms)`
  (`spark_gen.py:257-270`).

## Refusals

- No `SPARK_API_KEY` and no helper opt-in → `RuntimeError` naming the
  missing transport (`spark_gen.py:164-169`).
- Guardrail refusal comes from `spark_guardrail.check()` before the
  request is built (`spark_gen.py:170`).
- A redirect is refused by a no-redirect opener
  (`spark_gen.py:196-201`).
- HTTP failure → `RuntimeError("Spark request failed with HTTP <code>")`
  (`spark_gen.py:203-205`).
- No message content, or text that is not a JSON object →
  `RuntimeError` (`spark_gen.py:208-214`).
- Helper script absent → `RuntimeError` explaining the dev-only opt-in
  (`spark_gen.py:216-225`).
- Helper exits non-zero, or answers `ok: false` → `RuntimeError`
  (`spark_gen.py:243-255`).
- A file whose first two bytes are not `\xff\xd8` is refused before any
  transport (`spark_gen.py:266-268`).

## Correction channel difference

The direct transport appends the correction text to the prompt
(`spark_gen.py:152-160`). The helper's fixed CLI has no correction
parameter, so the retry re-sends the standard prompt and writes one
stderr line saying so (`spark_gen.py:226-235`). The correction reaches
the model only on the direct route.

## Findings

- The helper path and its `PYTHONPATH` are absolute, out-of-repo paths
  (`spark_gen.py:49-50`, `236-237`); a standalone checkout cannot use
  that transport, which the module states plainly.
- `_message_content` joins only parts with `type == "text"` and a string
  `text` (`spark_gen.py:86-90`); any other part is dropped silently.
- The helper route does not apply this module's guardrail by design
  (the helper keeps its own), so the two routes do not share a spend
  counter (`spark_gen.py:20-27`).
