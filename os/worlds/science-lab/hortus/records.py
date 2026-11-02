"""Hortus run records: append-only JSONL, fully reconstructible.

Every Hortus run writes one JSONL file. Records are only ever
appended; nothing is rewritten or deleted (PACK.md never-fake
rule 4: failures are records). The record kinds are:

- run_start   run configuration, seed, environment, model id
- birth       organism id, generation born, parent ids (empty
              for the seeded generation), genome, origin
- death       organism id, generation culled, cause
- generation  generation index, population size, best score,
              mean score, champion organism id for that step
- verdict     the verifier's ruling on the run's champion,
              with the held-out numbers it was based on
- run_end     final population ids and the run's champion id

Births and deaths together are the whole family tree: any
organism's ancestry and fate can be reconstructed from the log
alone, which reconstruct() below does and the tests check.
"""

import json
import os


class RecordWriter:
    """Append-only JSONL writer. Opens in append mode and never
    truncates; one JSON object per line, flushed per record so a
    crashed run still leaves its history on disk."""

    def __init__(self, path):
        self.path = path
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")

    def write(self, kind, **fields):
        record = {"kind": kind}
        record.update(fields)
        self._fh.write(json.dumps(record, sort_keys=True) + "\n")
        self._fh.flush()
        return record

    def close(self):
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def load_records(path):
    """Read a run's JSONL back into a list of record dicts."""
    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_generation(path, generation, parent_ids, child_ids):
    """Append one generation record with its parent and child ids.

    Refuses a child id that already exists in any generation record
    or repeats inside this one. One call writes exactly one record.
    """
    try:
        generation = int(generation)
    except (TypeError, ValueError):
        raise ValueError("generation must be an integer")
    parents = [str(p) for p in parent_ids]
    children = [str(c) for c in child_ids]
    if len(set(children)) != len(children):
        raise ValueError("generation record repeats a child id")
    existing = set()
    if os.path.exists(path):
        for record in load_records(path):
            if record.get("kind") == "generation-record":
                existing.update(str(c) for c in record.get("child_ids", []))
    duplicate = sorted(existing.intersection(children))
    if duplicate:
        raise ValueError("duplicate child id(s) refused: %r" % (duplicate,))
    record = {
        "kind": "generation-record",
        "generation": generation,
        "parent_ids": parents,
        "child_ids": children,
    }
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def list_generations(path, generation=None):
    """List generation records, optionally filtered by generation."""
    records = []
    if not os.path.exists(path):
        return records
    for record in load_records(path):
        if record.get("kind") != "generation-record":
            continue
        if generation is not None and record.get("generation") != int(generation):
            continue
        records.append(record)
    return records


def reconstruct(records):
    """Rebuild the family tree and run shape from raw records.

    Returns a dict with:
    - organisms: id -> {genome, parents, born, died, death_cause}
      (died is None for organisms alive in the final population)
    - generations: the generation records, in order
    - champion_id, verdict: from run_end / verdict records
    Raises ValueError on a structurally incomplete log: a death
    or birth that references an organism never born, a child
    whose parents were never born, or births with no matching
    death and no place in the final population.
    """
    organisms = {}
    generations = []
    final_population = None
    champion_id = None
    verdict = None

    for rec in records:
        kind = rec.get("kind")
        if kind == "birth":
            oid = rec["organism"]
            if oid in organisms:
                raise ValueError("organism born twice: %r" % oid)
            for parent in rec["parents"]:
                if parent not in organisms:
                    raise ValueError(
                        "organism %r has unborn parent %r"
                        % (oid, parent))
            organisms[oid] = {
                "genome": rec["genome"],
                "parents": list(rec["parents"]),
                "born": rec["generation"],
                "died": None,
                "death_cause": None,
            }
        elif kind == "death":
            oid = rec["organism"]
            if oid not in organisms:
                raise ValueError("death of unborn organism: %r" % oid)
            if organisms[oid]["died"] is not None:
                raise ValueError("organism died twice: %r" % oid)
            organisms[oid]["died"] = rec["generation"]
            organisms[oid]["death_cause"] = rec["cause"]
        elif kind == "generation":
            generations.append(rec)
        elif kind == "verdict":
            verdict = rec
        elif kind == "run_end":
            final_population = list(rec["final_population"])
            champion_id = rec["champion"]

    if final_population is None:
        raise ValueError("log has no run_end record")
    alive = set(final_population)
    for oid, org in organisms.items():
        if org["died"] is None and oid not in alive:
            raise ValueError(
                "organism %r neither died nor survived" % oid)
        if org["died"] is not None and oid in alive:
            raise ValueError(
                "organism %r is dead but in the final population"
                % oid)

    return {
        "organisms": organisms,
        "generations": generations,
        "final_population": final_population,
        "champion_id": champion_id,
        "verdict": verdict,
    }
