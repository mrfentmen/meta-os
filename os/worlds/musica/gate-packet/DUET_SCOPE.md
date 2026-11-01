# Duet mode scoping (HN-044)

Status: **SCOPING ONLY, NOT BUILT.** No duet code exists in this
lane. This document states what duet mode would be, so a future
build starts from a written scope instead of a guess.

## Idea

Two composition loops run side by side and critique each other's
takes. Loop A composes from its brief; loop B grades A's takes;
loop B composes from its brief; loop A grades B's takes. Each
loop hears the other's keepers and may answer them in its next
session (same brief family, different seed line).

## The never-grade-your-own-work rule

A take is NEVER graded by the loop that composed it. Grading
means the keeper pass (keepers.py) plus the variation pass
(similarity.py) of the OTHER loop, applied to the take's audio
and log entry. Self-grading would let a loop approve its own
output and hide its own repetition; the rule exists to stop that.

Applied concretely:

- Loop A's takes are judged only by loop B's keeper thresholds
  and variation threshold, and vice versa.
- A loop's own keeper verdict on its own take is advisory only
  and is never written to the shared take log as the verdict.
- The grading loop's verdict and reason are the ones recorded,
  with the grader's id on the record.
- If the two loops disagree (composer's advisory keeper, grader's
  reject), the disagreement itself is logged as a duet event, not
  resolved by either loop alone.

## What would need building

- A duet session record: two session ids, the grader mapping,
  and the disagreement log.
- A transport between loops: today each loop writes its own
  session dir; duet needs one loop to read the other's take log
  and audio (replay from the log covers the audio side).
- A tie-break: when the loops disagree, a human verdict from
  the A/B harness (HN-039) is the only tie-break, not a third
  loop vote.
- Separate keeper thresholds per loop are allowed (different
  taste), but both loops' thresholds must be stated in the duet
  record before the session starts.

## Explicitly out of scope

- No automatic remixing of the other loop's audio.
- No shared seed lines (each loop keeps its own seeds, so
  provenance stays clean).
- No live model grading: duet grading is the keeper/variation
  code, not a model opinion, until Spark assist is live on the
  Mac path and its own guardrail covers it.

## Open questions (not decided here)

- Should duet sessions share one take log or two linked logs?
- How long may a grading loop take before the composer moves on?
- Does the audience (board v2) show duet disagreements, or only
  final verdicts?
