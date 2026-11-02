"""Computational Lab execution layer (Section 4: tasks 31-40).

Clean-room command execution, determinism checks, department runners,
sandbox refusals, failure records, prereg comparison, compute budget,
and re-execution from archived records. Stdlib only.

Task map:
  31 run_experiment(): clean temp dir (tempfile.mkdtemp), capture
     stdout/exit, return a schemas/experiment.schema.json-shaped record.
  32 rerun_same(): run a plan twice; identical output_hash or record
     the difference and cap the claim.
  33 run_bio/run_chem/run_physics/run_materials: one small real,
     deterministic computation each (GC-content / exact mol wt from a
     formula (plus an honest CSV-statistic mode for the Delaney prep) /
     projectile range / rule-of-mixtures density). Same record schema.
  34 assert_sandbox_clean(): reject plans touching paths outside the temp
     dir or the network ('..', '/etc', '/Users', absolute paths,
     http/socket/curl-style tokens) with a loud PermissionError.
  35 Crash records: a nonzero exit (or timeout) is filed as a result
     carrying exit_code + stderr tail, output_hash null. Never retried.
  36 compare_to_prereg()/write_result(): outcome vs pre-registered
     prediction -> match / no-match / indeterminate. No adjectives.
  37 check_compute_budget()/write_stop_receipt(): wall-clock + call caps
     via lab_config; receipt on stop.
  38 reproduce_from_record(): re-run from archived inputs (hashes + seed)
     -> comparison record.
  40 Worked example: records/examples/computation_example.json (chem
     dept runner over the first 10 Delaney rows; gate NOT passed).

Sibling layers (imported, never reimplemented): ledger (append-only
log), ladder (evidence caps), lab_config (budget caps). literature.py
and reasoning.py are read-only territory: imported only where needed
(not at all here).
"""

import csv
import hashlib
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

try:
    from .ledger import append_record as _ledger_append
except ImportError:
    try:
        from ledger import append_record as _ledger_append
    except ImportError:
        _ledger_append = None

try:
    from .ladder import cap_for_experiment as _ladder_cap
except ImportError:
    try:
        from ladder import cap_for_experiment as _ladder_cap
    except ImportError:
        _ladder_cap = None

try:
    from . import lab_config as _lab_config_mod
except ImportError:
    try:
        import lab_config as _lab_config_mod
    except ImportError:
        _lab_config_mod = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#: Tokens that must never appear in a plan handed to the clean room.
#: The check scans the command plus every string in the plan inputs.
SANDBOX_FORBIDDEN = (
    "..",
    "/etc",
    "/Users",
    "/private",
    "/var/",
    "/root",
    "/home/",
    "http://",
    "https://",
    "ftp://",
    "ssh://",
    "socket",
    "urllib",
    "urlopen",
    "http.client",
    "requests",
    "curl",
    "wget",
)

#: Any absolute POSIX path token (e.g. /tmp/x, /opt/y) is outside the
#: temp dir by definition, so it is refused even when it names none of
#: the forbidden prefixes above. Relative tokens such as a/b or
#: 10.1021/ci034243x do not match (the slash must start the token).
_ABSOLUTE_PATH_RE = re.compile(r"(?:^|[\s\"\'(=,;])/[\w.~][\w.~\-/]*")

_MONOISOTOPIC = {
    "H": 1.00782503223, "He": 4.00260325413, "Li": 7.0160034366,
    "Be": 9.012183065, "B": 11.00930536, "C": 12.0,
    "N": 14.00307400443, "O": 15.99491461957, "F": 18.99840316273,
    "Na": 22.9897692809, "Mg": 23.985041697, "Al": 26.98153853,
    "Si": 27.97692653465, "P": 30.9737619985, "S": 31.9720711744,
    "Cl": 34.968852682, "K": 38.9637074864, "Ca": 39.962590983,
    "Fe": 55.93493633, "Cu": 62.92959772, "Zn": 63.92914222,
    "Br": 78.9183376, "I": 126.9044719,
}

_FORMULA_RE = re.compile(r"([A-Z][a-z]?)(\d*)")


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _new_id(prefix="exp"):
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])


def _tail(text, limit=2000):
    """Last `limit` chars of text (bounded log tails)."""
    if not text:
        return ""
    text = str(text)
    return text[-limit:] if len(text) > limit else text


# ------------------------------------------------------------------
# Task 34: sandbox
# ------------------------------------------------------------------

def _sandbox_scan_text(text):
    """Return the offending token in text, or None when clean."""
    if not isinstance(text, str):
        return None
    lowered = text.lower()
    for token in SANDBOX_FORBIDDEN:
        if token.lower() in lowered:
            return token
    match = _ABSOLUTE_PATH_RE.search(text)
    if match:
        return match.group(0).strip()[:64]
    return None


