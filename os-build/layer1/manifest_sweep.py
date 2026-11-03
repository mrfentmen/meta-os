#!/usr/bin/env python3
"""R13-101..125 — OSV sweep over this tree's real dependency manifests.

The Round 13 list names 25 manifests. Fifteen of those paths do not exist in this tree
(there is no package-lock.json, no requirements.txt, no per-package manifest for face/
board/relay/agents/tests/docs/image/skills). Inventing a sweep record for a file that is
not there would be the exact failure Aegis is built to refuse, so this tool sweeps the
manifests that DO exist and writes down, per task, which case it is.

Route, stated: https://api.osv.dev/v1/query, called directly. osv-mcp is not installed on
this host (the gateway config points at /home/hatch/..., which is not this machine), so the
"only through the boss's server" rule cannot be met here and the direct route is used under
the standing written exception. Every record repeats this sentence; a sweep whose source
line is a guess is not evidence.

Severity, stated: OSV does not publish a severity for every record. Three buckets, and none
of them is invented:
  GHSA band      database_specific.severity as published (LOW/MODERATE/HIGH/CRITICAL)
  UNRATED        a CVSS vector is present but no band is published; the vector is kept
  UNPUBLISHED    the source publishes neither
"""
import hashlib
import json
import os
import re
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "os-build", "round13", "aegis")
ROUTE = ("https://api.osv.dev/v1/query, direct (osv-mcp is not installed on this host; "
         "standing written exception, route stated in the record)")
BANDS = ["CRITICAL", "HIGH", "MODERATE", "LOW", "UNRATED", "UNPUBLISHED"]

LOCKFILES = ["Cargo.lock", "kernel/Cargo.lock", "os-build/userspace/user/Cargo.lock"]
CARGO_MANIFESTS = None  # discovered

# task id -> (named path, resolution rule)
TASKS = [
    ("R13-101", "package.json", "npm"),
    ("R13-102", "package-lock.json", "npm-lock"),
    ("R13-103", "Cargo.toml", "cargo"),
    ("R13-104", "Cargo.lock", "cargo-lock"),
    ("R13-105", "kernel/Cargo.toml", "cargo"),
    ("R13-106", "crates/intel", "crate"),
    ("R13-107", "crates/queue-core", "crate"),
    ("R13-108", "crates/os-supervisor", "crate"),
    ("R13-109", "services/MANIFEST.md", "none"),
    ("R13-110", "server/queue requirements", "python"),
    ("R13-111", "science-lab requirements", "python"),
    ("R13-112", "goose toolchain manifest", "none"),
    ("R13-113", "face/package.json", "npm"),
    ("R13-114", "board/package.json", "npm"),
    ("R13-115", "relay/package.json", "npm"),
    ("R13-116", "agents/package.json", "npm"),
    ("R13-117", "tests manifests", "npm"),
    ("R13-118", "os/worlds pack manifests", "npm"),
    ("R13-119", "docs tooling manifest", "npm"),
    ("R13-120", "image build manifest", "none"),
    ("R13-121", "legacy connector manifests", "none"),
    ("R13-122", "custom-skills manifests", "none"),
    ("R13-123", "mcp-gateway/package.json", "npm"),
    ("R13-124", "crates/assess-server", "crate"),
    ("R13-125", "crates/* (remaining)", "crates-all"),
]

_lock = threading.Lock()
_seen = {}


def rel(path):
    return os.path.relpath(path, ROOT)


def parse_cargo_lock(path):
    """Return (queries, local) for one Cargo.lock. `source` absent == workspace crate."""
    text = open(path, "r", encoding="utf-8").read()
    queries, local, seen = [], [], set()
    for block in text.split("[[package]]")[1:]:
        name = re.search(r'^name = "([^"]+)"', block, re.M)
        version = re.search(r'^version = "([^"]+)"', block, re.M)
        source = re.search(r'^source = "([^"]+)"', block, re.M)
        if not name or not version:
            continue
        if not source:
            local.append({"name": name.group(1), "version": version.group(1)})
            continue
        key = name.group(1) + "@" + version.group(1)
        if key in seen:
            continue
        seen.add(key)
        queries.append({"ecosystem": "crates.io", "name": name.group(1),
                        "version": version.group(1), "via": rel(path)})
    return queries, local


