"""Hortus rung-2 calibration: toy scorer vs real datasheet ratings.

Compares the analytic toy model in ../model.py against measured
thermal resistances of real commercial heatsinks
(datasheet_parts.json, Wakefield Engineering bonded-fin
catalogue; every value in that file was read off the source).

Method, stated so the result can be audited:

- Each part's geometry is fed to the model's heat core
  (model.heat_watts) with the plate constants temporarily set to
  the part's own plate size. Predictions use the UNPENALISED
  heat core: the demo scorer's spacing/mass penalties are
  search constructs for evolution, not physics, and no
  datasheet rating knows about them.
- Predicted thermal resistance R = delta_t / Q. Q is linear in
  delta_t in this model, so R is independent of the chosen
  delta_t; 40 K is used to match the training environment.
- Conditions matched to the datasheet as closely as the model
  allows: natural convection throughout; the alloy conductivity
  of the parts' stated alloy (6063-T5, k = 209 W/mK, ASM data
  sheet; see datasheet_parts.json property_sources).
- The model's one convective coefficient is its shipped nominal
  h = 10 W/m2K (model.TRAIN_ENV). Calibration fits ONE global
  multiplier on that h, by least squares on percent error, on
  the calibration subset ONLY. The validation subset is scored
  with the fitted multiplier but never fitted against, and the
  fit function never receives it.

Usage:
    python3 -m hortus.calibration.check_scorer
        Print the uncalibrated (multiplier = 1) comparison.
    python3 -m hortus.calibration.check_scorer --write-uncalibrated-md
        Also write UNCALIBRATED_RESULTS.md beside this file.
    python3 -m hortus.calibration.check_scorer --fit
        Fit the multiplier on the calibration subset, print
        before/after for BOTH subsets, write results.json.
"""

import json
import math
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    from hortus import model  # noqa: E402
else:
    from .. import model

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS_PATH = os.path.join(HERE, "datasheet_parts.json")
RESULTS_PATH = os.path.join(HERE, "results.json")
UNCALIBRATED_MD_PATH = os.path.join(HERE, "UNCALIBRATED_RESULTS.md")

# The model's shipped nominal coefficient. Calibration scales
# THIS number and nothing else.
NOMINAL_H = model.TRAIN_ENV["h_w_per_m2k"]
DELTA_T_K = 40.0
ALLOY_K = 209.0       # aluminium 6063-T5, ASM data sheet
ALLOY_RHO = 2700.0


def load_parts(path=PARTS_PATH):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data["parts"]


