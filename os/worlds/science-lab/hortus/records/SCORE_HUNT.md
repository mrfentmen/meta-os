# Hortus score hunt — four levers, one law (2026-11-01)

Boss's order: "find something that will make the score go up."
Four experiments, each changing exactly ONE lever against the
rung-2 baseline, all scored by the calibrated scorer, every
champion put through the verifier's held-out gate. All four
hunt runs share a fresh seed (20261102) so the levers are
compared on equal RNG footing; the baseline used 20261101.
Every run is a full append-only log in this directory and
reconstructs cleanly.

**Baseline** (`hortus-calibrated-run.jsonl`): 300 generations,
population 48, shipped genome bounds, calibrated train env
(h = 3.55161 W/m2K effective, natural convection). Final best
**53.1321**, champion organism 8175, genome (40 fins, 60.0 mm
height, 0.745 mm thickness, 1.400 mm base), verifier PASSED.

Was the baseline undercooked? No. Its champion was born at
generation 177, the last improvement of the entire run — the
best score did not move at all between generations 200 and 300
(53.1321 throughout). The 300-generation run had converged.

Was the baseline champion pinned by the walls? Yes — twice
over, and a third time by a constraint. The shipped bounds are
fin count ≤ 40 and fin height ≤ 60 mm (`model.GENE_BOUNDS`),
and 8175 sits exactly on both maxima. Its thickness (0.745 mm)
puts its fin spacing at exactly 1.800 mm, the train env's
margin boundary: a fourth fin's worth of area was available
only by paying the margin penalty. The champion was the best
design the BOX allowed, which is not the same as the best
design.

## Results

| Exp | Lever (the ONLY change vs baseline protocol) | Gens / pop | Final best | Δ vs 53.1321 | Champion genome (fins, height mm, thickness mm, base mm) | Verifier |
|---|---|---|---|---|---|---|
| A | Longer search: 3,000 generations, same bounds/env/gate | 3000 / 48 | 53.1325 | +0.0004 (+0.0008%) | organism 88072: (40.0, 60.0, 0.745, 2.680) | PASSED |
| B | Wider genome: fins ≤ 60, height ≤ 100 mm, base 1.0–3.0 mm (thickness bounds unchanged, see below) | 1500 / 64 | **86.2266** | **+33.0946 (+62.3%)** | organism 78901: (48.5, 100.0, 0.405, 1.000) | PASSED |
| C | Forced air (CONDITION): train h 3.55161 → 9.9445 W/m2K, EXTRAPOLATED | 1500 / 48 | 137.7113 *in the forced-air env* | +84.5792 raw — **not a design gain** | organism 4198: (40.0, 60.0, 0.745, 1.332) | PASSED (standard gate) |
| D | Copper (CONDITION): k 237 → 398 W/mK, rho 2700 → 8960 kg/m3 | 1500 / 48 | 30.6384 *in the copper env* | −22.4937 (−42.3%) | organism 19131: (40.0, 32.99, 0.400, 1.000) | **REJECTED** |

Run logs: `hortus-hunt-a-long-run.jsonl`,
`hortus-hunt-b-wide-run.jsonl`, `hortus-hunt-c-forced-run.jsonl`,
`hortus-hunt-d-copper-run.jsonl`; per-run summaries in
`score-hunt-{a,b,c,d}.summary.json`.

## Experiment notes

**A — longer search (design lever).** Ten times the generations
bought +0.0004. This run's own best at generation 300 was
already 53.13237, and its last improvement (generation 1914)
added +0.00012. Two different seeds, 300 and 3,000 generations,
land on the same corner of the box (40 fins, 60 mm, ~0.745 mm,
spacing exactly at the margin). Conclusion: the baseline had
converged; time was never the binding constraint. The box was.

**B — wider genome (design lever).** Bound changes, old →
new: fin count max 40 → 60; fin height max 60 → 100 mm; base
thickness 1.0–8.0 → 1.0–3.0 mm; fin thickness 0.4–4.0 mm
UNCHANGED (the ordered new minimum, 0.40 mm, already equals
the shipped one). The champion ran straight to the new
territory: 48 fins at the full 100 mm height, and it is pinned
AGAIN — height on the new maximum, thickness 0.405 mm a hair
above the minimum, base on the minimum, mass 0.450 kg exactly
at the 0.45 kg cap, spacing 1.67 mm (inside the margin band,
paying a small penalty for the extra area, above every hard
floor). Honest reading: +62.3% is real *within this scorer and
these rules*, and the design still wants more room — taller,
thinner, more fins — so 86.2266 is the best design in the
WIDER box, not a natural optimum. Each further widening is a
design-rules decision (a 100 mm fin at 0.4 mm thick is already
a foil, not a fin, in any real shop), not a search decision.

