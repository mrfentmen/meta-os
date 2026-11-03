# OC2B-416 transcribe surface record

Re-ran the documented probe set once each (2026-11-02, this Mac).
No new surfaces guessed.

- `POST /v1/audio/transcriptions` → `HTTPError: HTTP Error 404:
  Not Found` (matches MODEL_INTEGRATION.md).
- `POST /v1/chat/completions` with `muse-voice-transcribe-1.0` +
  audio input → `HTTPError: HTTP Error 404: Not Found` (was
  `model_not_found` in Pax's probe; the failure mode moved but the
  verdict is identical: no callable surface).
- `POST /v1/responses` with `muse-voice-transcribe-1.0` + audio
  input → `HTTPError: HTTP Error 404: Not Found` (same note as
  above).
- `models.transcribe(b"ID3")` → `EndpointUnresolvedError:
  muse-voice-transcribe-1.0: no verified call surface yet ...`
  (the seam raises instead of guessing, as designed).

Verdict: MATCHES MODEL_INTEGRATION.md's account — voice remains
listed-but-not-callable; Hands-Free stays text-first. No edit made to
that file. Proposed text for Pax's follow-up (one line):

> 2026-11-02 Mac re-probe: chat and Responses audio inputs now 404
> (were model_not_found); /v1/audio/transcriptions still 404;
> transcribe() still raises EndpointUnresolvedError by design.
