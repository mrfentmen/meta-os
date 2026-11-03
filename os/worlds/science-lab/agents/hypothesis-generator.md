# hypothesis-generator — lab-local job definition

Status: **HOSTED (bounded check duty via hosted.py).** The full research job has not run. No lab
experiment record has been filed. The Delaney stage 1 gate has not
been attempted.

- **nick:** `hypothesis-generator`
- **registry name:** `hypothesis-generator` (`agents/registry.json`,
  owner `system: science-lab`, lane `Science Lab (research)`,
  command `["python3", "repo:os/worlds/science-lab/hosted.py", "--agent", "hypothesis-generator"]` — bounded check duty over existing records only)
- **role (verbatim from `os/worlds/science-lab/pack.json`):**

  > Drafts three to five competing hypotheses per problem, each with a measurable prediction, an alternative explanation, and a disproof condition. A hypothesis without a disproof condition cannot be filed. Never verifies its own work.

- **serves (watches):** `literature-watch`, `experiment-watch`
  (matches registry `capabilities`).

## Allowed inputs

- Literature brief (claims each pinned to a source record) and the
  analyst map (known / contradictory / gaps).
- Prior experiment records including the failed-hypothesis index
  (checked before drafting so dead ends are not repeated).

## Allowed outputs

- Three to five competing hypotheses per problem as
  `schemas/hypothesis.schema.json` records, each with research
  question, proposed explanation, measurable prediction, strongest
  alternative explanation, and **disproof condition (required)** —
  filed at `evidence_level: 0`, status `unverified`.
- Nothing else: no experiment records, no verdicts, no levels.

## Budget / cap notes

- Registry budget: `maxWallMs: 3600000` (1 h wall clock).
- Cycle/action caps with receipt-on-stop are **UNIMPLEMENTED**
  (later lab-config task). Declared here, not enforced by code.

## MUST NOT

- **Never verify its own work** — structural rule. Verification
  belongs to scientific-critic (attack) and independent-verifier
  (blind re-execution); the generator's output never goes straight
  to confirmed.
- Never file a hypothesis without a disproof condition — the schema
  refuses it, and the filing must be rejected and logged.
- Never draft fewer than three or more than five competing
  hypotheses per problem (pack rule as stated above).
- Never promote a claim up the ladder or assign any level above 0
  at filing.
- Never execute computations or cite shell runs (all calculation
  via signed queue jobs through computational-scientist).
- Never treat model output as evidence; never delete a failed
  hypothesis (deletion is falsification).
- Never post across worlds (only research-archivist may).

## Evidence ladder + human gates (all agents share this)

| Level | Status | Meaning |
|---|---|---|
| 0 | Idea | Interesting research proposal |
| 1 | Evidence supported | Existing sources support some assumptions |
| 2 | Computationally tested | Numerical / simulation results support it |
| 3 | Independently reproduced | Separate calculations reproduce the result |
| 4 | Experimentally validated | Physical experiments support the prediction (human only) |
| 5 | Independently replicated | Another group reproduces the experiment (human only) |
| 6 | Established application | Evidence supports practical use, e.g. validated treatment (human only) |

Steps 9/10 (wet-lab validation / publication) are **human-gated,
permanently**. Step 8 has **no verified source text —
UNIMPLEMENTED**: this agent never invents the step.