def load_parts_report(path=PARTS_PATH):
    """Load parts, skipping entries without a measured score.

    Returns {"parts", "count", "skipped", "skipped_count"}. A
    skipped entry is reported by index and part_id, never silently
    dropped.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    parts, skipped = [], []
    for index, part in enumerate(data.get("parts", [])):
        if part.get("measured_thermal_resistance_c_per_w") is None:
            skipped.append({
                "index": index,
                "part_id": part.get("part_id"),
                "reason": "missing measured_thermal_resistance_c_per_w",
            })
            continue
        parts.append(part)
    return {
        "parts": parts,
        "count": len(parts),
        "skipped": skipped,
        "skipped_count": len(skipped),
    }


def prediction_env(h_multiplier):
    """Environment for one datasheet prediction: natural
    convection at the (possibly scaled) nominal coefficient,
    the parts' alloy, and no demo penalties in reach of the
    heat core (heat_watts applies none itself)."""
    return {
        "name": "datasheet-natural-convection",
        "h_w_per_m2k": NOMINAL_H * h_multiplier,
        "k_w_per_mk": ALLOY_K,
        "rho_kg_per_m3": ALLOY_RHO,
        "delta_t_k": DELTA_T_K,
        "min_spacing_m": 0.0,
        "margin_spacing_m": None,
        "mass_cap_kg": float("inf"),
    }


def predicted_resistance(part, h_multiplier=1.0):
    """Model-predicted thermal resistance (K/W) for one part.

    The model's plate footprint is a module constant (it ships
    as the demo plate); it is set to the part's own plate for
    the duration of the call and restored afterwards, so no
    caller ever observes a mutated model.
    """
    geo = part["geometry_mm"]
    genome = (
        float(geo["fin_count"]),
        float(geo["fin_height_mm"]),
        float(geo["fin_thickness_mm"]),
        float(geo["base_thickness_mm"]),
    )
    env = prediction_env(h_multiplier)
    old_w, old_d = model.PLATE_WIDTH_M, model.PLATE_DEPTH_M
    model.PLATE_WIDTH_M = geo["plate_width_mm"] / 1000.0
    model.PLATE_DEPTH_M = geo["plate_length_mm"] / 1000.0
    try:
        q = model.heat_watts(genome, env)
    finally:
        model.PLATE_WIDTH_M, model.PLATE_DEPTH_M = old_w, old_d
    return DELTA_T_K / q


def error_rows(parts, h_multiplier=1.0):
    """One comparison row per part at a given h multiplier."""
    rows = []
    for part in parts:
        pred = predicted_resistance(part, h_multiplier)
        meas = float(part["measured_thermal_resistance_c_per_w"])
        rows.append({
            "part_id": part["part_id"],
            "profile_no": part["profile_no"],
            "fin_height_in": part["fin_height_in"],
            "subset": part["subset"],
            "predicted_c_per_w": pred,
            "measured_c_per_w": meas,
            "pct_error": 100.0 * (pred - meas) / meas,
        })
    return rows


def summarise(rows):
    """Subset error summary: mean signed %, mean |%|, RMS %."""
    if not rows:
        return {"count": 0, "mean_pct": None, "mean_abs_pct": None,
                "rms_pct": None}
    errs = [r["pct_error"] for r in rows]
    return {
        "count": len(rows),
        "mean_pct": sum(errs) / len(errs),
        "mean_abs_pct": sum(abs(e) for e in errs) / len(errs),
        "rms_pct": math.sqrt(sum(e * e for e in errs) / len(errs)),
    }


def fit_multiplier(calibration_parts):
    """Least-squares fit of the single global h multiplier on
    percent error, calibration subset only.

    Golden-section search on log(multiplier); R_pred falls
    monotonically as h rises, so the squared-error surface over
    this family is unimodal in practice and the search is exact
    to ~1e-9. Deterministic: no randomness anywhere.
    """
    def objective(log_m):
        m = math.exp(log_m)
        return sum(r["pct_error"] ** 2
                   for r in error_rows(calibration_parts, m))

    lo, hi = math.log(0.02), math.log(3.0)
    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0
    c = hi - inv_phi * (hi - lo)
    d = lo + inv_phi * (hi - lo)
    fc, fd = objective(c), objective(d)
    for _ in range(200):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - inv_phi * (hi - lo)
            fc = objective(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + inv_phi * (hi - lo)
            fd = objective(d)
    return math.exp((lo + hi) / 2.0)


def _subset(rows, name):
    return [r for r in rows if r["subset"] == name]


def _print_rows(rows):
    print("%-12s %-4s %-11s %10s %10s %9s"
          % ("part", "H\"", "subset", "pred R", "meas R", "% err"))
    for r in rows:
        print("%-12s %-4d %-11s %10.3f %10.3f %+9.1f"
              % (r["part_id"], r["fin_height_in"], r["subset"],
                 r["predicted_c_per_w"], r["measured_c_per_w"],
                 r["pct_error"]))


def _print_summary(label, summary):
    print("%-24s n=%d  mean %+7.1f%%  mean|.| %6.1f%%  rms %6.1f%%"
          % (label, summary["count"], summary["mean_pct"],
             summary["mean_abs_pct"], summary["rms_pct"]))


def _uncalibrated_md(rows):
    lines = [
        "# Uncalibrated scorer vs datasheet reality",
        "",
        "The Hortus toy scorer (hortus/model.py, as shipped,",
        "h multiplier = 1.0 - i.e. its nominal h = 10 W/m2K and",
        "its own demo plate replaced per part by the part's plate)",
        "against measured thermal resistances of real Wakefield",
        "Engineering bonded-fin heatsinks (datasheet_parts.json).",
        "This table was produced and committed BEFORE any",
        "calibration was fitted. It is the raw evidence the",
        "calibration has to answer to.",
        "",
        "| part | profile | fin height | subset | predicted R (K/W) | measured R (K/W) | % error |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append("| %s | %s | %d in | %s | %.3f | %.3f | %+.1f |"
                     % (r["part_id"], r["profile_no"],
                        r["fin_height_in"], r["subset"],
                        r["predicted_c_per_w"], r["measured_c_per_w"],
                        r["pct_error"]))
    lines += ["", "Subset summaries (percent error of predicted R):", ""]
    for name in ("calibration", "validation"):
        s = summarise(_subset(rows, name))
        lines.append("- %s: n=%d, mean %+.1f%%, mean |error| %.1f%%, "
                     "RMS %.1f%%"
                     % (name, s["count"], s["mean_pct"],
                        s["mean_abs_pct"], s["rms_pct"]))
    lines += [
        "",
        "Method: check_scorer.py in this directory; predicted R",
        "= delta_t / model.heat_watts under each part's own",
        "geometry, alloy 6063-T5 (k = 209 W/mK), natural",
        "convection, unpenalised heat core. Negative error means",
        "the model predicts a LOWER thermal resistance than the",
        "real part achieves - i.e. the toy model overstates how",
        "well the heatsink works.",
        "",
    ]
    return "\n".join(lines)


def main(argv):
    parts = load_parts()
    if "--fit" in argv:
        calibration = [p for p in parts
                       if p["subset"] == "calibration"]
        validation = [p for p in parts if p["subset"] == "validation"]
        m = fit_multiplier(calibration)
        before = error_rows(parts, 1.0)
        after = error_rows(parts, m)
        print("fitted h multiplier (calibration subset only): %.6f" % m)
        print("effective natural-convection h: %.3f W/m2K"
              % (NOMINAL_H * m))
        print()
        _print_rows(after)
        print()
        result = {"fitted_h_multiplier": m, "nominal_h": NOMINAL_H,
                  "effective_h": NOMINAL_H * m, "subsets": {}}
        for name, subset in (("calibration", calibration),
                             ("validation", validation)):
            b = summarise(_subset(before, name))
            a = summarise(_subset(after, name))
            result["subsets"][name] = {"before": b, "after": a}
            _print_summary(name + " before (m=1)", b)
            _print_summary(name + " after (m=fit)", a)
        result["rows_before"] = before
        result["rows_after"] = after
        with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=1, sort_keys=True)
        print("\nwrote %s" % RESULTS_PATH)
        return 0
    rows = error_rows(parts, 1.0)
    _print_rows(rows)
    print()
    for name in ("calibration", "validation"):
        _print_summary(name + " (uncalibrated)", summarise(_subset(rows, name)))
    if "--write-uncalibrated-md" in argv:
        with open(UNCALIBRATED_MD_PATH, "w", encoding="utf-8") as fh:
            fh.write(_uncalibrated_md(rows))
        print("\nwrote %s" % UNCALIBRATED_MD_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
