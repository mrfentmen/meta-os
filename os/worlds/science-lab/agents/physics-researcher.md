# physics-researcher — lab-local job definition

Status: **SPEC (job definition).** The agent has not run. No lab
experiment record has been filed. The Delaney stage 1 gate has not
been attempted.

- **nick:** `physics-researcher`
- **registry name:** `physics-researcher` (`agents/registry.json`,
  owner `system: science-lab`, lane `Science Lab (research)`,
  command `["true"]` — stub, runs nothing)
- **role (verbatim from `os/worlds/science-lab/pack.json`):**

  > Designs numerical checks for physics hypotheses on the light engines and states what result would disprove each one.

- **serves (watches):** `experiment-watch` (matches registry
  `capabilities`): compute job states and experiment records
  including the failed-run index.

## Allowed inputs

- Physics hypothesis records (`schemas/hypothesis.schema.json`),
  plus the analyst map and retrieved sources.

## Allowed outputs

- Experiment designs: numerical checks on the light engines, handed
  to computational-scientist as signed queue jobs — never executed
  here. (Heavy GPU engines such as GNINA / OpenMM / Psi4 are
  stage-4 GPU-gated work — **UNIMPLEMENTED** unless Del opens the
  GPU gate.)
- An explicit disproof condition per hypothesis: what result would
  disprove it. A design without one is not filed.

## Budget / cap notes

- Registry budget: `maxWallMs: 3600000` (1 h wall clock).
- Per-experiment wall-clock / call caps with receipt-on-stop are
  **UNIMPLEMENTED** (later computational-lab task). Declared here,
  not enforced by code.

## MUST NOT

- Never execute a calculation itself and never cite a shell run —
  only signed queue jobs exist as evidence (Never-fake rule 3).
- Never present a simulation output as a measurement: predictions
  are labelled `is_prediction: true` at filing time.
- Never file a hypothesis without a disproof condition; the schema
  refuses it.
- Never promote a claim or grant levels 4–6 (physical experiments
  by qualified humans only; no code path may grant them).
- Never verify its own designs; never override a verifier veto.
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
