# Science Lab world pack: autonomous scientific discovery

Status: **PARTIAL.** This pack is a definition — a manifest
(`pack.json`, checked by `worlds/validate_pack.py`), the record
schemas in `schemas/`, and this document — plus one built
component: **Hortus**, the lab's breeding engine (see the Hortus
section below), which executes its own deterministic toy-model
calculations and nothing else. No runtime code in this pack runs
a laboratory, files a lab record, or makes a scientific claim.
Del ordered this pack on 2026-11-01, as the second system on Meta
OS after Imperium, from his architecture doc *Project LABORATORY:
Autonomous Scientific Discovery System*.

## Purpose

An autonomous research system will eventually claim it has
discovered cures, new physics, or groundbreaking reactions when
it has only generated a prediction, unless its honesty rules are
structural. This pack defines the agent crew for a laboratory
whose claims are capped by construction: every finding carries a
formal evidence level (0 to 6), a hypothesis cannot be filed
without a disproof condition, all calculation goes through
signed, structured compute jobs, an independent verifier
re-executes results from archived inputs before any claim rises,
and failed hypotheses and failed runs are kept as permanent
records. The laboratory works in the open, at the level its
evidence actually reached, and no higher.

## What it watches

- **Literature watch.** New papers, preprints, and datasets in
  tracked research areas, retrieved as original sources with
  DOI-level provenance. A search result is a lead, never
  evidence.
- **Experiment watch.** Compute job states and the experiment
  records they file, including the failed-run index, so the lab
  never unknowingly repeats a dead end.
- **Verification watch.** Findings waiting on independent
  reproduction, how long they have waited, and every ladder
  promotion or veto the verifier issues.

## Agent roster

The LABORATORY team is thirteen agents. Nobody gets every tool:
each agent's `serves` list in the manifest is its scope. Two
rules are structural, not polite: the hypothesis generator never
verifies its own work, and the verifier receives the problem,
data, methodology, and archived inputs — never the generator's
narrative.

| Agent | Job |
|---|---|
| research-director | Runs the discovery cycle and approves no claim above the level its record holds. Cannot override a veto. |
| literature-researcher | Retrieves original sources with locators and content hashes. |
| scientific-analyst | Maps what is known, what contradicts, and where the gaps are. |
| mathematics-researcher | Designs symbolic and numerical checks; states what would disprove each hypothesis. |
| chemistry-researcher | Designs descriptor and property calculations; states what would disprove each hypothesis. |
| biology-researcher | Designs checks against the biology sources; states what would disprove each hypothesis. |
| physics-researcher | Designs numerical checks on the light engines; states what would disprove each hypothesis. |
| hypothesis-generator | Drafts three to five competing hypotheses per problem, each with a measurable prediction, an alternative explanation, and a disproof condition. |
| computational-scientist | Turns designs into signed, schema-validated compute jobs. Has no terminal. |
| statistician | Checks error measures and tolerances on finished runs and reproductions. |
| scientific-critic | Attacks findings before verification; runs on a separate model from the generator when one is available. |
| independent-verifier | Re-executes from archived inputs. The only agent that may promote a claim up the evidence ladder; its veto is final inside the system. |
| research-archivist | Keeps the knowledge repository, failures included, permanently. The only agent that may post across worlds. |

## Record schemas

Two JSON Schemas live in `schemas/` and define the lab's records:

- `hypothesis.schema.json` — the LABORATORY section 6 record:
  research question, proposed explanation, measurable prediction,
  alternative explanation, and **disproof condition as a required
  field**. A hypothesis without one cannot be filed; the schema
  refuses it. `evidence_level` is required and starts at 0.
- `experiment.schema.json` — the LABORATORY section 8 record:
  question, hypothesis id and version, original data and source,
  software and model with versions, parameters, random seed,
  input and output hashes, execution logs, verification status,
  an `is_prediction` label set at filing time, and
  `evidence_level`. The schema caps the level structurally: no
  experiment record from this system may carry a level above 3,
  and an unverified or mismatched result is capped at 2 by the
  schema's own rules. Only a recorded independent reproduction
  supports level 3.

## The evidence ladder

From LABORATORY section 7. These levels are not interchangeable,
and every surface this pack ever produces — UI, reports, bus
posts — must use the correct level every time.

| Level | Status | What it means |
|---|---|---|
| 0 | Idea | Interesting research proposal |
| 1 | Evidence supported | Existing sources support some underlying assumptions |
| 2 | Computationally tested | Numerical or simulation results support the hypothesis |
| 3 | Independently reproduced | Separate calculations reproduce the result |
| 4 | Experimentally validated | Appropriate experiments support the prediction |
| 5 | Independently replicated | Another research group reproduces the experimental result |
| 6 | Established application | Evidence supports its practical use, such as a validated treatment |

