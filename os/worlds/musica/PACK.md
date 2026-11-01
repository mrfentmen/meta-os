# Meta Musica world pack: the studio that never closes

Status: **SPEC, NOT BUILT.** This pack is a definition: a manifest
(`pack.json`, checked by `worlds/validate_pack.py`) and this
document. No runtime code in this pack composes real music yet.
The runtime lands in the later HN tasks of this lane (loop, keeper
rules, catalogue, studio board), and this document's status moves
only as fast as that evidence (HN-045 truth pass).

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

- Proven: pack manifest validates green (HN-026).
- Unproven: everything else — the loop, the keeper bar, the
  catalogue, the board, Spark assist, and the overnight run are
  all still to land in this lane.
