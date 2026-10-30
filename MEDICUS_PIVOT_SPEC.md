# Medicus pivot spec — APPROVED by Del's tap 2026-10-29 23:55 EDT, posted to crew room 1 (bus list 400)

Del's idea: replace Meta Sanitas with an EMS product so the Trio is the
three services that answer 911 — police (Vigiles), fire (Ignis), EMS
(Medicus). Name settled by his tap: Medicus (over Mederi).

## Why the swap is cheap (CODE-INSPECTED 2026-10-29)

Products are config data, not code branches. Verified in
`native/Sources/MetaTrio/Models/ProductConfig.swift`: one config block per
product (name, department, tagline, accent color, categories, scenarios,
limitations, input guidance); the shared pipeline never branches on
product identity. Milo's Sanitas eval harness is already the shared metric
core the other lanes import. Contacts panel, DETAIL/session stats, theme
tokens are product-agnostic. Only Sanitas-specific fixtures, seeds, and
copy die.

## The one hard rule

"Medical advice" is on the hackathon avoid list. Medicus must be SCENE
awareness for EMS crews — visible scene conditions only, same law as the
other two products. No diagnosis, no cause guesses, no severity or triage
calls, no treatment recommendations, anywhere: categories, prompts, UI
copy, demo script, submission copy.

## Medicus config (draft)

- Product key: `medicus`
- Display name: Meta Medicus
- Department: FDNY EMS-oriented — medical incident scene awareness
- Tagline: Visible scene indicators for EMS crews, for human review.
- Accent color: green (carries over from Sanitas — zero theme rework)
- Categories (visible scene only):
  - person on ground
  - crowd gathered around a person
  - vehicle collision scene
  - blocked crew access
  - person motionless
  - normal activity
  - indeterminate
- Scenarios (eval + demo):
  - Person down on a sidewalk (staged or prerecorded)
  - Crowd gathered around a person on the ground
  - Vehicle collision aftermath scene
  - Blocked access: stretcher/crew path obstructed
  - Look-alikes: person sleeping on a bench, sunbathing on grass,
    yoga/stretching, sitting on a curb resting, CPR training manikin
  - Poor visibility or ambiguous conditions
- Limitations (always on screen): "Scene awareness only. It does not
  diagnose any condition, guess a cause, assess severity, or recommend
  treatment. A person who appears motionless may simply be resting. No
  automatic dispatch. Every assessment requires human verification."
- Input guidance: prerecorded footage or staged scenes with consenting
  participants only. Never a real emergency.

## Rebuild checklist (Milo's lane, est. one working day)

1. ProductID sanitas → medicus: native enum, web config, server prompt
   profile, contract tests. (Contract key changes; no other product's
   key moves.)
2. Config block swap per above.
3. Eval harness: keep the shared metric core; replace scenario fixtures
   with the Medicus set including the look-alike class. Same pass bar as
   Sanitas had.
4. Contacts seeds → EMS roles (duty officer, EMS supervisor), SAMPLE
   labeled, human-initiated only.
5. Theme: green stays; rename labels only.
6. Demo footage: public clips, corner/overhead angle per Del's standing
   ruling — person-down, crowd-around-person, collision aftermath;
   look-alikes: bench sleeper, park yoga, sunbather.
7. Copy sweep: README, submission copy, trio pitch → "the three services
   that answer 911: police, fire, EMS."

## Not changed

- Vigiles and Ignis lanes untouched.
- Spark stays held until Del green-lights the test phase.
- No-fake rule, v2 contract, human-review law: unchanged.
- Sanitas code stays in git history; nothing is lost if this reverses.
