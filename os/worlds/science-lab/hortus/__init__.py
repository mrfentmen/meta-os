"""Hortus — Meta Scientia's breeding engine (candidate generator).

Stdlib-only evolution engine: a population of candidate designs
is bred against a deterministic scorer (model.py), every birth,
death, and generation is appended to a JSONL run record
(records.py), and the run's champion must pass a separate
held-out verifier gate (verifier.py) before it may be called
even a verified candidate. Generator and verifier are separate
code paths; a Hortus champion is capped at evidence ladder
level 2 and is never a discovery claim (see PACK.md).
"""

from . import engine, model, records, verifier  # noqa: F401

__all__ = ["engine", "model", "records", "verifier"]
