# EVAL — batch 7: full re-run on current main (2026-11-03)

Ordered by Del ("do testing to get evals up... do evals on the
applications"). Method identical to batches 3–6: the real pipeline
helper (spark_call.py assess) with each product's own prompt
profile, one Muse Spark 1.3 call per frame, on the 15-frame
Wikimedia Commons pack in test-footage/frames/, adjudicated by Pax
against the manifest under the batch-6 rules (MATCH = assessment
names the expected class or correctly rejects a look-alike;
HELD = unconfirmed or a true but weaker class, routed to a human;
MISS = wrong call). Tree: main @a71444ed. Run cost: $0.1163
estimated (guardrail cumulative $2.15 of the $75 test budget).

## Result

- MATCH 12/15 = 80% · HELD 3/15 = 20% · MISS 0/15 = 0%
- Emergencies exact-named: 5/5 (house fire, car fire, wildfire
  smoke, person on ground, vehicle collision scene)
- False emergency flags: 0/8
- Category validity: 15/15
- Regions: 10 boxes returned across the pack

Identical score to batch 6, and the same three frames HELD, for
the same reasons:

- ignis-dust-1: "indeterminate" — dust not called smoke.
- vigiles-altercation-1: "crowd gathered" — true of the protest
  scene, altercation not committed to.
- medicus-bench-1: "person motionless" — a true, weaker scene
  class for the bench sleeper, not declared "person on ground."

Every look-alike was handled correctly this run: steam and fog
named "steam or fog," sunbathing, yoga, and the curb sitter all
read as normal activity, and the busy crossing stayed "normal
activity" (no crowd false flag).

## Per frame

| frame | expected | assessment | verdict |
|---|---|---|---|
| ignis-fire-1 | visible flame | visible flame | MATCH |
| ignis-fire-2 | visible flame | visible flame | MATCH |
| ignis-smoke-1 | visible smoke | visible smoke | MATCH |
| ignis-steam-1 | steam or fog (not smoke) | steam or fog | MATCH |
| ignis-fog-1 | steam or fog (not smoke) | steam or fog | MATCH |
| ignis-dust-1 | look-alike, dust | indeterminate | HELD |
| vigiles-crowd-1 | crowd gathered | crowd gathered | MATCH |
| vigiles-normal-1 | normal activity | normal activity | MATCH |
| vigiles-altercation-1 | public disturbance | crowd gathered | HELD |
| medicus-ground-1 | person on ground | person on ground | MATCH |
| medicus-collision-1 | vehicle collision scene | vehicle collision scene | MATCH |
| medicus-bench-1 | look-alike, bench sleeper | person motionless | HELD |
| medicus-sunbathing-1 | look-alike, sunbathing | normal activity | MATCH |
| medicus-yoga-1 | look-alike, yoga | normal activity | MATCH |
| medicus-curb-1 | look-alike, curb rest | normal activity | MATCH |

Status: VERIFIED (Pax ran the calls and adjudicated the raw model
text himself, 2026-11-03). The batch-6 configuration holds on the
current tree; no prompt change was made in this batch.