def _iter_plan_strings(plan, _depth=0):
    """Yield every string held anywhere inside a plan dict/list."""
    if _depth > 8:
        return
    if isinstance(plan, str):
        yield plan
    elif isinstance(plan, dict):
        for key, value in plan.items():
            if isinstance(key, str):
                yield key
            for found in _iter_plan_strings(value, _depth + 1):
                yield found
    elif isinstance(plan, (list, tuple)):
        for item in plan:
            for found in _iter_plan_strings(item, _depth + 1):
                yield found


def assert_sandbox_clean(plan):
    """Refuse a plan that reaches outside the clean temp dir.

    Scans the command plus every string in the plan inputs for '..',
    '/etc', '/Users', other absolute paths, and network tokens.
    Raises PermissionError naming the token -- loudly, never silently.
    Returns None when the plan is clean.
    """
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dict, got %r"
                        % type(plan).__name__)
    command = plan.get("command")
    texts = []
    if isinstance(command, str):
        texts.append(("command", command))
    elif isinstance(command, (list, tuple)):
        texts.append(("command", " ".join(str(c) for c in command)))
    for chunk in _iter_plan_strings(
            {k: v for k, v in plan.items() if k != "command"}):
        texts.append(("plan input", chunk))
    for origin, text in texts:
        hit = _sandbox_scan_text(text)
        if hit is not None:
            raise PermissionError(
                "SANDBOX REFUSAL: %s contains forbidden token %r: "
                "plans run in a clean temp dir and must not touch "
                "paths outside it (%s, absolute paths) or the "
                "network (http/socket/curl-style tokens). "
                "Refusing to run." % (origin, hit, "/etc, /Users, .."))
    return None


# ------------------------------------------------------------------
# Shared record builder (Task 31 schema shape)
# ------------------------------------------------------------------

_REQUIRED_RECORD_KEYS = (
    "id", "research_question", "hypothesis_id", "hypothesis_version",
    "original_data", "data_source", "software", "model", "parameters",
    "random_seed", "input_hash", "output_hash", "execution_logs",
    "verification_status", "is_prediction", "evidence_level",
)


def _cap_level(verification_status, requested):
    """Cap a requested level by verification status (ladder rule)."""
    try:
        cap = _ladder_cap(verification_status)
    except Exception:
        cap = None
    if cap is None:
        cap = 2 if str(verification_status) in ("unverified", "mismatch") else 3
    try:
        level = int(requested)
    except (TypeError, ValueError):
        level = cap
    return max(0, min(level, cap, 3))


def _build_record(plan, output_text, exit_code, elapsed_s,
                  execution_logs, crashed):
    """Assemble the schema-shaped record. output_text None on crash."""
    seed = plan.get("seed", plan.get("random_seed"))
    if seed is not None and not isinstance(seed, int):
        try:
            seed = int(seed)
        except (TypeError, ValueError):
            seed = None
    if crashed:
        output_hash = None
        requested = plan.get("evidence_level", 0)
    else:
        output_hash = _sha256_text(output_text or "")
        requested = plan.get("evidence_level", 2)
    software = plan.get("software") or {
        "name": "science-lab-compute", "version": platform.python_version()}
    model = plan.get("model") or {"name": "none", "version": "none"}
    record = {
        "id": plan.get("id") or _new_id(),
        "research_question": str(plan.get("research_question")
                                 or plan.get("question")
                                 or "Unlabelled computation"),
        "hypothesis_id": str(plan.get("hypothesis_id") or "H-UNLINKED"),
        "hypothesis_version": str(plan.get("hypothesis_version") or "v0"),
        "original_data": str(plan.get("original_data") or "none-archived"),
        "data_source": str(plan.get("data_source") or "local inputs"),
        "software": {"name": str(software.get("name") or "unknown"),
                     "version": str(software.get("version") or "unknown")},
        "model": {"name": str(model.get("name") or "none"),
                  "version": str(model.get("version") or "none")},
        "parameters": plan.get("parameters") if isinstance(
            plan.get("parameters"), dict) else {},
        "random_seed": seed,
        "input_hash": _sha256_text(_canonical({
            "code_hash": plan.get("code_hash"),
            "data_hash": plan.get("data_hash"),
            "seed": seed,
            "command": plan.get("command"),
            "parameters": plan.get("parameters"),
        }).decode("utf-8")),
        "output_hash": output_hash,
        "execution_logs": list(execution_logs),
        "verification_status": "unverified",
        "is_prediction": bool(plan.get("is_prediction", False)),
        "evidence_level": _cap_level("unverified", requested),
        "exit_code": exit_code,
        "elapsed_s": elapsed_s,
    }
    return record


