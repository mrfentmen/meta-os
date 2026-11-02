# W2 — Science Lab, first slice (Milo, BUILD WAVE 2026-11-02)

Branch: `milo/build-wave-w2`, off origin/main 804d1d7.
Status: **REGISTRY ENTRIES ONLY.** No lab agent has run, no cycle
run has executed, no new claim exists at any evidence level.
Hortus remains the lab's only built runtime component, unchanged.

## 1. The 13-agent team, as registry entries

`agents/registry.json` grows from 12 to 25 entries. Every entry is
copied from the lab pack's own roster (`os/worlds/science-lab/
pack.json` agents, `PACK.md` roster table) — nick, role, and
`serves` list carried verbatim into the registry's capability
field. Owner is `system: science-lab`; lane is `Science Lab
(research)`; budget is the standing governor placeholder
(maxWallMs 3600000, the crew entries' value) — the lab's real
compute budget cap is a firstboot field and is NOT set here.
Command is `["true"]`, the same placeholder the existing crew
entries carry: these entries name the agents, they do not run
them. Spawning a lab agent from this registry proves nothing
yet and is not claimed.

| Entry | Serves (capabilities) |
|---|---|
| research-director | literature-watch, experiment-watch, verification-watch |
| literature-researcher | literature-watch |
| scientific-analyst | literature-watch, experiment-watch |
| mathematics-researcher | experiment-watch |
| chemistry-researcher | experiment-watch |
| biology-researcher | experiment-watch |
| physics-researcher | experiment-watch |
| hypothesis-generator | literature-watch, experiment-watch |
| computational-scientist | experiment-watch |
| statistician | experiment-watch, verification-watch |
| scientific-critic | verification-watch |
| independent-verifier | verification-watch |
| research-archivist | experiment-watch, verification-watch |

Two structural rules from the pack carry over unchanged:
the hypothesis generator never verifies its own work, and the
verifier receives the problem, data, methodology, and archived
inputs — never the generator's narrative.

Verified in the worktree: `node agents/runtime.mjs list` loads
the registry clean, 25 entries, all 13 lab names present, no
duplicate-name error.

## 2. Discovery-cycle loop skeleton (phases, not invented steps)

The wave asks for the 10-step discovery cycle as the lab's
hosted loop skeleton. The full 10-step enumeration was NOT
found in the repo (searched `PACK.md`, `IDEAS_BUILD_LIST.md`,
`AGENT_LAYER_SPEC.md`, `AGENT_LAYER_TASKS.md`): this slice
does NOT invent steps 1–10. What the sources do name, and what
this skeleton therefore contains:

1. Problem (research-tasking in from crew; problem statements only)
2. Literature (original sources with locators and content hashes;
   a search result is a lead, never evidence)
3. Competing hypotheses (three to five per problem, each with a
   measurable prediction, an alternative explanation, and a
   disproof condition — a hypothesis without one cannot be filed)
4. Cheap calculations first (signed, schema-validated compute
   jobs through the queue; no terminal; a calculation that did
   not go through the queue does not exist)
5. Critic pass (attacks findings before verification; separate
   model from the generator when one is available)
6. Independent verification (re-execution from archived inputs;
   promotion or veto — see §3)
7. Archivist sealing (sealed cycle summary: cycle id, hypothesis
   titles with ladder levels, compute job counts, veto counts;
   titles, levels, and counts only cross the bus; research data
   never leaves the lab)
8. Human-gated terminal steps, named in the pack's stage 1:
   step 9 wet-lab validation and step 10 publication — human-gated,
   permanently, and not part of any automated loop.

OPEN, for Pax: where does the 10-step list live? Phases 1–7
above come from the director's pack role string and the stage 1
text; the numbering of the middle steps is unconfirmed until
that list is produced. A cycle run that produces records, not
claims, is the next slice — no such run exists yet.

## 3. Evidence ladder, enforced on records (already in the schemas)

Enforcement already lives in the lab's two record schemas; this
slice wires the registry to them and changes no schema:

- Hypothesis record (`schemas/hypothesis.schema.json`):
  `evidence_level` and `disproof_condition` are required fields.
  A record without its level, or without a disproof condition,
  fails validation and cannot be filed. New hypotheses file at
  level 0.
- Experiment record (`schemas/experiment.schema.json`):
  `evidence_level` is capped at 3 by the schema; an unverified
  or mismatched result is capped at 2 by its own rules; only a
  recorded independent reproduction (`verification_status:
  reproduced`) supports level 3.
- Levels 4–6 require physical experiments by qualified humans
  and are unreachable by this system alone; no code path in
  this slice grants them, and no automated path raises a record
  above level 3.
- Promotion belongs to the independent-verifier alone; its veto
  is final inside the system and the director cannot override it.
  Failed hypotheses and failed runs are kept permanently.

## 4. Independent Verification, named; first reproduction test chosen

Independent Verification is the `independent-verifier` registry
entry (§1): it re-executes from archived inputs and is the only
agent that may promote a claim up the ladder.

First reproduction test, CHOSEN AND WRITTEN UP here, run itself
a later slice per the wave: the pack's stage 1 completion gate —
Delaney (2004), ESOL. The system must find the paper through
the literature layer and extract the published model and the
paper's own reported fit statistics from the source (target
numbers pulled at run time, never hardcoded); obtain the public
ESOL compound set (1,128 compounds); compute descriptors with
RDKit as signed compute jobs; apply the published equation and
score predicted against measured across the full set; hand the
archived inputs to the independent verifier for re-execution
within a stated tolerance; file the full experiment record,
including every compound where the model misses badly. The claim
that gate earns is exactly ladder level 3 for the reproduction
itself, and no discovery claim whatsoever. The gate has NOT
been attempted — the pack says so, and this slice does not
change that.

## What is NOT in this slice

- No cycle run, no compute job, no lab record filed.
- No 10-step enumeration (OPEN, §2).
- No W3 Officina 2a acceptance gate and no W5 Gym drill —
  those are the next slices, queued, not started here.
- No merge: queued with Pax per the merge rule, branch only.
