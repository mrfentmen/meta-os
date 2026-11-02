#!/usr/bin/env python3
"""Faber build-order seam (CB-090).

The material is checked before any stage runs. An unknown material is a
refused order, not a stage failure: the caller's stage functions must not
be called at all.
"""


class FaberError(ValueError):
    pass


MATERIALS = {
    "aluminium": 205.0,
    "copper": 401.0,
    "steel": 50.0,
}


def run_order(order, stages=()):
    if not isinstance(order, dict):
        raise FaberError("faber: order must be an object")
    material = order.get("material")
    if material not in MATERIALS:
        raise FaberError("faber: unknown material %r; no stage ran" % (material,))
    results = []
    for stage in stages:
        results.append(stage(order))
    return results