def validate_record_shape(record):
    """Check a record carries every schema-required key with sane types.

    Returns (ok: bool, msg: str). Never raises for a bad record.
    """
    if not isinstance(record, dict):
        return (False, "not a record dict: %r" % type(record).__name__)
    missing = [k for k in _REQUIRED_RECORD_KEYS if k not in record]
    if missing:
        return (False, "missing required keys: %r" % (missing,))
    if record.get("verification_status") == "unverified" \
            and isinstance(record.get("evidence_level"), int) \
            and record["evidence_level"] > 2:
        return (False, "unverified record carries evidence_level %r (> 2)"
                % (record["evidence_level"],))
    if isinstance(record.get("evidence_level"), int) \
            and not 0 <= record["evidence_level"] <= 3:
        return (False, "evidence_level out of range: %r"
                % (record["evidence_level"],))
    if not isinstance(record.get("execution_logs"), list):
        return (False, "execution_logs must be a list")
    return (True, "ok: schema-required keys present, level cap holds")


# ------------------------------------------------------------------
# Task 31: run an experiment plan in a clean temp dir
# ------------------------------------------------------------------

def run_experiment(plan, timeout=30, ledger_path=None):
    """Execute plan['command'] in a fresh temp dir; return the record.

    plan carries code_hash, data_hash, seed, command plus the
    schema-facing metadata (research_question, hypothesis_id/version,
    original_data, data_source, software, model, parameters,
    is_prediction). stdout is hashed to output_hash; a nonzero exit
    (or timeout) files output_hash null with exit_code + stderr tail
    (Task 35) and is never retried. verification_status is always
    'unverified' here; evidence_level is capped at 2.
    """
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dict, got %r"
                        % type(plan).__name__)
    command = plan.get("command")
    if not command:
        raise ValueError("plan carries no 'command'; nothing to run")
    assert_sandbox_clean(plan)
    seed = plan.get("seed", plan.get("random_seed"))

    tmpdir = tempfile.mkdtemp(prefix="scilab-exp-")
    env = dict(os.environ)
    if isinstance(seed, int) and not isinstance(seed, bool):
        env["EXPERIMENT_SEED"] = str(seed)
        try:
            env["PYTHONHASHSEED"] = str(seed % 4294967296)
        except Exception:
            pass
    start = time.time()
    timed_out = False
    try:
        if isinstance(command, str):
            completed = subprocess.run(
                command, shell=True, cwd=tmpdir, capture_output=True,
                text=True, timeout=timeout, env=env)
        else:
            completed = subprocess.run(
                [str(c) for c in command], shell=False, cwd=tmpdir,
                capture_output=True, text=True, timeout=timeout, env=env)
        exit_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = (exc.stdout or "") if isinstance(
            getattr(exc, "stdout", ""), str) else ""
        stderr = (exc.stderr or "") if isinstance(
            getattr(exc, "stderr", ""), str) else ""
    elapsed = time.time() - start
    crashed = timed_out or (exit_code != 0)

    logs = [
        "command: %s" % (command if isinstance(command, str)
                         else " ".join(str(c) for c in command)),
        "tmpdir: scilab-exp-* (fresh mkdtemp, removed after run)",
        "exit_code: %s" % (exit_code,),
        "elapsed_s: %.3f" % (elapsed,),
        "timed_out: %s" % (timed_out,),
        "stdout_tail: %s" % (_tail(stdout) or "<empty>",),
    ]
    if crashed:
        logs.append("stderr_tail: %s" % (_tail(stderr) or "<empty>",))
        logs.append("note: run crashed (nonzero exit or timeout); "
                    "output_hash null; filed as a result, not retried.")
    else:
        if stderr.strip():
            logs.append("stderr_tail: %s" % _tail(stderr))

    record = _build_record(plan, stdout, exit_code, elapsed, logs, crashed)
    record["parameters"] = dict(record["parameters"])
    record["parameters"].setdefault("_command", command)
    record["parameters"].setdefault("_code_hash", plan.get("code_hash"))
    record["parameters"].setdefault("_data_hash", plan.get("data_hash"))
    if timed_out:
        record["parameters"]["_timed_out"] = True
    if ledger_path is not None:
        file_experiment_record(record, ledger_path,
                               agent=plan.get("agent",
                                              "computational-scientist"))
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass
    return record


# ------------------------------------------------------------------
# Task 32: determinism check
# ------------------------------------------------------------------

def rerun_same(plan, timeout=30):
    """Run plan twice; return {deterministic, hashes, records, ...}.

    deterministic True iff both output_hash values are identical and
    non-null. A difference is recorded (both hashes kept) and the
    claim is capped: nondeterministic runs support no claim above
    level 1 pending a seeded rerun.
    """
    first = run_experiment(plan, timeout=timeout)
    second = run_experiment(plan, timeout=timeout)
    hashes = [first.get("output_hash"), second.get("output_hash")]
    deterministic = (hashes[0] is not None and hashes[0] == hashes[1])
    return {
        "deterministic": deterministic,
        "hashes": hashes,
        "records": [first, second],
        "claim_cap": 2 if deterministic else 1,
        "note": ("identical output_hash across 2 runs; record cap 2 "
                 "(unverified)" if deterministic
                 else "output_hash differs across 2 runs (%r vs %r); "
                 "claim capped at 1 pending a seeded rerun"
                 % (hashes[0], hashes[1])),
    }


