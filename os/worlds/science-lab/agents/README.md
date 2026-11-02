# Science Lab agents — lab-local job definitions

Status: **SPEC.** Job definitions for the 13 registered lab agents.
Each agent's hosting record lives in `agents/registry.json` (owner
`system: science-lab`, lane `Science Lab (research)`, command
`["true"]` — stubs that run nothing). Roles below are verbatim from
`os/worlds/science-lab/pack.json`; watches (`serves`) match the
registry `capabilities`. No agent has run; no lab experiment record
has been filed; the Delaney stage 1 gate has not been attempted.

| # | Agent (nick) | File | Serves |
|---|---|---|---|
| 1 | research-director | [research-director.md](research-director.md) | literature-watch, experiment-watch, verification-watch |
| 2 | literature-researcher | [literature-researcher.md](literature-researcher.md) | literature-watch |
| 3 | scientific-analyst | [scientific-analyst.md](scientific-analyst.md) | literature-watch, experiment-watch |
| 4 | mathematics-researcher | [mathematics-researcher.md](mathematics-researcher.md) | experiment-watch |
| 5 | chemistry-researcher | [chemistry-researcher.md](chemistry-researcher.md) | experiment-watch |
| 6 | biology-researcher | [biology-researcher.md](biology-researcher.md) | experiment-watch |
| 7 | physics-researcher | [physics-researcher.md](physics-researcher.md) | experiment-watch |
| 8 | hypothesis-generator | [hypothesis-generator.md](hypothesis-generator.md) | literature-watch, experiment-watch |
| 9 | computational-scientist | [computational-scientist.md](computational-scientist.md) | experiment-watch |
| 10 | statistician | [statistician.md](statistician.md) | experiment-watch, verification-watch |
| 11 | scientific-critic | [scientific-critic.md](scientific-critic.md) | verification-watch |
| 12 | independent-verifier | [independent-verifier.md](independent-verifier.md) | verification-watch |
| 13 | research-archivist | [research-archivist.md](research-archivist.md) | experiment-watch, verification-watch |

Structural rules (PACK.md Never-fake rules): hypothesis-generator
never verifies its own work; verifier receives problem + data +
methodology + archived inputs, never the generator's narrative;
director cannot override a veto (only Del, in writing, on the
record); computational-scientist has no terminal — queue jobs only;
research-archivist is the only agent that may post across worlds,
and only titles, levels, and counts.

Evidence ladder 0–6 and caps (all files): system records cap at
level 3 (`experiment.schema.json`); unverified/mismatch cap at
level 2; only the independent-verifier promotes, only on
`reproduced`. Levels 4+ require physical experiments / external
replication by qualified humans. Steps 9/10 are human-gated,
permanently; step 8 has no verified source text — UNIMPLEMENTED
in every file.
