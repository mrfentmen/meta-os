#!/usr/bin/env python3
"""Prior-art note shape for Officina (CB-088).

A prior-art claim without sources is an opinion, not a record. The
validator refuses it by name; it does not fabricate a source.
"""


class PriorArtError(ValueError):
    pass


def validate_note(note):
    if not isinstance(note, dict):
        raise PriorArtError("prior-art note refused: note must be an object")
    sources = note.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PriorArtError("prior-art note refused: sources are required")
    for source in sources:
        if not isinstance(source, str) or not source.strip():
            raise PriorArtError("prior-art note refused: every source must be a non-empty string")
    return True