A molecule that scores well in a docking program is not a
discovered medicine. A mathematical result that survives random
tests is not necessarily a theorem. Levels 4 and above require
physical experiments by qualified humans and are **unreachable
by this system alone**; no code path in this pack may grant
them.

## Hortus — the lab's breeding engine

Hortus is the candidate **generator** inside this lab (Del's
ruling, 2026-11-01: the evolution engine belongs inside Meta
Scientia, not beside it). It lives in `hortus/` and is the one
built component in this pack. It runs a plain genetic algorithm
— population, mutation, crossover, tournament selection — as
discrete generations, where every organism's fitness comes from
a deterministic scorer in code (an analytic toy model, labelled
as one in its own docstring), never from a language model.

The generator/verifier split is structural here too:

- **Hortus proposes.** It breeds candidates against its training
  environment and logs everything: every birth, death, and
  generation goes into an append-only JSONL run record, so the
  whole family tree can be reconstructed from the log alone.
- **The Hortus verifier gate judges.** Separate code
  (`hortus/verifier.py`) receives the champion genome and a
  reference design — never the run's narrative — and re-scores
  both under held-out environments the population was not
  evolved against, including a tighter constraint floor. A
  champion that only wins at home is rejected, and the verdict
  is filed into the run record.

**Evidence cap.** A Hortus champion is a CANDIDATE, nothing
more. Its outputs are capped at evidence ladder **level 2**
(computationally tested) and are filed as predictions
(`is_prediction`), exactly like a docking score. Passing the
Hortus gate is a pre-filter, **not** a ladder promotion: it does
not make a result "independently reproduced" (level 3), because
the gate is part of the same component that generated the
candidate. Promotion remains the independent verifier's job,
from archived inputs, under the rules above. Nothing Hortus
produces is a discovery claim, and no code path in `hortus/`
grants a level above 2.

The shipped demo target is a fin/heatsink geometry evolved
against the toy thermal model in `hortus/model.py` — stated
assumptions, closed-form arithmetic, honest as a demonstration
and not physics truth. One real run is on record
(`hortus/records/hortus-demo-run.jsonl`, seed 20261101, 300
generations): best score 74.9996 at generation 0 to 138.3907 at
generation 300, champion organism 9086, verifier verdict PASSED
(verified-candidate). Tests: `os/tests/test_hortus_engine.py`.

**The scorer's own ladder.** The fitness model earns trust in
rungs, and a champion may only be described at the rung its
scorer has reached:

- **Rung 1 — formula.** The closed-form model as shipped,
  compared against nothing. The run above stands at this rung.
- **Rung 2 — calibrated against real measurements.**
  REACHED 2026-11-01. The heat core was scored against 14
  real Wakefield Engineering bonded-fin heatsinks with
  measured natural-convection thermal resistances
  (`hortus/calibration/datasheet_parts.json`); uncalibrated it
  overstated every part (mean error -64.5% on the calibration
  subset, -62.9% on held-out validation). One fitted
  coefficient later (a single multiplier on h, fitted on the
  calibration subset only), held-out validation error is
  ±6.3% RMS (mean -3.9%). The full record, including the
  residual blind spot — tight-pitch profiles whose fin-channel
  choking the model cannot represent, still -33% to -44% — is
  `hortus/calibration/CALIBRATION.md`. The evolution was
  re-run under the calibrated scorer (same protocol;
  `hortus/records/hortus-calibrated-run.jsonl`): best score
  27.6091 to 53.1321, champion organism 8175, verifier PASSED
  in all three calibrated held-out environments. The champion
  is re-filed (`hortus/records/hortus-calibrated-champion.json`)
  as: champion under calibrated scorer, validation error
  ±6.3% — rung 2 of 4; not simulation-verified, not
  fabricated/measured.
- **Rung 3 — real simulation.** Not reached. Finalists
  re-scored in a physics solver (CFD/FEA) instead of a
  formula; that is Officina-stage work.
- **Rung 4 — metal.** Not reached. The champion is fabricated
  and bench-measured; only then is a design "proven" in the
  physical sense, and only a human with a bench can do it.

The evidence cap is unchanged by any of this: a Hortus
champion, at any scorer rung, remains a ladder level 2
candidate filed as a prediction. The rungs grade the SCORER's
trustworthiness; they do not promote the claim.

