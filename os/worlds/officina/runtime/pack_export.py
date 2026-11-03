#!/usr/bin/env python3
"""Stage 2c blueprint pack export + bounds checker for META OFFICINA.

From a 2a run record (brief + iterated final parameters), emit the
blueprint pack a workshop could build from: dimensions, materials,
ordered build steps — every dimension inside the widened simulator
bounds (fin height <= 80 mm, base thickness <= 12 mm lineage; the
bounds are read live from heatsink.py, never copied). The checker
rejects any pack with an out-of-bounds dimension, a gap below the
1.0 mm floor, or a volume above budget, with each violation named.

Stdlib only. No model calls, no network. A pack exported from an
unproven design carries proven=false and the failing verification;
it is never dressed up as proven (same honesty rule as stage 1/2a).
A concept render, when one exists, is labelled GENERATED in the
pack and in its filename — a concept, never a measurement or photo.
"""

import json
import os
from datetime import datetime, timezone

from heatsink import (
    BASE_THICKNESS_MM,
    FIN_COUNT,
    FIN_HEIGHT_MM,
    FIN_THICKNESS_MM,
    FOOTPRINT_W_MM,
    FOOTPRINT_L_MM,
    K_ALUMINUM_W_MK,
    MIN_GAP_MM,
    VOLUME_BUDGET_MM3,
    HeatsinkParams,
    simulate,
)

#: The widened bounds, re-exported for readers: these names ARE the
#: heatsink.py ranges (same objects), so the pack cannot drift.
BOUNDS = {
    "fin_height_mm": FIN_HEIGHT_MM,
    "fin_thickness_mm": FIN_THICKNESS_MM,
    "fin_count": FIN_COUNT,
    "base_thickness_mm": BASE_THICKNESS_MM,
    "footprint_mm": (FOOTPRINT_W_MM, FOOTPRINT_W_MM),
}

DIMENSION_KEYS = (
    "fin_height_mm",
    "fin_thickness_mm",
    "fin_count",
    "base_thickness_mm",
    "footprint_mm",
)


def _params_of_record(record):
    fp = record.get("final_params")
    if fp is None:
        raise ValueError("run record has no final_params (ungradeable?)")
    return HeatsinkParams(
        fin_height_mm=float(fp["fin_height_mm"]),
        fin_thickness_mm=float(fp["fin_thickness_mm"]),
        fin_count=int(fp["fin_count"]),
        base_thickness_mm=float(fp["base_thickness_mm"]),
    )


def build_steps(params):
    """Ordered workshop build steps, each referencing its dimension."""
    gap = (FOOTPRINT_W_MM - params.fin_count * params.fin_thickness_mm) / (
        params.fin_count - 1
    )
    return [
        {
            "n": 1,
            "action": "cut base plate",
            "detail": "50 x 50 mm aluminium plate to base_thickness_mm "
            "= %.2f mm" % params.base_thickness_mm,
            "dims": ["base_thickness_mm", "footprint_mm"],
        },
        {
            "n": 2,
            "action": "form fins",
            "detail": "%d straight rectangular fins, t=%.2f mm, "
            "H=%.2f mm, full 50 mm depth"
            % (
                params.fin_count,
                params.fin_thickness_mm,
                params.fin_height_mm,
            ),
            "dims": ["fin_count", "fin_thickness_mm", "fin_height_mm"],
        },
        {
            "n": 3,
            "action": "deburr and gap-check",
            "detail": "clear every channel; drawn gap %.3f mm must stay "
            ">= %.1f mm floor" % (gap, MIN_GAP_MM),
            "dims": ["fin_count", "fin_thickness_mm"],
        },
        {
            "n": 4,
            "action": "inspect against bounds",
            "detail": "every dimension inside the widened bounds "
            "(H in %s, t in %s, N in %s, base in %s); run "
            "check_pack before any build" % (
                list(FIN_HEIGHT_MM),
                list(FIN_THICKNESS_MM),
                list(FIN_COUNT),
                list(BASE_THICKNESS_MM),
            ),
            "dims": list(DIMENSION_KEYS),
        },
        {
            "n": 5,
            "action": "thermal acceptance (simulated)",
            "detail": "held-out gate re-score from the parameters; a "
            "pass is a simulation result, not a measured heatsink — "
            "a human decides whether anything gets built",
            "dims": [],
        },
    ]