# ------------------------------------------------------------------
# Task 33: department runners (small, real, deterministic)
# ------------------------------------------------------------------

def _dept_record(dept, question, params, output_text, value,
                 plan, original_data, data_source):
    """Build the schema-shaped record for a department computation."""
    merged = dict(plan or {})
    merged.setdefault("research_question", question)
    merged.setdefault("original_data", original_data)
    merged.setdefault("data_source", data_source)
    merged.setdefault("software", {"name": "science-lab-compute",
                                  "version": platform.python_version()})
    parameters = dict(params)
    parameters["_dept"] = dept
    merged["parameters"] = parameters
    logs = [
        "dept: %s" % (dept,),
        "computation: deterministic, in-process, stdlib only",
        "output: %s" % (output_text,),
    ]
    record = _build_record(merged, output_text, 0, 0.0, logs, False)
    record["elapsed_s"] = 0.0
    record["value"] = value
    return record


def run_bio(plan=None, **kwargs):
    """GC-content of a DNA sequence. plan/keys: sequence (required)."""
    merged = dict(plan or {})
    merged.update(kwargs)
    seq = merged.get("sequence", merged.get("input"))
    if not seq or not isinstance(seq, str):
        raise ValueError("run_bio requires a 'sequence' string")
    assert_sandbox_clean({"sequence": seq})
    seq = seq.strip().upper().replace(" ", "")
    bad = sorted({c for c in seq} - set("ACGTNU"))
    if bad:
        raise ValueError("run_bio: invalid bases %r in sequence" % (bad,))
    if not seq:
        raise ValueError("run_bio: empty sequence")
    gc = sum(1 for c in seq if c in "GC")
    frac = gc / len(seq)
    text = "GC-content %.6f (%d/%d)" % (frac, gc, len(seq))
    return _dept_record(
        "bio", merged.get("research_question")
        or "What is the GC-content of the given sequence?",
        {"sequence": seq, "length": len(seq),
         "gc_count": gc, "gc_fraction": frac},
        text, frac, merged,
        original_data=merged.get("original_data") or "input sequence",
        data_source=merged.get("data_source") or "caller-supplied sequence")


def _parse_formula(formula):
    """Parse a molecular formula into [(element, count)]."""
    if not formula or not isinstance(formula, str):
        raise ValueError("formula must be a non-empty string")
    body = formula.strip().replace(" ", "")
    if not re.fullmatch(r"([A-Z][a-z]?\d+|[A-Z][a-z]?)+", body or ""):
        raise ValueError("run_chem: malformed formula %r" % (formula,))
    parts = _FORMULA_RE.findall(body)
    if not parts or "".join(e + n for e, n in parts) != body:
        raise ValueError("run_chem: malformed formula %r" % (formula,))
    out = []
    for element, count in parts:
        if element not in _MONOISOTOPIC:
            raise ValueError(
                "run_chem: unknown element %r in formula %r "
                "(supported: %s)" % (element, formula,
                                     ", ".join(sorted(_MONOISOTOPIC))))
        out.append((element, int(count) if count else 1))
    return out


def _resolve_lab_relative(path):
    """Resolve a repo-relative path against the science-lab directory."""
    candidate = os.path.normpath(os.path.join(BASE_DIR, path))
    if not os.path.exists(candidate):
        raise ValueError("dataset not found: %r (resolved %r)"
                         % (path, candidate))
    return candidate


def rmse(actual, predicted):
    """Root-mean-square error; refuses empty or mismatched series."""
    actual = list(actual)
    predicted = list(predicted)
    if not actual or not predicted:
        raise ValueError("rmse requires non-empty series")
    if len(actual) != len(predicted):
        raise ValueError(
            "rmse requires equal-length series, got %d and %d"
            % (len(actual), len(predicted)))
    total = 0.0
    for a, p in zip(actual, predicted):
        diff = float(a) - float(p)
        total += diff * diff
    return math.sqrt(total / len(actual))


def summary_stats(values):
    """Count, mean, population variance, and standard deviation."""
    values = [float(v) for v in values]
    if not values:
        raise ValueError("summary_stats requires non-empty values")
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "variance": statistics.pvariance(values),
        "stddev": statistics.pstdev(values),
    }


def parse_numeric_rows(rows, column):
    """Parse one column into ordered (index, value) pairs.

    Non-numeric or missing cells are reported by row index, never
    silently replaced.
    """
    if not isinstance(rows, (list, tuple)):
        raise TypeError("rows must be a list")
    if not isinstance(column, str) or not column:
        raise ValueError("parse_numeric_rows requires a column name")
    pairs = []
    bad_rows = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            bad_rows.append(index)
            continue
        cell = row.get(column)
        if cell is None or (isinstance(cell, str) and not cell.strip()):
            bad_rows.append(index)
            continue
        try:
            pairs.append({"index": index, "value": float(cell)})
        except (TypeError, ValueError):
            bad_rows.append(index)
    return {"rows": pairs, "bad_rows": bad_rows}