**Score hunt (2026-11-01).** Four single-lever experiments
against the rung-2 baseline (53.1321) under this calibrated
scorer: longer search (+0.0004 — the baseline had converged),
forced air (a condition change, design unchanged), copper
(worse under the mass cap; its champion was rejected at the
gate, 25 mg over the mass cap), and a wider genome — fins to
60, height to 100 mm — which gained +62.3%. The current best
Hortus champion is the wider-genome run's organism 78901 at
86.2266, verifier-passed, filed in
`hortus/records/hortus-hunt-champion.json`; full results and
the honest caveats are in `hortus/records/SCORE_HUNT.md`. The
champion's level is unchanged: rung 2 of 4, a candidate.

## Alerts (shared wire format)

Alert lines follow the FND-020 freeze in `intel/README.md`:
`ALERT:<id> <severity> <kind>`, severity `critical` or `warning`,
one line, pointing at a stored record. A pack alert adds a
privacy class and an urgency class (see `worlds/README.md`);
only alerts marked summary may cross the bus.

| Kind | Severity | Privacy | Crosses bus | Carries |
|---|---|---|---|---|
| hazardous-request-blocked | critical | local | no | Request id and the blocked category. Contents stay in the lab. |
| verifier-veto | warning | summary | yes | Finding id, the level it was stopped at, veto reason class. No data. |
| reproduction-mismatch | warning | local | no | Experiment id and which verification check failed. Logs stay in the lab. |
| budget-cap-reached | warning | local | no | Job id and the compute budget cap state. |
| finding-promoted | warning | summary | yes | Hypothesis id, title, and the level the verifier promoted it to. |
| unverified-ageing | warning | local | no | Count of findings past the reproduction age threshold, and the oldest wait. |

## Privacy classes

| Class | Contents |
|---|---|
| local_only | Full experiment inputs and outputs, unpublished findings and working notes, datasets and retrieved source files, complete verification logs, failed hypotheses and failed runs (kept permanently, never shared as claims). |
| bus_summary | Hypothesis titles and their evidence-ladder levels, compute job counts and states, promotion and veto notices with levels only, sealed cycle summaries. |

Research data stays in the lab that made it. What crosses the
bus is what another world needs to coordinate: which questions
are open, what level their claims honestly sit at, and how much
work is queued. Never the findings themselves.

## Cross-world messages

Sends:

- To **crew**: `research-cycle-summary` (cycle id, hypothesis
  titles with their ladder levels, compute job counts, veto
  counts). Never carries experiment inputs or outputs,
  unpublished findings, datasets, or credentials or tokens.

Receives:

- From **crew**: `research-tasking` (research problems and
  priorities set by the crew world; problem statements only).

## Firstboot config

Per-installation personalization happens at firstboot, not in a
per-lab image. One Science Lab image serves every installation;
each box learns which laboratory it is during first boot. Fields
are prompts only; zero credentials are baked into any image.

| Field | Label | Required |
|---|---|---|
| lab_name | Laboratory name for this installation | yes |
| default_domain | Default research domain (for example chemistry, mathematics, biology) | yes |
| compute_budget_cap | Compute budget cap for this installation | yes |
| room_name | Bus room this installation joins | yes |
| gateway_token | MCP gateway token slot (prompted at first boot, never baked into the image) | no |

## Urgency classes

| Rank | Class | Meaning in this pack |
|---|---|---|
| 1 | life-safety | Hazardous-application requests blocked by the lab. Preempts everything else on the bus. |
| 2 | urgent | Verifier vetoes and compute budget caps. |
| 3 | routine | Ladder promotions, job state changes, verification queue ageing. |
| 4 | digest | Sealed research cycle summaries and end-of-shift records. |

## Build stages

From the approved build plan (`SCIENCE_LAB_PLAN.md`, 2026-11-01).
This pack is stage 1, item 1: the scaffold. One later-stage
component has landed ahead of the stage sequence on Del's
ruling: Hortus (the candidate-generation engine described
above, stage 3 machinery) is built and tested. That changes
nothing about the gates: the stage 1 completion gate below is
still the lab's first claim to any evidence level, and it has
not been run.

1. **Stage 1 — skeleton that can prove itself (light engines
   only).** This pack and registry entry; the record schemas;
   literature adapters (arXiv, Crossref, PubMed on top of the
   existing OpenAlex backend); light compute job types behind
   the queue (RDKit, SymPy, SciPy); verifier gate v1 with
   independent re-execution; the director loop on the guarded
   model path. Wet-lab validation and publication (discovery
   cycle steps 9 and 10) are human-gated, permanently.
2. **Stage 2 — chemistry and biology data depth.** PubChem and
   ChEMBL adapters; UniProt, RCSB PDB, Open Targets; a second
   reproduction gate in a different problem type.
