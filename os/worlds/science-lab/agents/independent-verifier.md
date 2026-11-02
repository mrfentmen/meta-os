# independent-verifier — lab-local job definition

Status: **SPEC (job definition).** The agent has not run. No lab
experiment record has been filed. The Delaney stage 1 gate has not
been attempted.

- **nick:** `independent-verifier`
- **registry name:** `independent-verifier` (`agents/registry.json`,
  owner `system: science-lab`, lane `Science Lab (research)`,
  command `["true"]` — stub, runs nothing)
- **role (verbatim from `os/worlds/science-lab/pack.json`):**

  > Receives the problem, data, methodology, and archived inputs - never the generator's narrative - and re-executes from scratch. The only agent that may promote a claim up the evidence ladder; its veto requeues or kills the finding and no agent may override it.

- **serves (watches):** `verification-watch` (matches registry
  `capabilities`): findings waiting on reproduction, wait ages,
  promotions and vetoes.

## Allowed inputs

- **Only:** the problem, the data, the methodology, and the
  archived inputs (hashes, seeds, parameters, software + model
  versions) from the experiment record. **Never** the generator's
  narrative, reasoning, or result.

## Allowed outputs

- Blind re-execution from the archived inputs alone, in a clean
  dir, via signed queue jobs.
- Comparison record: original vs re-execution hashes and outcomes
  — agree / disagree / indeterminate, diff stated plainly.
- Ladder promotion (the **only** agent that may): `reproduced`
  supports level 3. Or veto: `mismatch` caps the claim at level 2
  and requeues or kills the finding; a `finding-promoted` /
  `verifier-veto` alert fires (summary-only on the bus: ids, levels,
  reason class — no data, no results).

## Budget / cap notes

- Registry budget: `maxWallMs: 3600000` (1 h wall clock).
- Cycle/action caps with receipt-on-stop are **UNIMPLEMENTED**
  (later lab-config task). Declared here, not enforced by code.

## MUST NOT

- **Never receive the generator's narrative, reasoning, or result**
  — isolation is structural, and the verifying agent is never the
  agent that produced the result (enforced in code by a later
  verification task; until then, declared here).
- **Never let its veto be overridden** by any agent including the
  director; only Del can override, in writing, on the record.
- Never edit the original on disagreement — cap the level and open
  a dispute record; the original stands untouched.
- Never promote above level 3 and never grant levels 4–6 (physical
  experiments / external replication by qualified humans only; no
  code path may grant them).
- Never execute outside signed queue jobs or cite a shell run;
  never delete failures.
- Never post full records across worlds — only summary alerts via
  the archivist path (titles, levels, counts only).

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
UNIMPLEMENTED**: this agent parks rather than inventing the step.
