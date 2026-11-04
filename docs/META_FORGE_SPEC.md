# Meta Forge — application spec

Status: branch-only spec, written for Del's 21:18 EST 2026-11-03
applications ask, after Del's follow-up in room 1 the same night:
"spec out meta forge more" (Del to Hana). Nothing here is merged
to main. Nothing is forced. ISO work stays with Buffy. This spec
expands Hana's earlier one-line Forge idea: an agent designs a small
repair or part, a second agent checks it, a human confirms, then the
nearest public workshop or printer makes it for pickup.

## The idea in one sentence

You show the agent a small broken thing. The agent designs a
replacement part for that exact thing. A second agent checks the
design. You approve it. Then the nearest public workshop or library
printer that has the right machine and material makes it, and you
pick it up.

## Why it is not a search engine lookup

A search engine finds products that already exist. The part you need
usually does not exist as a product: it has no name, the maker
stopped selling it, or it only fits your exact broken thing — your
drawer knob's screw spacing, your blender's cracked coupling, the
clip that held your vacuum's hose. There is nothing to look up.
The part has to be designed from the thing in front of you, and
that is the agent-native job: look, measure, design, check.

It is also not "just buy a new one." Buying new throws the whole
thing away for one broken piece. Forge keeps the thing working.

## How it would work

1. **Show it.** You take a photo of the broken thing and the place
   it broke from. The agent guides the measurements it needs: a
   ruler in the shot, screw spacing, how thick the piece was, what
   it has to do (hold, turn, cover, join). A photo alone is never
   enough when a measurement matters — the agent asks until the
   numbers are in.
2. **Design it.** A designer agent drafts the replacement: shape,
   dimensions, material, and how it will be made (3D print, cut,
   or milled). Small parts only. The design says plainly what it
   is for and what it is not strong enough for.
3. **Check it.** A second agent reviews the design before anyone
   makes anything: do the dimensions match the measurements, is
   the material right for the job, does the part actually do what
   the broken piece did? Any failed check or any safety flag
   stops the job. The designer never checks its own work.
4. **You say go.** You see the design, the material, the price
   the workshop sets, and the pickup time. Nothing is made until
   you approve it. The app never invents a price and never orders
   on its own.
5. **The nearest capable place makes it.** The app matches a
   public workshop, makerspace, or library printer by machine and
   material and opening hours, not just by distance. A printer
   that cannot print your material is not "nearest" in any useful
   sense.
6. **Pickup and fit check.** You pick the part up and try it. If
   it does not fit, the miss is recorded — which measurement was
   off — and the design is corrected. The record of misses is
   what makes the next design better.

## How it differs from the other apps

- **Not Meta Haven (shelter beds):** Haven looks up beds that
  already exist and are already listed. Forge creates a part that
  does not exist yet anywhere.
- **Not Meta Mother Tongue (language preservation):** Mother
  Tongue records what only a person carries. Forge measures what
  only your broken thing shows.
- **Not Science Lab:** the Lab thinks through experiments. Forge
  thinks through one physical object and ends with a thing you
  can hold.
- **Not Meta Surveyor:** Surveyor measures a neighbourhood (heat,
  air, water, noise) with two agents confirming each reading.
  Forge measures one object, and its second check is a design
  review, not a second measurement.
- **Not Officina:** Officina is the workshop-side tooling Pax's
  workers are building. Forge is the user side — design and
  check — and hands the making step to workshops rather than
  duplicating workshop tooling. If Officina grows a maker-side
  handoff, Forge uses it instead of building its own.

## What it is for

Repair without expertise, and less waste. Most people cannot
design a replacement part, and most broken things are not worth
a repair shop's fee — so the thing goes in the trash. Forge
closes that gap: the agent does the skilled part (design and
check), a public workshop does the making, and the person keeps
their thing.

## Deliberately out of scope

- No safety-critical parts, ever: no brakes, no gas parts, no
  mains-electrical parts, no medical devices, no pressure
  vessels, no structural parts, no locks or keys, and nothing
  whose failure could hurt someone, flood a home, or start a
  fire. When in doubt, the checker refuses and says why.
- No weapons parts, and no copies made for resale. Personal
  repair of your own thing only — no counterfeit branded goods.
- No making without a human approval, and no payment moves
  without a human approval. The workshop sets the price; the
  app never invents one.
- No design from a photo alone when a measurement matters.
- No shipping in the first version: pickup only, from a public
  place you can walk into.

## Demo plan (next piece, still owed tonight)

Demo stills showing the shape of the app, labelled as a concept
still, not a claim that any real workshop made anything yet:
a snapped plastic knob, the design with its dimensions, the
checker pass screen, and a pickup ticket at a library printer.
Real app screens only when the app exists; until then, concept
stills say so on their face. No real person's likeness is used
without permission, and no real workshop is named without its
say-so.

## Open questions for Del / Pax

- Which broken thing should the first demo use — a drawer knob,
  a blender coupling, a vacuum clip, or something else small
  and easy to show?
- Where does the workshop list come from — real public listings
  (libraries, makerspaces) or a small supplied starter list for
  the demo?
- Should Forge stand alone, or live as the user side of
  Officina once Officina's maker-side handoff exists?
- Should the first build cover 3D printing only, or printing
  plus simple cutting from the start?