def run_chem(plan=None, **kwargs):
    """Exact monoisotopic mass from a formula, or an honest CSV statistic.

    Formula mode: plan carries {"formula": "H2O"}.
    Dataset mode: plan carries {"dataset": <lab-relative csv path>,
    "column": <header name>, "n_rows": 10, "statistic": "mean"}.
    Rows mode: plan carries {"rows": [...], "target_column": ...,
    "prediction_column": ...} and returns the RMSE over those rows.
    """
    merged = dict(plan or {})
    merged.update(kwargs)
    if merged.get("rows") is not None:
        return _run_chem_rows(merged)
    if "dataset" in merged and merged["dataset"]:
        return _run_chem_dataset(merged)
    formula = merged.get("formula")
    if not formula:
        raise ValueError("run_chem requires 'formula' or 'dataset'")
    assert_sandbox_clean({"formula": formula})
    parts = _parse_formula(formula)
    mass = sum(_MONOISOTOPIC[el] * n for el, n in parts)
    text = "exact mass of %s = %.6f Da" % (formula.strip(), mass)
    return _dept_record(
        "chem", merged.get("research_question")
        or "What is the exact molecular mass of %s?" % (formula.strip(),),
        {"formula": formula.strip(),
         "composition": [{"element": el, "count": n} for el, n in parts],
         "exact_mass_da": mass},
        text, mass, merged,
        original_data=merged.get("original_data") or "formula %s"
        % (formula.strip(),),
        data_source=merged.get("data_source")
        or "monoisotopic masses (IUPAC)")


def _run_chem_rows(merged):
    rows = merged.get("rows")
    target = merged.get("target_column")
    prediction = merged.get("prediction_column")
    if not isinstance(rows, (list, tuple)):
        raise ValueError("run_chem rows mode requires a list of rows")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("run_chem rows mode requires target_column")
    if not isinstance(prediction, str) or not prediction.strip():
        raise ValueError("run_chem rows mode requires prediction_column")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("run_chem row %d is not an object" % index)
        if target not in row:
            raise ValueError(
                "run_chem target column %r missing at row %d"
                % (target, index))
        if prediction not in row:
            raise ValueError(
                "run_chem prediction column %r missing at row %d"
                % (prediction, index))
    actual = parse_numeric_rows(rows, target)
    predicted = parse_numeric_rows(rows, prediction)
    bad = sorted(set(actual["bad_rows"] + predicted["bad_rows"]))
    if bad:
        raise ValueError(
            "run_chem non-numeric cell at row(s) %s" % (bad,))
    actual_values = [p["value"] for p in actual["rows"]]
    predicted_values = [p["value"] for p in predicted["rows"]]
    result = rmse(actual_values, predicted_values)
    text = "rmse(%r vs %r, %d rows) = %r" % (
        target, prediction, len(actual_values), result)
    return _dept_record(
        "chem", merged.get("research_question")
        or "How closely do predictions track the target over %d rows?"
        % len(rows),
        {"target_column": target, "prediction_column": prediction,
         "rows_used": len(rows), "rmse": result},
        text, result, merged,
        original_data=merged.get("original_data")
        or "in-memory fixture rows (%d)" % len(rows),
        data_source=merged.get("data_source") or "caller-supplied fixture rows")


def _run_chem_dataset(merged):
    dataset = merged["dataset"]
    if not isinstance(dataset, str):
        raise ValueError("dataset must be a path string")
    assert_sandbox_clean({"dataset": dataset})
    column = merged.get("column")
    n_rows = merged.get("n_rows", 10)
    statistic = merged.get("statistic", "mean")
    try:
        n_rows = int(n_rows)
    except (TypeError, ValueError):
        raise ValueError("n_rows must be an int, got %r" % (n_rows,))
    if n_rows <= 0:
        raise ValueError("n_rows must be positive, got %r" % (n_rows,))
    path = _resolve_lab_relative(dataset)
    with open(path, "rb") as fh:
        file_sha256 = hashlib.sha256(fh.read()).hexdigest()
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        if column is None:
            raise ValueError(
                "no 'column' given; CSV header is %r" % (header,))
        if column not in header:
            raise ValueError(
                "column %r not in CSV header %r" % (column, header))
        values = []
        bad_rows = []
        for i, row in enumerate(reader):
            if i >= n_rows:
                break
            cell = (row.get(column) or "").strip()
            try:
                values.append(float(cell))
            except ValueError:
                bad_rows.append(i)
    if not values:
        raise ValueError("no numeric values under column %r in first %d "
                         "rows" % (column, n_rows))
    if statistic == "mean":
        result = statistics.mean(values)
    elif statistic == "min":
        result = min(values)
    elif statistic == "max":
        result = max(values)
    elif statistic == "sum":
        result = sum(values)
    else:
        raise ValueError("unknown statistic %r (mean/min/max/sum)"
                         % (statistic,))
    text = "%s(%r, first %d rows) = %r" % (statistic, column,
                                          len(values), result)
    record = _dept_record(
        "chem", merged.get("research_question")
        or "What is the %s of %r over the first %d archived rows?"
        % (statistic, column, len(values)),
        {"dataset": dataset, "column": column, "n_rows": n_rows,
         "statistic": statistic, "rows_used": len(values),
         "bad_rows_excluded": bad_rows, "file_sha256": file_sha256,
         "header": header, "values": values, "result": result},
        text, result, merged,
        original_data=merged.get("original_data")
        or "archived file %s (sha256 %s, first %d rows)"
        % (dataset, file_sha256[:12], len(values)),
        data_source=merged.get("data_source")
        or "archived file %s, column %r" % (dataset, column))
    return record


