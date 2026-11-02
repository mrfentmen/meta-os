# Officina stage 2c record — blueprint packs (OC2B-370)

## What it does

Emits a buildable blueprint pack from a 2a run record: dimensions
(H/t/N/base/footprint), aluminium material (k matched to the
simulator), 5 ordered build steps each referencing its dimensions,
the live bounds copied into the pack for readers, and provenance
(words, rounds, proven flag, both R numbers). `check_pack`
re-verifies every dimension against the live heatsink.py ranges
plus the 1.0 mm gap floor and the 100000 mm^3 volume budget,
naming each violation.

Runs: brief-a/b/c packs + build-001/002 packs — all five check
ok=True from the build dir AND from a clean directory. Checker
tests pin: at-bounds pass, +1 mm over FIN_HEIGHT_MM fails naming
the field, below-2.0 mm base fails (closed range, thin side).

## What it never claims

- A pack from an unproven design exports proven=false (pinned).
- A pack is not a built part: thermal acceptance is labelled
  SIMULATED, and a human decides whether anything gets built.
- Bounds are the workshop's widened ranges, not physics limits.

## Registry/README proposals (OC2B-372 2c half — FOR PARENT: lift into status file §15)

- PROPOSE os/worlds/officina/PACK.md: parts list gains
  runtime/pack_export.py ("emits packs; check_pack gates builds").
- PROPOSE agents/registry.json: no new role; workshop-herald gains
  "+pack-export (bounds-gated)" capability line only.