def parse_package_json(path):
    doc = json.load(open(path, "r", encoding="utf-8"))
    deps = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        deps.update(doc.get(key) or {})
    # A range is not a version. Asking OSV about "^1.2.3" is asking about a string it cannot
    # resolve, and recording the answer as a finding would be recording a parse artefact.
    pinned, ranged = [], []
    for name, spec in deps.items():
        m = re.fullmatch(r"=?(\d+\.\d+\.\d+)", str(spec).strip())
        if m:
            pinned.append({"ecosystem": "npm", "name": name, "version": m.group(1),
                           "via": rel(path)})
        else:
            ranged.append({"name": name, "spec": str(spec), "via": rel(path)})
    return pinned, ranged


def severity_of(vuln):
    band = (vuln.get("database_specific") or {}).get("severity")
    if isinstance(band, str) and band.upper() in BANDS:
        return band.upper(), None
    sev = vuln.get("severity") or []
    if sev:
        return "UNRATED", sev[0].get("score")
    return "UNPUBLISHED", None


def query(ref):
    key = (ref["ecosystem"], ref["name"], ref["version"])
    with _lock:
        if key in _seen:
            return _seen[key]
    body = json.dumps({"package": {"name": ref["name"], "ecosystem": ref["ecosystem"]},
                       "version": ref["version"]}).encode()
    req = urllib.request.Request("https://api.osv.dev/v1/query", data=body,
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read())
    except Exception as exc:                                  # noqa: BLE001 - reported, not hidden
        result = {"error": str(exc), "vulns": []}
    else:
        result = {"vulns": payload.get("vulns", [])}
    with _lock:
        _seen[key] = result
    return result


def manifest_block(label, path, queries, extra=None):
    findings = []
    errors = []
    for ref in queries:
        answer = query(ref)
        if answer.get("error"):
            errors.append({"package": ref["name"], "error": answer["error"]})
        for vuln in answer["vulns"]:
            band, vector = severity_of(vuln)
            findings.append({
                "id": vuln.get("id"),
                "aliases": vuln.get("aliases", []),
                "package": ref["name"],
                "version": ref["version"],
                "severity": band,
                "cvss": vector,
                "summary_present": bool(vuln.get("summary")),
                "source": vuln.get("modified") and "osv" or "osv",
            })
    counts = {band: 0 for band in BANDS}
    for finding in findings:
        counts[finding["severity"]] += 1
    block = {
        "label": label,
        "path": path,
        "exists": path is not None,
        "refs": len(queries),
        "findings": findings,
        "counts_by_severity": {k: v for k, v in counts.items() if v},
        "errors": errors,
    }
    if extra:
        block.update(extra)
    return block


