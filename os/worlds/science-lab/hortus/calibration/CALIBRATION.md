# Hortus scorer calibration — rung 2

Date: 2026-11-01. Code: `check_scorer.py` in this directory.
Data: `datasheet_parts.json` (every value read from the source
document named there). Raw before/after numbers:
`results.json`; the pre-fit comparison is committed separately
in `UNCALIBRATED_RESULTS.md`.

## What was compared

The toy scorer's heat core (`model.heat_watts`) against the
measured natural-convection thermal resistances of 14 real
Wakefield Engineering bonded-fin heatsink configurations:
7 catalogue base profiles, each at fin heights of 2 in and
4 in, all 6 in long (the catalogue's rating basis for profiles
under 8 in wide). Predicted thermal resistance is
R = delta_t / Q with each part's own geometry, the part
family's alloy (aluminium 6063-T5, k = 209 W/mK per the ASM
data sheet), and the model's plate constants set to the part's
plate for the duration of the prediction.

Predictions use the unpenalised heat core. The demo scorer's
spacing/mass penalties are search constructs; no datasheet
rating corresponds to them, so including them would corrupt
the comparison in a way that flatters nothing and means
nothing.

## The split

- Calibration subset (fitted against): profiles 8711, 8731,
  8546, 8119, 8712 — 10 configurations.
- Validation subset (never fitted against, scored only with
  the finished multiplier): profiles 8737, 8556 —
  4 configurations.

## The fit

One global parameter: a multiplier on the model's nominal
convective coefficient (h = 10 W/m2K as shipped). Least
squares on percent error over the calibration subset,
golden-section search; deterministic.

- **Fitted multiplier: 0.355161** (effective h = 3.552 W/m2K,
  a physically sane value for natural convection seen through
  a model with no radiation term).

## Errors, before and after (percent error of predicted R)

| subset | mean before | mean after | mean \|err\| before | mean \|err\| after | RMS before | RMS after |
| --- | --- | --- | --- | --- | --- | --- |
| calibration (n=10) | -64.5% | -8.0% | 64.5% | 24.4% | 65.3% | 28.0% |
| **validation (n=4)** | **-62.9%** | **-3.9%** | **62.9%** | **5.8%** | **62.9%** | **6.3%** |

## Verdict

**Rung 2 is earned — with a named blind spot.** On parts the
fit never saw, the calibrated scorer predicts thermal
resistance to about ±6% RMS (mean error -3.9%, mean absolute
error 5.8%, worst single part -8.6%). That is a real,
held-out improvement from ~63% systematic overstatement, and
it makes the scorer a defensible ranking instrument for this
heatsink family: designs it ranks better are, within that
error band, better.

The blind spot is visible in the calibration subset's own
residual (RMS 28%): the two tight-pitch profiles (8546 and
8712, fin gaps of ~3.8 mm) still read -33% to -44% after the
fit. In natural convection, closely spaced fins choke the
buoyant flow between them; the toy model has no such physics
(its spacing term is a demo penalty, deliberately excluded
here), so no single h multiplier can or should absorb it.
Those profiles are not evidence the calibration failed; they
are the map of where the toy model's physics ends. Champions
evolved under the calibrated scorer inherit this: within wide
to moderate fin pitch the scorer is calibrated to ±6%; tight-
pitch champions carry an unmodelled-choking caveat, and the
verifier's tighter held-out spacing floor remains their main
guard.

Other stated limits: the catalogue does not state which
surface finish its ratings were taken with, and the model has
no radiation term, so any radiation contribution is inside
the fitted coefficient and the residual; the ratings are one
manufacturer family's catalogue values (themselves nominal,
not per-unit test reports); and the fitted coefficient is for
natural convection in this geometry family — it says nothing
about forced convection or other shapes.

## Wiring

`model.CALIBRATED_H_MULTIPLIER = 0.355161`, applied only when
a caller opts in via `model.calibrated_train_env()` or
`model.calibrated_held_out_envs()` (each scales h exactly
once). The toy model as shipped is untouched and the rung-1
demo run reproduces exactly as recorded.
