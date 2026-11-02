# MODEL INTEGRATION — every Meta model, every program

Del's order 2026-11-02: a 3+ model pipeline, SAM 3.1 and the
multimodal Muse models integrated into all programs. This file is
the map: what the account actually serves (verified, not assumed),
which surface each model answers on, and where each one plugs into
the platform. Statuses use the house labels: VERIFIED (ran it),
CODE-INSPECTED (read it), UNIMPLEMENTED (not built yet).

## The account, probed live 2026-11-02 (Pax)

GET https://api.meta.ai/v1/models with the project's own key
returned nine ids: muse-spark-1.3, muse-spark-1.3-contributor,
muse-spark-1.2, muse-spark-1.2-contributor, muse-spark-1.1,
muse-wonder-1.0, sam-3.1, muse-image-1.0,
muse-voice-transcribe-1.0.

Call surfaces, each proven with a real call the same morning:

| Model | Surface | Proof |
|---|---|---|
| muse-spark-1.3 | POST /v1/chat/completions | in production since 2026-10-30 (assess) |
| muse-wonder-1.0 | POST /v1/chat/completions | probe reply "WONDEROK", usage returned, ~2s |
| sam-3.1 | POST /v1/responses | chat surface refuses it ("Use /v1/responses"); Responses call returned a box + encoded mask for a real eval frame |
| muse-image-1.0 | POST /v1/responses | chat surface refuses it ("image models are only supported on the /v1/responses API"); Responses call returned an image_generation_call with a 52,216-char base64 result |
| muse-voice-transcribe-1.0 | NOT RESOLVED | /v1/audio/transcriptions -> 404; Responses and chat with input audio -> model_not_found. Listed is not callable-yet; see the voice seam below. |

SAM 3.1's output format (from the live call, frame ignis-fire-1):
`<|box;x1=8;y1=0;x2=599;y2=354;w=600;h=470|><|mask;x=0;y=0;data=...|>`
— a pixel box on the image's own size, plus an encoded mask. The
client converts the box to the platform's 0-1000 region scale.

## The client: server/queue/models.py (on main, 2026-11-02)

One module for every model call, following spark_gen.py's
production pattern: SPARK_API_KEY from the environment only, every
call through spark_guardrail (the $75 hard stop), redirects
refused, and one JSON receipt line per call (model, surface,
usage, latency; a dollar estimate only for Muse Spark, the one
model with a published rate card — other receipts carry raw usage
with est_cost_usd null).

- `chat_text(model, prompt)` — Spark and Wonder. VERIFIED (unit
  tests + the live probes above).
- `segment(image_bytes, prompt)` — SAM 3.1; `parse_sam_text`
  extracts box/mask/region and raises rather than inventing a
  region when no box comes back. VERIFIED: unit tests plus a parse
  of the real captured SAM output (box 8,0-599,354 on 600x470 ->
  region x13 y0 w985 h753, 64,798-char mask extracted).
- `generate_image(prompt)` — Muse Image; decodes the base64
  result, detects png/jpeg/webp by magic bytes, raises rather
  than returning a placeholder. CODE-INSPECTED + live shape
  VERIFIED by probe; the repo-side function is unit-tested at the
  parser level only.
- `transcribe(audio_bytes)` — raises EndpointUnresolvedError.
  UNIMPLEMENTED until a working surface is verified; the function
  exists so callers wire to the seam, never to a guess.

Tests: tests/queue-python/test_models.py (9) — full queue suite
141/141 green on the merged tree (was 128).

## The Imperium pipeline — now four model stages

1. PATROL — Muse Spark 1.3 vision assessment (production).
2. SEGMENT — SAM 3.1 cuts the flagged subject out of the frame;
   its box replaces the reading's guessed region with a measured
   one. Client built (above); wiring into the patrol step is the
   next queue item.
3. REVIEW — independent second reading. Today Spark again; the
   multimodal second reader is Muse Wonder, one config change
   away now that chat_text takes the model id (crew.assess still
   routes through spark_gen; swapping the review call to Wonder
   is a named follow-up, not yet done).
4. JUDGE — v2 WIRED 2026-11-02: judge.rule_with_model makes the
   judge's own prompted Muse Spark call over both readings
   (build_judge_prompt + fail-safe parse_verdict). crew.py uses it
   when TRIO_JUDGE_MODEL=1; the deterministic combine() remains
   the default and the named fallback, and the timeline records
   judge_mode either way. VERIFIED end to end in the sandbox: a
   live judge call through the vault helper returned
   "confirm / visible flame" with reasons, parsed clean
   (est $0.0047). The two readings in that smoke were staged
   dicts; the call, the prompt, and the verdict were real.
   Tests: tests/queue-python/test_judge_model.py (6).

## Per-program integration

- **Imperium (Vigiles / Ignis / Medicus)** — the pipeline above.
  Spark live; SAM client built, patrol wiring next; Wonder review
  swap next; judge v2 wired behind its flag.
- **Science Lab** — director/analyst/critic/verifier are separate
  model calls by design (LABORATORY): Spark reasons, Wonder reads
  figures and plates multimodally, SAM segments specimen and
  molecule imagery. OpenCode 2's execution lane builds the real
  cycles; models.py is the transport they call.
- **Officina** — Spark writes the brief and checks the spec;
  Muse Image renders a concept image for the blueprint pack,
  labelled GENERATED wherever it appears (it is a concept, never
  a measurement).
- **Musica** — Spark studio agent; Muse Image cover art for
  pieces, labelled generated.
- **Meta Aegis / Meta Nervus** — text-reasoning lanes: Spark over
  findings (Aegis) and over neuron maps and sweep records
  (Nervus). No vision stage claimed for either.
- **Hands-Free** — Muse Voice Transcribe is the input stage by
  design; its call surface is unresolved (above), so Hands-Free
  stays text-first until the surface is verified. Nothing about
  the parked demo-voice lane changes.
- **Face / OS agents** — Spark endpoint, as settled (the brain
  sits behind one endpoint; the seat is swappable).

## Open weights — the other half of the judging line

Eligibility is meaningful use of the Meta Model API AND/OR the
open-weight models. The API half is what this file covers. The
open-weight half stays exactly where Del left it: Muse Glimmer
is the packable class (~20GB tier), Muse Spark Open (~493GB at
4-bit) is not packable on this hardware, Del applied for a
Baseten key for hosted Spark Open on 2026-11-01 (outcome not yet
known), and the local pack is designed, NOT built — Del's order:
endpoint only for now. Nothing in this integration changes that.

## Spend note

Probe + verification calls for this integration: 11 calls total.
SAM reports zero tokens (it counts images_processed); the image
call used 9,933 tokens, 7,936 of them cached; the judge smoke
estimated $0.0047 at Spark rates. The helper's cumulative
estimated test spend after the judge smoke: $1.64 of the $75
guardrail.
