# R12-040 — the voice seam, as probed

**Status: BLOCKED — the transcription endpoint is unresolved. No voice path exists in this
tree, and nothing below is a guess about what the endpoint will accept.**

## Facts, with the file that holds them

| Fact | Where it was recorded |
|---|---|
| `muse-voice-transcribe-1.0` is listed by `GET /v1/models` | `server/queue/models.py:16-21`, `os-build/MODEL_INTEGRATION.md:16` |
| `POST /v1/audio/transcriptions` returned **404** | `os-build/MODEL_INTEGRATION.md:26` |
| Responses and chat with input audio returned **model_not_found** | same line |
| The call surface is therefore **NOT RESOLVED**, not merely unimplemented | `os-build/MODEL_INTEGRATION.md:26` |
| The code refuses rather than inventing one: `transcribe()` raises `EndpointUnresolvedError` | `server/queue/models.py:268-276` |
| A test holds that refusal: `test_transcribe_raises_until_surface_verified` | `tests/queue-python/test_models.py:85-87` |

Probe date recorded in the tree: **2026-11-02**. The probe was against the live model list and
the live audio route, not against a documentation page.

## What the seam still needs

1. A verified call surface for `muse-voice-transcribe-1.0` — method, path, request shape, audio
   format, and response shape, each confirmed by a real call that returns a transcript.
2. One repo-owned audio sample small enough to keep the probe cheap and repeatable.
3. A recorded transcript for that sample, so the next run can be compared rather than trusted.

Until all three exist, the voice layer may only do what `handsfree/voice.mjs` does today:
produce the text a voice layer would say, from records. There is no microphone, no wake word,
no synthesis, and no transcription in this tree.

## What would make this record wrong

A real successful transcription call. On that day this file is replaced (not edited around):
the route, the request, the sample, the transcript, and the date. Until then, any claim that
Meta OS "takes voice" is false.