def run_physics(plan=None, **kwargs):
    """Projectile range R = v0^2 * sin(2*theta) / g (no drag)."""
    merged = dict(plan or {})
    merged.update(kwargs)
    for key in ("v0", "angle_deg"):
        if merged.get(key) is None:
            raise ValueError("run_physics requires 'v0' and 'angle_deg'")
    try:
        v0 = float(merged["v0"])
        angle = float(merged["angle_deg"])
        g = float(merged.get("g", 9.81))
    except (TypeError, ValueError):
        raise ValueError("run_physics: v0/angle_deg/g must be numbers")
    if g <= 0:
        raise ValueError("run_physics: g must be positive")
    assert_sandbox_clean({"v0": str(v0), "angle_deg": str(angle)})
    span = v0 ** 2 * math.sin(2 * math.radians(angle)) / g
    text = "range(v0=%r, angle=%r deg, g=%r) = %.6f m" % (v0, angle, g, span)
    return _dept_record(
        "physics", merged.get("research_question")
        or "What is the drag-free projectile range?",
        {"v0": v0, "angle_deg": angle, "g": g, "range_m": span},
        text, span, merged,
        original_data=merged.get("original_data") or "launch parameters",
        data_source=merged.get("data_source") or "caller-supplied inputs")


def run_materials(plan=None, **kwargs):
    """Rule-of-mixtures density rho = sum(f_i * rho_i)."""
    merged = dict(plan or {})
    merged.update(kwargs)
    fractions = merged.get("fractions")
    densities = merged.get("densities")
    if fractions is None or densities is None:
        raise ValueError("run_materials requires 'fractions' and "
                         "'densities' lists")
    fractions = list(fractions)
    densities = list(densities)
    if len(fractions) != len(densities) or not fractions:
        raise ValueError("run_materials: fractions and densities must be "
                         "non-empty lists of equal length")
    try:
        fractions = [float(f) for f in fractions]
        densities = [float(d) for d in densities]
    except (TypeError, ValueError):
        raise ValueError("run_materials: fractions/densities must be numbers")
    if any(f < 0 for f in fractions):
        raise ValueError("run_materials: fractions must be non-negative")
    if any(d <= 0 for d in densities):
        raise ValueError("run_materials: densities must be positive")
    if abs(sum(fractions) - 1.0) > 1e-6:
        raise ValueError("run_materials: fractions sum to %r, not 1"
                         % (sum(fractions),))
    rho = sum(f * d for f, d in zip(fractions, densities))
    text = "rule-of-mixtures density = %.6f" % (rho,)
    return _dept_record(
        "materials", merged.get("research_question")
        or "What is the rule-of-mixtures density?",
        {"fractions": fractions, "densities": densities,
         "density": rho},
        text, rho, merged,
        original_data=merged.get("original_data") or "phase fractions",
        data_source=merged.get("data_source") or "caller-supplied inputs")


# ------------------------------------------------------------------
# Task 35 helpers + filing
# ------------------------------------------------------------------

def file_experiment_record(record, ledger_path, agent="computational-scientist"):
    """File a record to the ledger. Returns the filed entry."""
    if _ledger_append is None:
        raise NotImplementedError(
            "UNIMPLEMENTED: ledger module unavailable; cannot file.")
    ok, msg = validate_record_shape(record)
    if not ok:
        raise ValueError("refused: record not schema-shaped (%s)" % (msg,))
    entry = dict(record)
    entry.setdefault("kind", "experiment-result")
    entry["agent"] = agent
    return _ledger_append(str(ledger_path), entry)


# ------------------------------------------------------------------
# Task 36: outcome vs pre-registered prediction
# ------------------------------------------------------------------

def _observed_value(outcome):
    """Extract a numeric observation. Returns (found, value)."""
    if isinstance(outcome, bool):
        return (False, None)
    if isinstance(outcome, (int, float)):
        return (True, float(outcome))
    if isinstance(outcome, str):
        try:
            return (True, float(outcome.strip()))
        except ValueError:
            return (False, None)
    if isinstance(outcome, dict):
        for key in ("value", "observed", "observed_value", "outcome",
                    "result"):
            if outcome.get(key) is not None and not isinstance(
                    outcome.get(key), bool):
                found, value = _observed_value(outcome[key])
                if found:
                    if "metric" in outcome and isinstance(
                            outcome.get("metric"), str):
                        return (True, (outcome["metric"], value))
                    return (True, value)
        params = outcome.get("parameters")
        if isinstance(params, dict) and params.get("value") is not None:
            return _observed_value(params["value"])
    return (False, None)