def main():
    os.makedirs(OUT, exist_ok=True)
    # Positive control. "Zero findings" is the one answer a broken parser also gives, so the
    # run proves it can still see a hit: crates.io/time@0.1.44 is a published RUSTSEC advisory
    # and a sweep that cannot find it has not swept anything.
    control_ref = {"ecosystem": "crates.io", "name": "time", "version": "0.1.44"}
    control = query(dict(control_ref))
    control_ids = sorted(v.get("id") for v in control.get("vulns", []))
    records = []
    crate_manifests = sorted(
        rel(os.path.join(dp, f))
        for dp, _, files in os.walk(os.path.join(ROOT, "crates")) for f in files
        if f == "Cargo.toml")
    crate_manifests += ["kernel/Cargo.toml", "os-build/userspace/user/Cargo.toml",
                        "Cargo.toml"]

    # Sweep each lockfile once and reuse the answer for every task that names it.
    lock_blocks = {}
    for lock in LOCKFILES:
        path = os.path.join(ROOT, lock)
        if not os.path.exists(path):
            continue
        queries, local = parse_cargo_lock(path)
        lock_blocks[lock] = manifest_block(
            "crates.io lock", lock, queries,
            {"local_crates": len(local), "lock_sha256": hashlib.sha256(
                open(path, "rb").read()).hexdigest()})

    for task, named, kind in TASKS:
        if kind == "cargo-lock":
            path = os.path.join(ROOT, "Cargo.lock")
            block = dict(lock_blocks.get("Cargo.lock") or {
                "label": "crates.io lock", "path": "Cargo.lock", "exists": False,
                "refs": 0, "findings": [], "counts_by_severity": {}, "errors": []})
        elif kind == "npm-lock":
            path = os.path.join(ROOT, "package-lock.json")
            block = manifest_block("npm lock", "package-lock.json", []) if os.path.exists(path) else {
                "label": "npm lock", "path": "package-lock.json", "exists": False,
                "refs": 0, "findings": [], "counts_by_severity": {}, "errors": []}
        elif kind == "npm":
            path = os.path.join(ROOT, named)
            if os.path.exists(path):
                pinned, ranged = parse_package_json(path)
                block = manifest_block("npm manifest", named, pinned,
                                       {"unversioned": len(ranged)})
            else:
                block = {"label": "npm manifest", "path": named, "exists": False,
                         "refs": 0, "findings": [], "counts_by_severity": {}, "errors": []}
        elif kind == "cargo":
            path = os.path.join(ROOT, named)
            if not os.path.exists(path):
                block = {"label": "cargo manifest", "path": named, "exists": False,
                         "refs": 0, "findings": [], "counts_by_severity": {}, "errors": []}
            else:
                # A Cargo.toml declares ranges. The resolved versions are in the lockfile,
                # so the lockfile is the query set and the manifest is the declaration.
                deps = len(re.findall(r"^[\w-]+\s*=", open(path, encoding="utf-8").read(), re.M))
                block = {"label": "cargo manifest", "path": named, "exists": True,
                         "declared_lines": deps, "refs": 0, "findings": [],
                         "counts_by_severity": {}, "errors": [],
                         "note": "Cargo.toml names ranges; the resolved versions were swept "
                                 "through the lockfile record that covers this crate."}
        elif kind == "crate":
            manifest = os.path.join(named, "Cargo.toml")
            exists = os.path.exists(os.path.join(ROOT, manifest))
            block = {"label": "cargo crate", "path": manifest, "exists": exists,
                     "refs": 0, "findings": [], "counts_by_severity": {}, "errors": [],
                     "note": ("resolved versions come from Cargo.lock, swept under R13-104"
                              if exists else "crate directory is not in this tree")}
        elif kind == "crates-all":
            block = {"label": "cargo crate set", "path": "crates/*/Cargo.toml", "exists": True,
                     "manifests": crate_manifests, "refs": 0, "findings": [],
                     "counts_by_severity": {}, "errors": [],
                     "note": "every crate manifest was enumerated; resolved versions were "
                             "swept through Cargo.lock (R13-104), which is the only file that "
                             "pins them."}
        elif kind == "python":
            block = {"label": "python requirements", "path": named, "exists": False,
                     "refs": 0, "findings": [], "counts_by_severity": {}, "errors": [],
                     "note": "no requirements.txt or pyproject.toml exists anywhere in the tree"}
        else:
            block = {"label": "none", "path": named, "exists": False, "refs": 0,
                     "findings": [], "counts_by_severity": {}, "errors": [],
                     "note": "the named artifact is not a dependency manifest"}
        block["task"] = task
        block["named"] = named
        block["route"] = ROUTE
        records.append(block)

    out = {
        "tool": "os-build/layer1/manifest_sweep.py",
        "route": ROUTE,
        "control": {"ref": control_ref, "ids": control_ids,
                     "ok": bool(control_ids)},
        "lockfiles": lock_blocks,
        "tasks": records,
    }
    with open(os.path.join(OUT, "OSV_SWEEP.json"), "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=2)
        handle.write("\n")

    total = sum(len(r["findings"]) for r in records)
    print("route: %s" % ROUTE)
    print("control crates.io/time@0.1.44 -> %d ids %s" % (
        len(control_ids), control_ids))
    if not control_ids:
        print("CONTROL FAILED: the query path sees nothing; this run is BLOCKED, not clean")
        return 3
    for lock, block in lock_blocks.items():
        print("lock %-34s refs=%-4d findings=%-3d %s" % (
            lock, block["refs"], len(block["findings"]),
            json.dumps(block["counts_by_severity"])))
    print("\nper task:")
    for rec in records:
        print("%-9s %-34s exists=%-5s refs=%-4d findings=%d %s" % (
            rec["task"], rec["named"], rec["exists"], rec["refs"],
            len(rec["findings"]), json.dumps(rec["counts_by_severity"])))
    print("\ntasks=%d findings_total=%d" % (len(records), total))


if __name__ == "__main__":
    sys.exit(main())
