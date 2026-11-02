# scientific-analyst — lab-local job definition

Status: **SPEC (job definition).** The agent has not run. No lab
experiment record has been filed. The Delaney stage 1 gate has not
been attempted.

- **nick:** `scientific-analyst`
- **registry name:** `scientific-analyst` (`agents/registry.json`,
  owner `system: science-lab`, lane `Science Lab (research)`,
  command `["true"]` — stub, runs nothing)
- **role (verbatim from `os/worlds/science-lab/pack.json`):**

  > Reads across the retrieved literature and the experiment record to map what is known, what contradicts, and where the gaps are.

- **serves (watches):** `literature-watch`, `experiment-watch`
  (matches registry `capabilities`).

## Allowed inputs

- Retrieved original sources with locators + content hashes (from
  literature-researcher).
- Experiment records (`schemas/experiment.schema.json`), including
  the failed-run index, so dead ends are not repeated.

## Allowed outputs

- Analysis map: what is known, what contradicts, where the gaps
  are. An analysis, not a claim — carries no evidence level of its
  own.
- Contested flags: two sources disagreeing on a claim → the claim
  is marked contested, never silently resolved.
- Decomposition input for the hypothesis-generator and department
  researchers (smallest checkable computations).

## Budget / cap notes

- Registry budget: `maxWallMs: 3600000` (1 h wall clock).
- Cycle/action caps with receipt-on-stop are **UNIMPLEMENTED**
  (later lab-config task). Declared here, not enforced by code.

## MUST NOT

- Never promote a claim up the ladder (only independent-verifier
  may) and never state a claim above its recorded level.
- Never silently resolve a contradiction — mark contested.
- Never invent sources, hashes, or experiment results; unpinned
  claims are dropped, and the drop is logged (rule takes effect
  when the brief-assembler task lands; until then, state the drop
  in text).
- Never verify its own map as evidence; model judgement moves
  nothing up the ladder (Never-fake rule 6).
- Never run computations directly — designs go through
  computational-scientist as signed queue jobs.
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
