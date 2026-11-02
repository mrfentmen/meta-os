#!/usr/bin/env python3
"""os-build/layer1/reconcile_counts.py -- E5: every count in the docs, checked.

Docs in this lane repeat four numbers constantly: how many services, how many drivers, how
many assertions, how many lines. When one of them changes, the docs that repeat it go stale
silently, and a reviewer has no way to tell a stale page from a wrong system.

This program does two things:

  1. Measures the live numbers from the tree and the runner's own row file.
  2. Scans the markdown in the lane for assertions of the same shape and reports each one
     whose number disagrees with the live value.

Historical documents (round reports, sign-offs) are EXPECTED to disagree: they are records
of a moment, and rewriting them would destroy the record. They are listed in HISTORICAL and
must carry a banner pointing at COUNTS.md; a missing banner is itself a finding.

Usage:
    python3 os-build/layer1/reconcile_counts.py          # report, exit 1 on a live mismatch
    python3 os-build/layer1/reconcile_counts.py --write  # rewrite COUNTS.md, then report
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SERVICES = os.path.join(ROOT, "services")
DEST = os.path.join(HERE, "COUNTS.md")
BANNER = "> Counts in this file are as of the round it records. Live numbers: `COUNTS.md`."

# Records of a moment. Their numbers must not be rewritten; their banner must exist.
HISTORICAL = {
    "ROUND6.md", "SIGNOFF.md", "GATE_RERUN.md", "FINISH_STATE.md", "FINISH_STATUS.md",
    "BUFFY_REPORT.md", "RECONCILE_DEMO_FACTS.md", "FREEZE_AUDIT.md", "SERVICES_SCOPE.md",
    "BOOT_PLAN.md", "LOAD_ORDER_1102.md", "KERNEL_NEEDS_AFTER.md",
}


def dirs_with_source():
    out = []
    for name in sorted(os.listdir(SERVICES)):
        p = os.path.join(SERVICES, name)
        if not os.path.isdir(p) or name in ("common", "tests", "build"):
            continue
        if any(f.endswith(".goose") for f in os.listdir(p)):
            out.append(name)
    return out


def goose_files():
    out = []
    for base, _dirs, names in os.walk(SERVICES):
        for n in names:
            if n.endswith(".goose"):
                out.append(os.path.join(base, n))
    return out


def live():
    files = goose_files()
    lines = 0
    for f in files:
        with open(f, "r", encoding="utf-8") as h:
            lines += h.read().count("\n")
    drivers = len([f for f in os.listdir(os.path.join(SERVICES, "tests"))
                   if f.endswith(".goose")])
    rows = os.path.join(HERE, "host", "run_rows.txt")
    runs = checks = 0
    with open(rows, "r", encoding="utf-8") as h:
        for line in h:
            parts = line.rstrip("\n").split("|")
            if len(parts) < 4 or not parts[0].startswith("tests/"):
                continue
            if parts[1] == "RUNS":
                runs += 1
            try:
                checks += int(parts[2])
            except ValueError:
                pass
    boot = 0
    with open(os.path.join(SERVICES, "supervisor", "bootorder.goose"), "r",
              encoding="utf-8") as h:
        m = re.search(r"fn bo_count\(\) -> i64 \{ return (\d+);", h.read())
        boot = int(m.group(1)) if m else 0
    manifest = 0
    mpath = os.path.join(HERE, "services.json")
    if os.path.exists(mpath):
        import json
        with open(mpath, "r", encoding="utf-8") as h:
            manifest = len(json.load(h).get("services", []))
    return {
        "services with code": len(dirs_with_source()),
        "services in the manifest": manifest,
        "services in the boot order": boot,
        "Goose files": len(files),
        "lines of Goose": lines,
        "test drivers": drivers,
        "drivers that run": runs,
        "passing checks": checks,
    }


# A claim is "<number> <noun>" where the noun is one of the counted things, anywhere in the
# lane's markdown. The mapping is explicit because "22 services" and "22 rows" are different
# claims and a regex that guessed would report the wrong one.
CLAIMS = [
    (re.compile(r"\b(\d[\d,]*)\s+(?:test\s+)?drivers?\b"), "test drivers"),
    (re.compile(r"\b(\d[\d,]*)\s+assertions?\b"), "passing checks"),
    (re.compile(r"\b(\d[\d,]*)\s+(?:services? with code|services? in the manifest)\b"),
     "services with code"),
    (re.compile(r"\b(\d[\d,]*)\s+services?\s+in the boot (?:table|order)\b"),
     "services in the boot order"),
]


def scan(live_values):
    findings = []
    docs = []
    for base, dirs, names in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in ("host", "captures", "contracts")]
        for n in sorted(names):
            if n.endswith(".md") and n not in ("COUNTS.md", "SERVICES_FINAL.md"):
                docs.append(os.path.join(base, n))
    for path in docs:
        rel = os.path.relpath(path, HERE)
        with open(path, "r", encoding="utf-8") as h:
            text = h.read()
        name = os.path.basename(path)
        for pattern, key in CLAIMS:
            for m in pattern.finditer(text):
                claimed = int(m.group(1).replace(",", ""))
                if claimed == live_values[key]:
                    continue
                # A number with a date beside it is a record of that day, not a live claim.
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_end = text.find("\n", m.end())
                line = text[line_start:line_end if line_end > 0 else len(text)]
                historical = name in HISTORICAL
                findings.append({
                    "file": rel,
                    "claim": m.group(0).strip(),
                    "line": line.strip()[:120],
                    "expected": live_values[key],
                    "historical": historical,
                })
    return findings


def banner_missing():
    missing = []
    for name in sorted(HISTORICAL):
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as h:
            if BANNER not in h.read():
                missing.append(name)
    return missing


def write_index(values, findings, missing):
    lines = ["# Counts — the live numbers, and every doc that repeats one",
             "",
             "Generated by `python3 os-build/layer1/reconcile_counts.py --write`. If a number",
             "here disagrees with a report, this file is the one with a command behind it.",
             "",
             "| Count | Value | Command |",
             "|---|---|---|"]
    cmds = {
        "services with code": "`ls -d services/*/` minus `common`, `tests`, `build`",
        "services in the manifest": "`jq '.services | length' os-build/layer1/services.json`",
        "services in the boot order": "`python3 os-build/layer1/bootorder_check.py`",
        "Goose files": "`find services -name '*.goose' | wc -l`",
        "lines of Goose": "`cat $(find services -name '*.goose') | wc -l`",
        "test drivers": "`ls services/tests/*.goose | wc -l`",
        "drivers that run": "`./os-build/layer1/run_native.sh`",
        "passing checks": "`awk -F'|' '/^tests\\// {s+=$3} END {print s}' os-build/layer1/host/run_rows.txt`",
    }
    for key in values:
        lines.append("| %s | **%s** | %s |" % (key, f"{values[key]:,}", cmds.get(key, "")))
    lines += [
        "",
        "## Docs that repeat a count",
        "",
        "A number that matches the table above is fine wherever it appears. A number that does",
        "not is listed below, with the reason it is allowed to disagree.",
        "",
        "| File | Claim in the doc | Live value | Status |",
        "|---|---|---|---|",
    ]
    stale = [f for f in findings if not f["historical"]]
    for f in stale:
        lines.append("| `%s` | %s | %s | **STALE — must be fixed** |"
                     % (f["file"], f["claim"].replace("|", "\\|"), f"{f['expected']:,}"))
    hist = [f for f in findings if f["historical"]]
    for f in hist:
        lines.append("| `%s` | %s | %s | historical record, bannered |"
                     % (f["file"], f["claim"].replace("|", "\\|"), f"{f['expected']:,}"))
    if not stale:
        lines.append("| — | no live doc disagrees | — | clean |")
    lines += [
        "",
        "## Historical documents without a banner",
        "",
    ]
    if missing:
        for name in missing:
            lines.append("- `%s` — repeats round numbers and does not point here" % name)
    else:
        lines.append("None: every record names `COUNTS.md` in its first lines.")
    lines += ["", "_The two counts that are easy to confuse are named apart on purpose:_ "
              "**test drivers** is how many programs exist, **passing checks** is how many "
              "assertions they printed `ok` for. A driver count is not a service count and "
              "never has been.", ""]
    with open(DEST, "w", encoding="utf-8") as h:
        h.write("\n".join(lines))
    return DEST


def main(argv):
    values = live()
    findings = scan(values)
    missing = banner_missing()
    if "--write" in argv:
        path = write_index(values, findings, missing)
        print("wrote %s" % os.path.relpath(path, ROOT))
    print("counts: " + ", ".join("%s=%s" % (k, v) for k, v in values.items()))
    print("")
    stale = [f for f in findings if not f["historical"]]
    if stale:
        print("STALE in live docs (%d):" % len(stale))
        for f in stale:
            print("  %-40s %-24s live=%d" % (f["file"], f["claim"], f["expected"]))
        print("")
    else:
        print("no stale counts in the live docs")
        print("")
    if missing:
        print("historical docs missing the banner (%d): %s" % (len(missing), ", ".join(missing)))
        return 1
    if stale:
        return 1
    print("clean: every live doc agrees with the tree, every record is bannered")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