3. **Stage 3 — discovery loop.** Competing-hypothesis generation
   at scale, the novelty engine (literature plus patents, with
   earliest sources recorded and uncertainties stated), a
   separate-model critic, automated prioritisation. The Hortus
   breeding engine (above) is this stage's candidate generator;
   it has landed early and currently runs only its shipped demo
   target, not lab hypotheses.
4. **Stage 4 — heavy compute (GPU-gated).** GNINA, OpenMM, Psi4
   and their class behind the same structured-request gateway,
   only if Del opens the GPU gate. Nothing in stages 1 to 3
   changes shape.
5. **Stage 5 — new departments as packs.** Materials, physics,
   energy: each lands as its own pack, no core changes.

## Stage 1 completion gate

Reproduce a published result, end to end, unaided:

**Delaney (2004), ESOL** — "ESOL: Estimating Aqueous Solubility
Directly from Molecular Structure," *J. Chem. Inf. Comput. Sci.*
44(3), 1000–1005. The system must (1) find the paper through the
literature layer and extract the published linear model and the
paper's **own reported fit statistics from the source** — the
target numbers are pulled from the paper at run time and are
**never hardcoded** in this pack, the plan, or any code; (2)
obtain the public ESOL compound set (1,128 compounds with
measured log solubilities); (3) compute the model's descriptors
with RDKit as signed compute jobs; (4) apply the published
equation and score predicted against measured across the full
set; (5) hand the archived inputs to the independent verifier,
who re-runs from scratch and confirms the aggregate error lands
within a stated tolerance of the paper's reported figure; (6)
file the full experiment record, including every compound where
the model misses badly.

The claim this gate earns is exactly ladder **level 3** —
independently reproduced computational result — *for the
reproduction itself*. It earns no discovery claim whatsoever,
and the gate report must say so.

## Never-fake rules

These are build rules, not aspirations. They mirror the
LABORATORY spec's verifier-with-veto and evidence ladder.

1. **Ladder discipline.** Every claim, everywhere, carries its
   evidence level 0 to 6. A docking score is level 2 on its best
   day and is never "a discovered medicine." A computational
   reproduction is level 3 and never "validated." Levels 4 and
   above require physical experiments by qualified humans; the
   software must not contain a code path that grants them.
2. **Verifier veto is structural.** The verifier receives the
   problem, data, methodology, and archived inputs — not the
   generator's narrative — and re-executes. Its rejection
   requeues or kills the finding. No agent, including the
   director, can override a veto; only Del can, in writing, on
   the record.
3. **No terminal, only structured requests.** All calculation
   goes through signed, schema-validated jobs. An agent that
   "just ran something in a shell" produced nothing the system
   may cite.
4. **Failures are records.** Failed hypotheses and failed runs
   are kept, indexed, and checked before new work starts.
   Deleting a failure is falsification.
5. **Sources, not snippets.** A finding's evidence trail ends at
   a retrieved original source with a locator and a content
   hash. A search returning no results never establishes
   novelty; a qualified human review is still required before
   any defensible novelty claim.
6. **Model agreement is not truth.** Critic and verifier run on
   separate models where available. Agreement between models
   moves nothing up the ladder; only re-execution and data do.
7. **Predictions are not experiments.** Docking, structure
   prediction, and simulation output are labelled predictions at
   filing time, in the record schema itself (`is_prediction`),
   not in prose someone can forget to write.
8. **Hard human gates.** No autonomous chemical synthesis,
   biological engineering, or human or animal experimentation
   pathways exist in this system. Hazardous-application requests
   are blocked, not routed (see the `hazardous-request-blocked`
   alert).
9. **Honesty of status.** Pack `status` fields, README claims,
   and demo copy follow the house rule across Meta OS: a thing
   is "spec," "skeleton," or "verified" — and "verified" means
   someone ran the check named next to the claim.

## Honesty label

PARTIAL. This pack defines watchers, agents, alerts, privacy
classes, cross-world messages, firstboot fields, urgency
classes, and the two record schemas — and, as of 2026-11-01,
contains one built runtime component: the Hortus breeding
engine (`hortus/`), unit-tested, with one real executed run on
record against its own analytic toy model. Hortus is not wired
into the lab's job queue or discovery cycle, no agent in the
roster has run, no lab experiment record has been filed, the
Delaney stage 1 gate has not been attempted, and the pack does
not contain a working science system. `pack.json` status is
`partial` because a runtime now exists and the manifest names
it, per the worlds honesty convention; every other part of
this pack remains spec.
