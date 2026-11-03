#!/usr/bin/env python3
"""R13-126..150 — CISA KEV cross-check for the Section E findings.

The list asks for a per-finding KEV flag, and says a silent pass is a failed task. Section E
found zero vulnerabilities, so every one of these 25 cross-checks has an empty input. That is
recorded explicitly, per task, and never as "all clear".

Two things make the empty result checkable rather than vacuous:

  1. The feed is actually fetched. Its catalog version, release date, entry count and SHA-256
     go in the record, so a reader can tell this run read a real feed and which one.
  2. A positive control. CVE-2021-44228 (log4j) is in the KEV catalogue; a matcher that cannot
     find it has not matched anything, and the run is marked BROKEN rather than clean.

Usage: python3 os-build/layer1/kev_crosscheck.py
Exit: 0 ran with a working control, 3 control failed (run is blocked, not clean).
"""
import hashlib
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "os-build", "round13", "aegis")
FEED = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CONTROL_CVE = "CVE-2021-44228"

# task id -> (findings class named by the list, the classes that would feed it)
TASKS = [
    ("R13-126", "node dependency findings", "batch 1", ["npm"]),
    ("R13-127", "rust crate findings", "batch 1", ["crates.io"]),
    ("R13-128", "python dependency findings", "batch 1", ["PyPI"]),
    ("R13-129", "lockfile-pinned findings", "batch 1", ["crates.io", "npm"]),
    ("R13-130", "transitive findings", "batch 1", ["crates.io", "npm", "PyPI"]),
    ("R13-131", "node dependency findings", "batch 2", ["npm"]),
    ("R13-132", "rust crate findings", "batch 2", ["crates.io"]),
    ("R13-133", "python dependency findings", "batch 2", ["PyPI"]),
    ("R13-134", "lockfile-pinned findings", "batch 2", ["crates.io", "npm"]),
    ("R13-135", "transitive findings", "batch 2", ["crates.io", "npm", "PyPI"]),
    ("R13-136", "node dependency findings", "batch 3", ["npm"]),
    ("R13-137", "rust crate findings", "batch 3", ["crates.io"]),
    ("R13-138", "python dependency findings", "batch 3", ["PyPI"]),
    ("R13-139", "lockfile-pinned findings", "batch 3", ["crates.io", "npm"]),
    ("R13-140", "transitive findings", "batch 3", ["crates.io", "npm", "PyPI"]),
    ("R13-141", "node dependency findings", "batch 4", ["npm"]),
    ("R13-142", "rust crate findings", "batch 4", ["crates.io"]),
    ("R13-143", "python dependency findings", "batch 4", ["PyPI"]),
    ("R13-144", "lockfile-pinned findings", "batch 4", ["crates.io", "npm"]),
    ("R13-145", "transitive findings", "batch 4", ["crates.io", "npm", "PyPI"]),
    ("R13-146", "node dependency findings", "batch 5", ["npm"]),
    ("R13-147", "rust crate findings", "batch 5", ["crates.io"]),
    ("R13-148", "python dependency findings", "batch 5", ["PyPI"]),
    ("R13-149", "lockfile-pinned findings", "batch 5", ["crates.io", "npm"]),
    ("R13-150", "transitive findings", "batch 5", ["crates.io", "npm", "PyPI"]),
]


def fetch():
    with urllib.request.urlopen(FEED, timeout=60) as res:
        raw = res.read()
    return raw, json.loads(raw)


def main():
    os.makedirs(OUT, exist_ok=True)
    raw, feed = fetch()
    entries = feed.get("vulnerabilities", [])
    kev = {}
    for entry in entries:
        kev[entry.get("cveID")] = {
            "vendor": entry.get("vendorProject"),
            "product": entry.get("product"),
            "dateAdded": entry.get("dateAdded"),
            "knownRansomware": entry.get("knownRansomwareCampaignUse"),
            "dueDate": entry.get("requiredAction") and entry.get("dueDate"),
        }
    control = CONTROL_CVE in kev

    sweep_path = os.path.join(OUT, "OSV_SWEEP.json")
    findings = []
    if os.path.exists(sweep_path):
        sweep = json.load(open(sweep_path, encoding="utf-8"))
        for block in sweep.get("lockfiles", {}).values():
            findings.extend(block.get("findings", []))

    records = []
    for task, klass, batch, ecosystems in TASKS:
        subset = [f for f in findings if f.get("ecosystem", "crates.io") in ecosystems]
        # OSV returned ids like RUSTSEC-/GHSA-; a KEV entry is keyed by CVE. An advisory with
        # no CVE alias can never match the catalogue, and saying "cleared" for it would be a
        # claim the data does not support.
        checked, unmatchable = [], []
        for finding in subset:
            aliases = finding.get("aliases") or []
            cves = [a for a in aliases if str(a).startswith("CVE-")] or (
                [finding["id"]] if str(finding.get("id", "")).startswith("CVE-") else [])
            if not cves:
                unmatchable.append(finding.get("id"))
                continue
            hits = [c for c in cves if c in kev]
            checked.append({"id": finding.get("id"), "cves": cves, "kev": hits})
        records.append({
            "task": task,
            "class": klass,
            "batch": batch,
            "findings_in_class": len(subset),
            "kev_flagged": sum(1 for c in checked if c["kev"]),
            "cleared": sum(1 for c in checked if not c["kev"]),
            "unmatchable_no_cve": unmatchable,
            "status": "NOTHING_TO_CHECK" if not subset else "CHECKED",
            "line": ("0 findings of this class in Section E; nothing to cross-check. "
                     "This is not a clearance of the class." if not subset else
                     "%d findings, %d KEV-flagged, %d cleared" % (
                         len(subset), sum(1 for c in checked if c["kev"]),
                         sum(1 for c in checked if not c["kev"]))),
        })

    out = {
        "tool": "os-build/layer1/kev_crosscheck.py",
        "feed": FEED,
        "feed_sha256": hashlib.sha256(raw).hexdigest(),
        "feed_catalog_version": feed.get("catalogVersion"),
        "feed_date_released": feed.get("dateReleased"),
        "feed_entries": len(entries),
        "control": {"cve": CONTROL_CVE, "present": control},
        "findings_source": "os-build/round13/aegis/OSV_SWEEP.json",
        "findings_total": len(findings),
        "tasks": records,
    }
    with open(os.path.join(OUT, "KEV_CROSSCHECK.json"), "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=2)
        handle.write("\n")

    print("feed %s catalog=%s released=%s entries=%d sha256=%s" % (
        FEED, feed.get("catalogVersion"), feed.get("dateReleased"), len(entries),
        out["feed_sha256"][:16]))
    print("control %s present=%s" % (CONTROL_CVE, control))
    print("findings_total=%d" % len(findings))
    for rec in records:
        print("%-9s %-28s %-8s findings=%-3d %s" % (
            rec["task"], rec["class"], rec["batch"], rec["findings_in_class"], rec["line"]))
    if not control:
        print("CONTROL FAILED: the matcher cannot see a known KEV entry; run is BLOCKED")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