def _prereg_target(prereg):
    """Parse a prereg dict. Returns (kind, target, tolerance, metric).

    kind is 'expected' (match within tolerance) or 'threshold'
    (directional comparison), or (None, ...) when unparseable.
    """
    if not isinstance(prereg, dict):
        return (None, None, None, None)
    metric = prereg.get("metric")
    if isinstance(metric, str) and not metric.strip():
        metric = None
    for key in ("expected_value", "expected", "prediction",
                "predicted_value"):
        if prereg.get(key) is not None:
            try:
                target = float(prereg[key])
            except (TypeError, ValueError):
                continue
            tol = prereg.get("tolerance", prereg.get("tol", 0.0))
            try:
                tol = float(tol)
            except (TypeError, ValueError):
                tol = 0.0
            return ("expected", target, abs(tol), metric)
    if prereg.get("threshold") is not None:
        try:
            target = float(prereg["threshold"])
        except (TypeError, ValueError):
            return (None, None, None, None)
        direction = str(prereg.get("direction", ">=")).strip()
        if direction not in (">=", "<=", ">", "<", "=="):
            direction = ">="
        return ("threshold", target, direction, metric)
    return (None, None, None, None)


def compare_to_prereg(outcome, prereg):
    """Compare an outcome to a pre-registered prediction.

    Returns {"verdict": "match"|"no-match"|"indeterminate", ...}.
    No adjectives: the verdict is one of the three tokens, and the
    detail states numbers only.
    """
    found, observed = _observed_value(outcome)
    kind, target, tol_or_dir, metric = _prereg_target(prereg)
    base = {"observed": observed if not isinstance(observed, tuple)
            else observed[1],
            "observed_metric": observed[0] if isinstance(observed, tuple)
            else (outcome.get("metric") if isinstance(outcome, dict)
                  else None),
            "target": target}
    if not found:
        base.update(verdict="indeterminate",
                    detail="observed value absent; no comparison recorded")
        return base
    if kind is None:
        base.update(verdict="indeterminate",
                    detail="pre-registered prediction has no numeric "
                    "expected value or threshold; no comparison recorded")
        return base
    obs = observed[1] if isinstance(observed, tuple) else observed
    obs_metric = (observed[0] if isinstance(observed, tuple)
                  else (outcome.get("metric") if isinstance(outcome, dict)
                        else None))
    if metric and obs_metric and metric != obs_metric:
        base.update(
            verdict="indeterminate",
            detail="metric %r does not match pre-registered metric %r; "
            "no comparison recorded" % (obs_metric, metric))
        return base
    if kind == "expected":
        match = abs(obs - target) <= tol_or_dir
        base.update(
            verdict="match" if match else "no-match",
            detail="observed=%r expected=%r tolerance=%r" % (
                obs, target, tol_or_dir))
        return base
    ops = {">=": obs >= target, "<=": obs <= target, ">": obs > target,
           "<": obs < target, "==": obs == target}
    match = bool(ops[tol_or_dir])
    base.update(
        verdict="match" if match else "no-match",
        detail="observed=%r threshold=%r direction=%r" % (
            obs, target, tol_or_dir))
    return base


def write_result(outcome, prereg, ledger_path=None,
                 agent="computational-scientist", extra=None):
    """Compare an outcome to a preregistration; optionally file it.

    Returns the comparison record {"kind": "result-vs-prereg",
    "verdict": match|no-match|indeterminate, ...}.
    """
    comparison = compare_to_prereg(outcome, prereg)
    record = {"kind": "result-vs-prereg", "agent": agent,
              "recorded_at": _utcnow()}
    record.update(comparison)
    if isinstance(extra, dict):
        for key, value in extra.items():
            record.setdefault(key, value)
    if ledger_path is not None:
        if _ledger_append is None:
            raise NotImplementedError(
                "UNIMPLEMENTED: ledger module unavailable; cannot file.")
        return _ledger_append(str(ledger_path), record)
    return record


# ------------------------------------------------------------------
# Task 37: compute budget (wall-clock + call caps via lab_config)
# ------------------------------------------------------------------

