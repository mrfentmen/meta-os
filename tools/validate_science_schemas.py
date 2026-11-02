"""Validate the five Science Lab schemas and their cross-file contracts.

Reads every schema as data; never edits one. Two contracts are checked
against the Python modules that consume them:

  * ``cycle.schema.json``'s ``phase`` enum must equal ``cycle.ALL_PHASES``
    (PHASES + STEP_8 + HUMAN_GATES), read from ``cycle.py`` as source text.
  * every field in ``hypothesis.schema.json``'s ``required`` list must be
    a field the parser in ``reasoning.py`` actually reads.

Exit code 0 when no findings, 1 otherwise. Findings name the file and the
field; the JSON schema engine itself is out of scope (this is a shape and
drift check, not a full validator).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "os" / "worlds" / "science-lab" / "schemas"
LAB_DIR = ROOT / "os" / "worlds" / "science-lab"

TOP_LEVEL_KEYS = ("$schema", "$id", "type", "properties")
SCHEMA_FILES = (
    "source.schema.json",
    "repository.schema.json",
    "cycle.schema.json",
    "hypothesis.schema.json",
    "experiment.schema.json",
)


def load_schemas(directory: Path | str = SCHEMA_DIR) -> dict[str, dict]:
    """Load every schema by filename; a parse failure is raised, not skipped."""
    directory = Path(directory)
    loaded: dict[str, dict] = {}
    for name in SCHEMA_FILES:
        loaded[name] = json.loads((directory / name).read_text(encoding="utf-8"))
    return loaded


def check_schema(name: str, doc: dict) -> list[str]:
    """Return findings for one schema's documented top-level shape."""
    findings: list[str] = []
    if not isinstance(doc, dict):
        return [f"{name}: schema is not an object"]
    for key in TOP_LEVEL_KEYS:
        if key not in doc:
            findings.append(f"{name}: missing top-level key {key!r}")
    if doc.get("type") != "object":
        findings.append(f"{name}: top-level type must be 'object'")
    if not isinstance(doc.get("properties"), dict) or not doc.get("properties"):
        findings.append(f"{name}: properties must be a non-empty object")
    required = doc.get("required")
    if required is not None and not isinstance(required, list):
        findings.append(f"{name}: required must be an array")
    return findings


def _python_phases(lab_dir: Path) -> set[str]:
    text = (lab_dir / "cycle.py").read_text(encoding="utf-8")
    block = re.search(r"^PHASES\s*=\s*\[(.*?)\]", text, re.M | re.S)
    if not block:
        raise ValueError("cycle.py: PHASES list not found")
    phases = set(re.findall(r"[\"']([^\"']+)[\"']", block.group(1)))
    step8 = re.search(r"^STEP_8\s*=\s*[\"']([^\"']+)[\"']", text, re.M)
    if not step8:
        raise ValueError("cycle.py: STEP_8 not found")
    gates = re.search(r"^HUMAN_GATES\s*=\s*\((.*?)\)", text, re.M | re.S)
    if not gates:
        raise ValueError("cycle.py: HUMAN_GATES not found")
    phases.add(step8.group(1))
    phases.update(re.findall(r"[\"']([^\"']+)[\"']", gates.group(1)))
    return phases


def check_cycle_enum(schemas: dict[str, dict], lab_dir: Path | str = LAB_DIR) -> list[str]:
    """The schema enum and cycle.ALL_PHASES must agree exactly."""
    lab_dir = Path(lab_dir)
    enum = schemas["cycle.schema.json"]["properties"]["phase"]["enum"]
    from_python = _python_phases(lab_dir)
    from_schema = set(enum)
    findings = []
    for missing in sorted(from_python - from_schema):
        findings.append(f"cycle.schema.json: phase {missing!r} is in cycle.py but not the enum")
    for extra in sorted(from_schema - from_python):
        findings.append(f"cycle.schema.json: phase {extra!r} is in the enum but not cycle.py")
    return findings


def check_hypothesis_required(schemas: dict[str, dict], lab_dir: Path | str = LAB_DIR) -> list[str]:
    """Every schema-required hypothesis field must appear in the parser source."""
    lab_dir = Path(lab_dir)
    source = (lab_dir / "reasoning.py").read_text(encoding="utf-8")
    parser = source.split("def parse_hypothesis", 1)
    if len(parser) != 2:
        return ["reasoning.py: parse_hypothesis not found"]
    body = parser[1].split("\ndef ", 1)[0]
    findings = []
    for field in schemas["hypothesis.schema.json"]["required"]:
        if f'"{field}"' not in body and f"'{field}'" not in body:
            findings.append(
                f"hypothesis.schema.json: required field {field!r} is never read by parse_hypothesis"
            )
    return findings


def check_all(
    schema_dir: Path | str = SCHEMA_DIR, lab_dir: Path | str = LAB_DIR
) -> list[str]:
    """All shape and drift findings for the real tree."""
    schemas = load_schemas(schema_dir)
    findings: list[str] = []
    for name, doc in schemas.items():
        findings.extend(check_schema(name, doc))
    findings.extend(check_cycle_enum(schemas, lab_dir))
    findings.extend(check_hypothesis_required(schemas, lab_dir))
    return findings


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    schema_dir = Path(argv[0]) if argv else SCHEMA_DIR
    lab_dir = Path(argv[1]) if len(argv) > 1 else LAB_DIR
    findings = check_all(schema_dir, lab_dir)
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
