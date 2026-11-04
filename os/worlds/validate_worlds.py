"""os/worlds/validate_worlds.py: world data-file validator (Section A lane).

Validates every world file under os/worlds/ against its expected schema:

- every ``*/pack.json`` parses and satisfies the pack contract in
  ``validate_pack.py`` (imported from the same directory; stdlib only);
- every other ``*.json`` parses;
- every ``*.jsonl`` has only parseable non-blank lines;
- known entry/run records carry the fields the dashboard pages read
  (``surfaces.html`` + ``js/surfaces.js`` + ``runtime/board.py``):

  - ``custos/runs/*.jsonl``: each row an object with ``record_type``;
    ``observation`` rows carry ``tier``/``source``/``category``/``ts``;
  - ``officina/runs/*.json``: one of three shapes the board renders --
    run-001 (``rough_input``, ``brief``, ``rounds_used``,
    ``final_grade``, ``verification``), overnight (``artefact_class``,
    ``n_variants``, ``failures`` list, ``best``), best-design
    (``artefact_class``, ``best``, ``verification``);
  - ``musica/sessions/*/session.json``: ``session_id``, ``brief_id``;
    ``take_log.jsonl`` rows: ``take_id`` plus ``verdict`` keeper/reject;
    ``catalogue.json``: object (``tracks`` list when present);
    ``rights.json``: ``passed`` + ``rejected``;
  - ``science-lab/records/exports/board.json``: ``export_version``,
    ``cycles``, ``claims_by_level``; ``records/cycles/*.json``:
    ``cycle_id``; ``records/ledger.jsonl`` rows: ``kind``;
    ``records/repository/claims.jsonl``: ``claim_id`` + ``level``;
    ``cycles.jsonl``: ``cycle_id``; ``experiments.jsonl``:
    ``experiment_id``.

Usage: ``python3 os/worlds/validate_worlds.py`` from the repo root.
Exit 0 when clean; exit 1 with ``file:line: message`` failures.
"""

import glob
import json
import os
import sys

WORLDS_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, WORLDS_DIR)
try:
    import validate_pack
except ImportError:  # pragma: no cover - same-dir import always present
    validate_pack = None


def _fail(errors, path, message, line=1):
    errors.append("%s:%d: %s" % (path, line, message))


def _is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_pack(path, errors):
    try:
        with open(path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError) as exc:
        _fail(errors, path, "cannot parse pack.json: %s" % exc)
        return
    if validate_pack is None:
        for key in ("pack", "status", "watchers", "agents", "alerts"):
            if key not in manifest:
                _fail(errors, path, "pack missing required key: %s" % key)
        return
    for err in validate_pack.validate_pack(manifest):
        _fail(errors, path, "pack contract: %s" % err)
    dirname = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if isinstance(manifest, dict) and manifest.get("pack") != dirname:
        _fail(errors, path, "pack name %r does not match directory %r"
              % (manifest.get("pack"), dirname))


def check_custos_jsonl(path, errors):
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        _fail(errors, path, "cannot read: %s" % exc)
        return
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            _fail(errors, path, "bad JSON: %s" % exc, i)
            continue
        if not isinstance(row, dict):
            _fail(errors, path, "record is not an object", i)
            continue
        if not isinstance(row.get("record_type"), str):
            _fail(errors, path, "record missing string record_type", i)
            continue
        if row["record_type"] == "observation":
            for field in ("tier", "source", "category", "ts"):
                if not isinstance(row.get(field), str):
                    _fail(errors, path,
                          "observation missing string field: %s" % field, i)


def check_officina_run(path, errors):
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        _fail(errors, path, "cannot parse run file: %s" % exc)
        return
    if not isinstance(doc, dict):
        _fail(errors, path, "run file is not an object")
        return
    if isinstance(doc.get("n_variants"), int):
        for field in ("artefact_class", "n_variants", "failures", "best"):
            if field not in doc:
                _fail(errors, path,
                      "overnight run missing field: %s" % field)
        if "failures" in doc and not isinstance(doc["failures"], list):
            _fail(errors, path, "overnight run failures is not a list")
    elif "final_params" in doc or "rough_input" in doc:
        for field in ("rough_input", "brief", "rounds_used",
                      "final_grade", "verification"):
            if field not in doc:
                _fail(errors, path, "run-001 missing field: %s" % field)
        grade = doc.get("final_grade")
        if isinstance(grade, dict) and \
                not _is_num(grade.get("r_th_c_per_w")):
            _fail(errors, path, "final_grade.r_th_c_per_w is not a number")
        if isinstance(doc.get("brief"), dict) and \
                "artefact_class" not in doc["brief"]:
            _fail(errors, path, "brief missing artefact_class")
    elif "best" in doc:
        for field in ("artefact_class", "best", "verification"):
            if field not in doc:
                _fail(errors, path,
                      "best-design missing field: %s" % field)
    else:
        _fail(errors, path, "run file matches no known board shape "
              "(run-001 / overnight / best-design)")