def check_compute_budget(config, agent="computational-scientist",
                         spend=0, calls=0, elapsed_seconds=None,
                         actions=None):
    """Check call/spend caps via lab_config plus an optional wall clock.

    config may carry compute.maxWallSeconds; elapsed_seconds above it
    stops the run. Returns (allowed: bool, reason: str).
    """
    if _lab_config_mod is None:
        return (False, "blocked: lab_config module unavailable; refusing "
                "to run without budget caps")
    if not isinstance(config, dict):
        raise TypeError("config must be a dict")
    allowed, reason = _lab_config_mod.check_budget(
        config, agent, spend, calls, actions)
    if not allowed:
        return (False, reason)
    limit = None
    compute_cfg = config.get("compute")
    if isinstance(compute_cfg, dict):
        limit = compute_cfg.get("maxWallSeconds",
                                compute_cfg.get("max_wall_seconds"))
    if limit is not None and elapsed_seconds is not None:
        try:
            if float(elapsed_seconds) > float(limit):
                return (False,
                        "budget-cap-reached: agent %r wall-clock %s > "
                        "maxWallSeconds %s" % (agent, elapsed_seconds, limit))
        except (TypeError, ValueError):
            pass
    if limit is None:
        return (True, reason + "; wall-clock: no maxWallSeconds cap set")
    return (True, reason + "; wall-clock %s/%s s" % (elapsed_seconds, limit))


def write_stop_receipt(path, agent, spend, calls, reason, actions=None):
    """Write a budget-stop receipt. The run stops here."""
    if _lab_config_mod is None:
        raise NotImplementedError(
            "UNIMPLEMENTED: lab_config module unavailable; cannot file.")
    return _lab_config_mod.write_receipt(path, agent, spend, calls,
                                         reason, actions)


# ------------------------------------------------------------------
# Task 38: reproduce from an archived record
# ------------------------------------------------------------------

def reproduce_from_record(record, ledger_path=None, timeout=30):
    """Re-run a record from its archived inputs; return the comparison.

    Rebuilds the plan from record parameters (_command or _dept
    inputs), the archived seed, and hashes; re-executes; compares
    output_hash. Returns {"match": bool, "verdict":
    "reproduced"|"mismatch", ...}, filed to ledger_path when given.
    A record with no archived rerun inputs raises ValueError loudly.
    """
    if not isinstance(record, dict):
        raise TypeError("record must be a dict")
    params = record.get("parameters")
    if not isinstance(params, dict):
        raise ValueError("not reproducible: record carries no parameters")
    dept = params.get("_dept")
    if dept == "bio":
        rerun = run_bio({"sequence": params["sequence"],
                         "seed": record.get("random_seed")})
    elif dept == "chem":
        if "dataset" in params:
            rerun = run_chem({"dataset": params["dataset"],
                              "column": params.get("column"),
                              "n_rows": params.get("n_rows", 10),
                              "statistic": params.get("statistic", "mean"),
                              "seed": record.get("random_seed")})
        else:
            rerun = run_chem({"formula": params["formula"],
                              "seed": record.get("random_seed")})
    elif dept == "physics":
        rerun = run_physics({"v0": params["v0"],
                             "angle_deg": params["angle_deg"],
                             "g": params.get("g", 9.81),
                             "seed": record.get("random_seed")})
    elif dept == "materials":
        rerun = run_materials({"fractions": params["fractions"],
                               "densities": params["densities"],
                               "seed": record.get("random_seed")})
    elif params.get("_command"):
        plan = {
            "command": params["_command"],
            "seed": record.get("random_seed"),
            "code_hash": params.get("_code_hash"),
            "data_hash": params.get("_data_hash"),
            "research_question": record.get("research_question"),
            "hypothesis_id": record.get("hypothesis_id"),
            "hypothesis_version": record.get("hypothesis_version"),
            "original_data": record.get("original_data"),
            "data_source": record.get("data_source"),
            "software": record.get("software"),
            "model": record.get("model"),
            "parameters": {k: v for k, v in params.items()
                           if not k.startswith("_")},
            "is_prediction": record.get("is_prediction", False),
        }
        rerun = run_experiment(plan, timeout=timeout)
    else:
        raise ValueError(
            "not reproducible: record %r carries no archived command "
            "(_command) or department inputs (_dept)" % (record.get("id"),))
    original_hash = record.get("output_hash")
    rerun_hash = rerun.get("output_hash")
    match = (original_hash is not None and original_hash == rerun_hash)
    comparison = {
        "kind": "reproduction-check",
        "original_id": record.get("id"),
        "original_output_hash": original_hash,
        "rerun_output_hash": rerun_hash,
        "match": match,
        "verdict": "reproduced" if match else "mismatch",
        "recorded_at": _utcnow(),
    }
    if ledger_path is not None:
        if _ledger_append is None:
            raise NotImplementedError(
                "UNIMPLEMENTED: ledger module unavailable; cannot file.")
        filed = _ledger_append(str(ledger_path), dict(comparison))
        comparison["entry_hash"] = filed.get("entry_hash")
        comparison["prev_hash"] = filed.get("prev_hash")
    comparison["rerun_record"] = rerun
    return comparison


__all__ = [
    "SANDBOX_FORBIDDEN",
    "assert_sandbox_clean",
    "run_experiment",
    "rerun_same",
    "run_bio",
    "run_chem",
    "run_physics",
    "run_materials",
    "validate_record_shape",
    "file_experiment_record",
    "compare_to_prereg",
    "write_result",
    "check_compute_budget",
    "write_stop_receipt",
    "reproduce_from_record",
]
