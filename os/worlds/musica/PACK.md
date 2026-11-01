# Meta Musica world pack: the studio that never closes

Status: **PARTIAL.** The loop, keeper bar, variation check,
catalogue, rights log, normalisation, studio board, failure
museum, prompt library, listening harness, and overnight pipeline
are built and run on real sessions (see Proven below). Spark
assisted composition is NOT live (builders only, no key, no calls
from this sandbox), duet mode is scoping only, and the board
pages are static HTML whose audio playback is not yet verified in
a browser. This document's status moves only as fast as that
evidence.

## Purpose

A studio that never closes still needs taste it can prove. This
pack defines the agent crew that gives it taste: a loop that
renders real audio takes from written genre briefs, a log that
records every attempt with its prompt, seed, duration, verdict,
and reason, a keeper bar written as code so a take passes or
fails measurably, and a catalogue that exports keepers with a
licence and provenance line per track. Nothing enters the
catalogue without a rights line. Nothing is presented as a real
take unless it was rendered and logged.

The pack composes and records. It never claims a human
performance, never presents a mocked file as a real take, and
never moves money or rights it does not hold.

## What it watches

- **Take log.** Every composition attempt recorded with prompt,
  seed and parameters, duration, verdict, and reason, in order,
  so no take is ever lost or invented after the fact.
- **Keeper gate.** Length, loudness, silence ratio, and
  repetition measured per take, so a take passes or fails
  measurably and the reason is on the record.
- **Catalogue.** Keepers exported with a licence and provenance
  line per track, refusing any track whose rights line is empty.

## Agent roster

| Agent | Job |
|---|---|
| loop-composer | Renders one take per seed from a genre brief, measures it, and appends it to the take log. |
| keeper | Applies the keeper rules as code to every take and records the verdict and reason. |
| cataloguer | Exports keepers as the catalogue with licence and provenance per track; refuses tracks with no rights line. |

## Alerts (shared wire format)

- **take-rejected** (warning, local): take id, session id, and
  the keeper-rule reason it failed. Reasons only, no audio.
- **keeper-published** (warning, summary, crosses the bus):
  session id, keeper count, and catalogue titles. Counts and
  titles only — never audio bytes, unreleased takes, or seeds.
- **session-stalled** (warning, local): session id and how long
  the loop has produced no new take. State only.

## Proven / unproven (updated at HN-045)

Proven:

- Pack manifest validates green (HN-026) and the registry lists
  it (HN-026, updated here to PARTIAL).
- The loop renders real deterministic audio: hn029 (12 takes),
  three brief sessions (4 takes each), and overnight-001 (100
  takes, 85 keepers, 15 rejects, 0 clones, 76.6 s).
- The keeper bar measures and discriminates: length, loudness,
  silence, bar-fingerprint repetition, thresholds from real takes.
- The variation check is calibrated: distinct-seed keepers score
  at most 0.9242, a gain-changed clone 0.9997, threshold 0.98.
- The catalogue exports keepers with licence + provenance; the
  rights log passes hn029 11/11 and rejects empty rights lines.
- Catalogue tracks normalise to -16 LUFS, before/after measured
  per track, all hn029 tracks within tolerance.
- The studio board (v1 session board, v2 studio-wide browser),
  failure museum, and prompt library all read records only.
- The A/B harness is blind by construction (anonymised files)
  and records picks as human verdicts in the take log.
- Session persistence is proven by live kill + resume with no
  lost takes and contiguous ids.
- Spark assist builders (structure/lyric) follow the repo
  contract; every attempt is recorded; no live call is made
  from this sandbox.

Unproven:

- Spark-assisted composition live: builders only, no key here,
  no calls sent, no model reply ever recorded as sent.
- Board audio playback in a real browser (no browser in this
  sandbox; the pages are static HTML).
- A Swift mirror musica case (noted at HN-027, not built;
  the Trio Swift mirror is unaffected).
- Duet mode (HN-044 scoping only, no code).
- Catalogue audio for sessions after hn029 is reproducible from
  the log, not committed (repo-lean policy, sessions README).