def check_musica_session(session_dir, errors):
    session_path = os.path.join(session_dir, "session.json")
    try:
        with open(session_path, encoding="utf-8") as fh:
            session = json.load(fh)
    except (OSError, ValueError) as exc:
        _fail(errors, session_path, "cannot parse session.json: %s" % exc)
        session = None
    if session is not None:
        if not isinstance(session, dict):
            _fail(errors, session_path, "session.json is not an object")
        else:
            for field in ("session_id", "brief_id"):
                if field not in session:
                    _fail(errors, session_path,
                          "session.json missing field: %s" % field)
    log_path = os.path.join(session_dir, "take_log.jsonl")
    if os.path.exists(log_path):
        try:
            with open(log_path, encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError as exc:
            _fail(errors, log_path, "cannot read: %s" % exc)
            lines = []
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as exc:
                _fail(errors, log_path, "bad JSON: %s" % exc, i)
                continue
            if not isinstance(row, dict):
                _fail(errors, log_path, "take is not an object", i)
                continue
            if "take_id" not in row:
                _fail(errors, log_path, "take missing take_id", i)
            if row.get("verdict") not in ("keeper", "reject"):
                _fail(errors, log_path,
                      "take verdict is not keeper/reject: %r"
                      % (row.get("verdict"),), i)
    for name, required in (("catalogue.json", ()),
                           ("rights.json", ("passed", "rejected"))):
        fpath = os.path.join(session_dir, name)
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            _fail(errors, fpath, "cannot parse %s: %s" % (name, exc))
            continue
        if not isinstance(doc, dict):
            _fail(errors, fpath, "%s is not an object" % name)
            continue
        for field in required:
            if field not in doc:
                _fail(errors, fpath, "%s missing field: %s" % (name, field))
        if name == "catalogue.json" and "tracks" in doc \
                and not isinstance(doc["tracks"], list):
            _fail(errors, fpath, "catalogue tracks is not a list")


def check_science_lab(path, errors):
    rel = os.path.relpath(path, WORLDS_DIR)
    if path.endswith("records/exports/board.json"):
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            _fail(errors, path, "cannot parse board.json: %s" % exc)
            return
        for field in ("export_version", "cycles", "claims_by_level"):
            if not isinstance(doc, dict) or field not in doc:
                _fail(errors, path,
                      "board.json missing field: %s" % field)
        return
    if "/records/cycles/" in rel and path.endswith(".json"):
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            _fail(errors, path, "cannot parse cycle record: %s" % exc)
            return
        if not isinstance(doc, dict) or "cycle_id" not in doc:
            _fail(errors, path, "cycle record missing cycle_id")
        return
    if path.endswith(".jsonl"):
        name = os.path.basename(path)
        required = {"ledger.jsonl": ("kind",),
                    "calls.jsonl": ("kind",),
                    "mcp_smoke_calls.jsonl": ("kind",),
                    "claims.jsonl": ("claim_id", "level"),
                    "cycles.jsonl": ("cycle_id",),
                    "experiments.jsonl": ("experiment_id",)}.get(name, ())
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError as exc:
            _fail(errors, path, "cannot read: %s" % exc)
            return
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as exc:
                _fail(errors, path, "bad JSON: %s" % exc, i)
                continue
            if not isinstance(row, dict):
                _fail(errors, path, "record is not an object", i)
                continue
            for field in required:
                if field not in row:
                    _fail(errors, path,
                          "record missing field: %s" % field, i)


def main():
    errors = []
    n_json = 0
    n_jsonl = 0
    n_session_files = 0
    json_files = sorted(glob.glob(
        os.path.join(WORLDS_DIR, "**", "*.json"), recursive=True))
    jsonl_files = sorted(glob.glob(
        os.path.join(WORLDS_DIR, "**", "*.jsonl"), recursive=True))
    for path in json_files:
        rel = os.path.relpath(path, WORLDS_DIR)
        parts = rel.split(os.sep)
        if len(parts) == 2 and parts[1] == "pack.json":
            check_pack(path, errors)
            n_json += 1
        elif (len(parts) >= 3 and parts[0] == "officina"
                and parts[1] == "runs"):
            check_officina_run(path, errors)
            n_json += 1
        elif parts[0] == "science-lab" and (
                "records/exports/board.json" in rel
                or "/records/cycles/" in rel):
            check_science_lab(path, errors)
            n_json += 1
        elif parts[0] == "musica" and parts[1] == "sessions" and len(
                parts) == 4 and parts[3] in (
                    "session.json", "catalogue.json", "rights.json"):
            n_session_files += 1  # checked per-session below
        else:
            try:
                with open(path, encoding="utf-8") as fh:
                    json.load(fh)
            except (OSError, ValueError) as exc:
                _fail(errors, path, "cannot parse JSON: %s" % exc)
            n_json += 1
    for path in jsonl_files:
        rel = os.path.relpath(path, WORLDS_DIR)
        parts = rel.split(os.sep)
        if len(parts) >= 3 and parts[0] == "custos" and parts[1] == "runs":
            check_custos_jsonl(path, errors)
            n_jsonl += 1
        elif parts[0] == "science-lab" and "/records/" in rel:
            check_science_lab(path, errors)
            n_jsonl += 1
        else:
            try:
                with open(path, encoding="utf-8") as fh:
                    lines = fh.readlines()
            except OSError as exc:
                _fail(errors, path, "cannot read: %s" % exc)
                continue
            for i, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except ValueError as exc:
                    _fail(errors, path, "bad JSON: %s" % exc, i)
            n_jsonl += 1
    sessions = sorted(glob.glob(
        os.path.join(WORLDS_DIR, "musica", "sessions", "*")))
    n_sessions = 0
    for session_dir in sessions:
        if not os.path.isdir(session_dir):
            continue
        if not os.path.exists(os.path.join(session_dir, "session.json")):
            continue
        check_musica_session(session_dir, errors)
        n_sessions += 1
    total = n_json + n_jsonl + n_session_files
    if errors:
        for err in errors:
            print(err)
        print("validate_worlds: FAIL %d error(s) in %d files "
              "(%d json, %d jsonl, %d musica session files, %d sessions)"
              % (len(errors), total, n_json, n_jsonl,
                 n_session_files, n_sessions))
        return 1
    print("validate_worlds: OK %d files "
          "(%d json, %d jsonl, %d musica session files in %d sessions, "
          "%d packs)"
          % (total, n_json, n_jsonl, n_session_files, n_sessions,
             len(glob.glob(os.path.join(WORLDS_DIR, "*", "pack.json")))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
