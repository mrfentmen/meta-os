# BOLO interactive plan (boss's order 2026-11-01)

Status: PLANNED, not built. Sequencing per the boss: OS work first,
this is a program build that follows. Lanes when it starts: Hana
(surfaces) + the queue evidence code, Milo gate-1, Pax merge.

## What exists today (verified 2026-11-01)

- On main, `server/queue/evidence.py` builds the BOLO block the
  moment an incident is flagged and recorded: division, category,
  camera, area, description, visible marks. Exact key set pinned
  by a test. ID is always UNIDENTIFIED; no name ever.
- Hana's BOLO card (HN-061, branch hana/surfaces) renders that
  block exactly as recorded.
- The live flag path has never fired on a real feed, so the full
  moment (flag lands, card appears) is unproven. This plan is
  what turns it into a real, tested moment.

## Part A — the full dispatcher description

Extend the BOLO with an observed-descriptor block, the fields a
real dispatcher description carries. Every field comes from the
review step's observation of the actual frames. Nothing is
invented to fill a field.

- approximate age (a range, labelled an estimate)
- height (a range, labelled an estimate, judged against fixed
  objects in frame where any exist)
- build and weight class (estimate)
- apparent race or ethnicity descriptor, visible appearance only
- hair (colour, length, style as visible)
- clothing: top, bottom, footwear, colours and patterns
- carried items (bag, tool, object in hand)
- visible marks (already built: tattoos, scars, glasses, etc.)
- direction of travel and last seen camera

Rules for the block:

- NOT DETERMINABLE is a first class value on every field and is
  the required answer when the footage does not clearly show it.
  A guessed descriptor is a failed eval, same as a wrong category.
- Estimates stay ranges, never a single exact number.
- The descriptor instruction lands in BOTH mirrored prompt
  builders (the app model builder and spark_gen.py) in the same
  change, like every prompt change.
- The pinned BOLO key set grows by the new keys in the same
  commit that updates the pinning test. No silent key drift.
- requires_human_review stays true on every assessment.

## Part B — following the person

- An active red BOLO pins its card to the incident's camera on
  the wall. When the investigation step places the person on a
  neighbouring camera, the card's feed follows (the
  nearest-camera handoff work is the starting point; evaluate
  the existing branch before writing new code).
- Every new sighting appends to the incident timeline (the
  records timeline from HN-062 is the surface) with time, camera,
  and what changed in the descriptor block.
- The map pin follows the latest sighting.

## Part C — the card is interactive

- Click the card: evidence crops, the full descriptor block, the
  timeline, and the dispatch receipt, in one place.
- The card updates live as records append; no reload.
- Red tier gets the full following card. Yellow tier gets a
  static recorded card only (no following, no dispatch — the
  tier rules do not change).
- A false-positive close purges the crops and closes the card,
  under the existing purge rule.

## Part D — proof before it is claimed

- Batch eval frames get descriptor scoring alongside category
  scoring: per field, correct / wrong / not determinable used
  correctly. Our own adjudication, our own numbers, same rule
  as categories.
- The end to end moment is proven on a staged, labelled test
  feed: flag lands, card appears, follows across two cameras,
  timeline grows. Recorded once, kept as the proof.

## Hard lines that do not move

- ID: UNIDENTIFIED, always. The system describes a person; it
  never names one. No face templates, no identification.
- Dispatch stays SIMULATED and labelled, to the simulated
  endpoint only.
- Descriptors are observations of visible appearance. They are
  never a conclusion about who someone is.
