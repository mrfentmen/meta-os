#!/usr/bin/env python3
"""Officina pack export gate (CB-083).

A pack without its bounds record cannot be exported: the bounds are what
make a design score checkable after the fact. Refusal happens before the
file is opened, so a failed export writes nothing.
"""

import json
import os


class PackExportError(ValueError):
    pass


def export_pack(pack, path):
    """Write one pack export, or raise PackExportError before writing."""
    if not isinstance(pack, dict):
        raise PackExportError("pack export refused: pack must be an object")
    bounds = pack.get("bounds")
    if not isinstance(bounds, dict) or not bounds:
        raise PackExportError("pack export refused: missing bounds record")
    if not pack.get("artefact_class"):
        raise PackExportError("pack export refused: missing artefact_class")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(pack, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path