def export_pack(record, concept_render=None):
    """Emit the blueprint pack dict for a 2a run record."""
    params = _params_of_record(record)
    grade = record.get("final_grade") or {}
    verification = record.get("verification")
    if concept_render is None:
        concept_render = {
            "present": False,
            "note": "no concept render generated for this pack",
        }
    return {
        "stage": "2c-blueprint-pack",
        "artefact_class": record["brief"]["artefact_class"],
        "dimensions": {
            "fin_height_mm": params.fin_height_mm,
            "fin_thickness_mm": params.fin_thickness_mm,
            "fin_count": params.fin_count,
            "base_thickness_mm": params.base_thickness_mm,
            "footprint_mm": FOOTPRINT_W_MM,
        },
        "materials": [
            {
                "part": "fins + base",
                "name": "aluminium",
                "thermal_conductivity_w_mk": K_ALUMINUM_W_MK,
                "note": "matches the simulator's k; no alloy, finish, "
                "or fastener specified — unstated, not graded",
            }
        ],
        "steps": build_steps(params),
        "bounds": {k: list(v) for k, v in BOUNDS.items()},
        "provenance": {
            "rough_words": record.get("rough_input"),
            "rounds_used": record.get("rounds_used"),
            "proven": bool(record.get("proven")),
            "status": record.get("status"),
            "final_r_th_c_per_w": grade.get("r_th_c_per_w"),
            "verification_proven": bool(
                verification and verification.get("proven")
            ),
        },
        "concept_render": concept_render,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def check_pack(pack):
    """Bounds checker. Returns {ok, violations}: every dimension is
    verified against the live widened bounds, plus the gap floor and
    the volume budget recomputed from the parameters. A pack with any
    violation is rejected (ok=False), each reason named."""
    violations = []
    dims = pack.get("dimensions", {})
    for key in DIMENSION_KEYS:
        if key not in dims:
            violations.append("missing dimension: %s" % key)
            continue
        lo, hi = BOUNDS[key]
        try:
            value = float(dims[key])
        except (TypeError, ValueError):
            violations.append("non-numeric dimension: %s" % key)
            continue
        if key == "fin_count" and float(int(value)) != value:
            violations.append(
                "fin_count %s is not a whole number" % (dims[key],)
            )
        if not lo <= value <= hi:
            violations.append(
                "%s %.4g outside bounds [%s, %s]"
                % (key, value, lo, hi)
            )
    if not violations or all(
        k in dims for k in ("fin_count", "fin_thickness_mm")
    ):
        try:
            params = HeatsinkParams(
                fin_height_mm=float(dims.get("fin_height_mm", 0)),
                fin_thickness_mm=float(dims.get("fin_thickness_mm", 0)),
                fin_count=int(float(dims.get("fin_count", 0))),
                base_thickness_mm=float(
                    dims.get("base_thickness_mm", 0)),
            )
            result = simulate(params)
            if result.gap_mm < MIN_GAP_MM:
                violations.append(
                    "fin gap %.3f mm below minimum %.1f mm"
                    % (result.gap_mm, MIN_GAP_MM)
                )
            if result.volume_mm3 > VOLUME_BUDGET_MM3:
                violations.append(
                    "volume %.1f mm^3 above budget %.1f mm^3"
                    % (result.volume_mm3, VOLUME_BUDGET_MM3)
                )
        except (TypeError, ValueError, KeyError) as e:
            violations.append("dimensions do not form a simulatable "
                              "design: %s" % e)
    footprint = dims.get("footprint_mm")
    if footprint is not None and float(footprint) != FOOTPRINT_W_MM:
        violations.append(
            "footprint %.4g mm is not the class footprint %.0f mm"
            % (float(footprint), FOOTPRINT_W_MM)
        )
    return {"ok": not violations, "violations": violations}


def write_pack(pack, path):
    """Write the pack as JSON. Returns the path."""
    with open(path, "w") as f:
        json.dump(pack, f, indent=2)
        f.write("\n")
    return path


def read_pack(path):
    """Read a pack file back (for the independent clean-dir check)."""
    with open(path) as f:
        return json.load(f)


def main(argv=None):
    """CLI: pack_export.py <record_json> <pack_json> — export, then
    self-check with check_pack (nonzero exit if rejected)."""
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print("usage: pack_export.py <record_json> <pack_json>")
        return 2
    record_path, pack_path = argv
    with open(record_path) as f:
        record = json.load(f)
    pack = export_pack(record)
    check = check_pack(pack)
    write_pack(pack, pack_path)
    print(
        "pack %s check=%s -> %s"
        % (pack_path, "ok" if check["ok"] else "REJECTED", pack_path)
    )
    for v in check["violations"]:
        print("  violation: %s" % v)
    return 0 if check["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
