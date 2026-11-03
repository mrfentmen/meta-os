"""Schematic data for one heatsink design.

This is not a drawing and not an image: it is the data a drawing needs, taken
from the design's own numbers and nothing else. Every value here is either a
parameter or arithmetic on parameters, so a schematic can never show a fin the
simulator did not score.

Pure: no files, no clock, no model calls.
"""

SCHEMATIC_VERSION = 1


def schematic(params):
    """Sections for one design: overall stack, base plate, and each fin.

    `params` is anything with the four HeatsinkParams fields (the dataclass, or
    a dict-like with those keys). Fins are listed one per unit with their own
    thickness and height, because a drawing places each one, not the average.
    """
    get = params.get if isinstance(params, dict) else lambda k: getattr(params, k)

    fin_height = float(get("fin_height_mm"))
    fin_thickness = float(get("fin_thickness_mm"))
    fin_count = int(get("fin_count"))
    base_thickness = float(get("base_thickness_mm"))

    if fin_count < 1:
        raise ValueError("schematic: a design needs at least one fin")
    if min(fin_height, fin_thickness, base_thickness) <= 0:
        raise ValueError("schematic: dimensions must be positive")

    fins = [
        {"index": i, "thickness_mm": fin_thickness, "height_mm": fin_height}
        for i in range(fin_count)
    ]

    return {
        "v": SCHEMATIC_VERSION,
        "units": "mm",
        "overall": {
            "height_mm": round(base_thickness + fin_height, 6),
            "base_mm": base_thickness,
            "fin_height_mm": fin_height,
        },
        "base": {
            "thickness_mm": base_thickness,
            "fin_count": fin_count,
        },
        "fins": fins,
        "fin_count": fin_count,
        # The sum of the fin thicknesses: how much of the base is fin root.
        "fin_root_mm": round(fin_thickness * fin_count, 6),
    }


def validate_schematic(draw):
    """Named errors for a schematic dict; [] when the sections are complete."""
    errors = []
    if not isinstance(draw, dict):
        return ["schematic: must be an object"]
    for section in ("overall", "base", "fins"):
        if section not in draw:
            errors.append(section + ": section missing")
    if "fins" in draw:
        fins = draw["fins"]
        if not isinstance(fins, list) or not fins:
            errors.append("fins: must be a non-empty list")
        else:
            for i, fin in enumerate(fins):
                if fin.get("index") != i:
                    errors.append("fins[%d]: index is out of order" % i)
                if not fin.get("height_mm") or not fin.get("thickness_mm"):
                    errors.append("fins[%d]: a fin needs height and thickness" % i)
            if draw.get("fin_count") != len(fins):
                errors.append("fin_count: does not match the fin list")
    return errors