**C — forced air (condition lever, EXTRAPOLATED).** Train env h
set to 28.0 × 0.355161 = 9.9445 W/m2K: 28 is the nominal
forced-air coefficient the verifier's held-out set already
uses, scaled once by the calibration multiplier. The
multiplier was fitted on natural-convection datasheets only;
the model has a single h and cannot separate convection
regimes, so applying it here is an extrapolation and is
labelled as such everywhere C's numbers appear. The 137.7113
is the same heatsink design breathing faster air, not a better
heatsink: scored back under the baseline natural-convection
env, C's champion gets 53.1285 — the baseline champion's
53.1321, to three decimal places. C converged by generation
91 to the same corner genome. Nothing about the DESIGN
improved; the condition did. Filed as a condition result only.

**D — copper (condition lever).** k 237 → 398 W/mK (pure
copper at 25 °C, CRC Handbook value as tabulated by MatWeb)
and rho 2700 → 8960 kg/m3, so the mass cap and mass penalty
charge copper its real density (3.32× aluminium). One
correction to the hunt brief, recorded rather than silently
absorbed: the brief described the baseline material as
aluminium 6063 (k = 209). k = 209 is the 6063-T5 value used
when CHECKING the scorer against Wakefield datasheets
(calibration/); the evolution train env has always used
model.TRAIN_ENV's k = 237. D therefore changed k 237 → 398
against A and nothing else, preserving the one-lever rule.
Result: copper LOSES under a fixed mass cap. At 8960 kg/m3
the 0.45 kg cap buys roughly a third of aluminium's volume;
the evolved copper design is small (33 mm fins) and scores
30.6384 in its own env, 30.3230 scored as aluminium — worse
either way. And the gate REJECTED its champion: the genome
beats the reference on heat in all three held-out envs
(83.47 W vs 18.97 W; 25.44 W vs 5.62 W; 37.31 W vs 8.33 W)
but its mass is 0.45003 kg against the 0.45 kg cap — 25 mg
over. Training's penalty is soft (200 W per kg over costs it
0.005 points), so evolution rode the cap edge and tipped
over it; the verifier's hard feasibility check caught what
the fitness function tolerated. Copper is a finding, not a
failure of method: under a mass budget, conductivity per
kilogram is what matters, and copper's density eats its
conductivity advantage whole.

## Verdict

- **The lever that works is the box, not the clock.** Wider
  genome: **+33.0946 (+62.3%)**, the only design gain on the
  table. Longer search: +0.0004 — nothing.
- **Design gains (comparable on the baseline scale):** B
  86.2266, A 53.1325. **Condition gains (different scoring
  environments, NOT comparable as designs):** C 137.7113 in
  forced air with a champion that is baseline-grade (53.1285)
  in natural convection; D 30.6384 in copper, a regression,
  champion rejected at the gate.
- **Best honest champion overall: experiment B's organism
  78901** — genome (48.525 fins → 48 fins, 100.0 mm height,
  0.405 mm thickness, 1.000 mm base), final best 86.2266,
  verifier PASSED, filed as `hortus-hunt-champion.json`. Its
  level text: "champion under calibrated scorer (validation
  error +-6.3% RMS, 5.8% mean absolute, on 4 held-out
  datasheet parts never used in fitting) - rung 2 of 4; not
  simulation-verified, not fabricated/measured. Score-hunt
  experiment B champion (2026-11-01): evolved in a widened
  search space - fin count up to 60, fin height up to 100 mm,
  base thickness 1.0-3.0 mm - under the same calibrated scorer
  and gate; the design gains come from the wider space, not
  from any scorer change."

## What remains unverified

- B's champion, like every Hortus champion, is a candidate
  under an analytic toy scorer at rung 2 of 4: not
  simulation-verified (rung 3, in OpenCode's lane), not
  fabricated or measured (rung 4). The calibration behind the
  scorer is one manufacturer family (Wakefield bonded-fin),
  natural convection only; the wider genome's territory (fin
  heights to 100 mm, gaps to 1.67 mm at 48 fins) lies outside
  the calibrated profiles' geometry range, so the ±6.3%
  validation figure is inherited, not re-measured there.
- C's forced-air coefficient is an extrapolation of a
  natural-convection fit (labelled EXTRAPOLATED wherever it
  appears); no forced-air datasheet calibration exists yet.
- D's copper constants are handbook values (CRC/MatWeb),
  not measurements of any physical part.
- The engine change behind experiment B (optional
  `gene_bounds` on `run_evolution`, recorded in run_start)
  defaults to the shipped bounds; all 14 Hortus tests pass
  and pack validation is green, but no other engine behaviour
  was re-audited.
