# REPRODUCTION REPORT — Science Lab + Officina (Bond, wave 2, 2026-11-02)

Scope: tasks 46-56. HEAD `78862a5`.

## 46. Science status claims

`os-build/OPENCODE2_SCIENCE_STATUS.md` does **not** exist. The nearest
document, `os-build/SCIENCE_LAB_W2_SLICE1.md`, says plainly:

> REGISTRY ENTRIES ONLY. No lab agent has run, no cycle run has executed,
> no new claim exists at any evidence level.

That is the claim set: 13 registry entries, no cycle.

## 47. First completed science cycle

None found. Searched `os/worlds/science-lab/` and `os-build/` for cycle
ledgers, result files, and preregistration records. The only science
artifacts are Hortus breeding logs and the calibration table.

Status: BLOCKED-no-cycle.

## 48. Independent re-run

Not possible: there are no recorded cycle inputs (seed/hash) to re-run.
BLOCKED-no-cycle.

## 49. MATCH or DIFFER

Not applicable. No output pair exists.

## 50. Evidence ladder vs proof

Not applicable. No cycle claim exists to grade.

## 51. Falsifier + preregistration ordering

Not applicable. No cycle ledger exists, so there is no ordering to check.

## 52. First completed Officina build

`os/worlds/officina/runs/rough-words-run-001.json` is the recorded
words-to-pack build; `rough-words-best-design.json` carries the proven
design and its verification block.

## 53. Officina 2a gate

```
python3 os-build/officina_2a_gate.py
GATE: PASS (14/14 clauses)
```

Exit 0. Log: `os-build/bond-evidence/logs/officina-2a-gate.log`.

## 54. Dimensions inside the widened bounds

Declared ranges (`os/worlds/officina/runtime/heatsink.py:54-57`, widened
2026-11-01): height 5-80 mm, thickness 0.5-3 mm, count 4-30, base 2-12 mm.

The proven design (`rough-words-best-design.json`):

| Dimension | Value | Range | Inside |
|---|---|---|---|
| fin_height_mm | 39.0625 | 5-80 | yes |
| fin_thickness_mm | 1.5 | 0.5-3 | yes |
| fin_count | 15 | 4-30 | yes |
| base_thickness_mm | 4.0 | 2-12 | yes |

VERIFIED.

## 55. This file

Written from 46-54.

## 56. Claims with no artifact behind them

1. `MODEL_INTEGRATION.md` says SAM "wiring into the patrol step is the
   next queue item" and Wonder review is "a named follow-up" — no code, no
   artifact. Honest wording, but not implemented.
2. `MODEL_INTEGRATION.md` says Muse Image renders concept art for Officina
   and Musica. No caller of `generate_image` exists; no image artifact.
3. `MODEL_INTEGRATION.md` spend note (11 calls, $0.0047 judge smoke) has no
   receipt file in the repo.
4. No science-cycle claim exists, so nothing to flag there.

## What was not done

The Science Lab reproduction half of Section 4 is blocked by the absence
of a completed cycle. It is not marked pass. Officina is the only half
with a real, re-runnable proof.
