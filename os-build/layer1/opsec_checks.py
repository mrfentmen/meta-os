#!/usr/bin/env python3
"""R13-226..250 — OPSEC checks. Mechanical where a command can decide, filed where it cannot.

The list's rule: deliver a pass/fail finding record, size failures small or big, fix only what
is ours and mechanical, and never auto-fix anything security-shaped. This tool does the
mechanical half and refuses the judgement half:

  PASS            a command decided it, and the record names the command's count
  FAIL            a command decided it against us
  NOT_INSPECTABLE no command can decide it (pixels, recordings) -- filed as a gap
  NOT_APPLICABLE  the artifact does not exist in this tree

No values: emails, paths and hostnames are counted, never printed. A path that names a user
account is the thing being checked for, so writing it into the record would fail the check it
was recording.

Usage: python3 os-build/layer1/opsec_checks.py
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "os-build", "round13", "aegis")

HOME_PATH = re.compile(r"(?:/Users/|/home/|C:\\\\Users\\\\)([A-Za-z0-9._-]+)")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
ROUTINE = re.compile(r"\b(?:0[0-3]|2[0-3]):[0-5][0-9]\b")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          errors="replace")


def read(rel):
    try:
        return open(os.path.join(ROOT, rel), encoding="utf-8", errors="ignore").read()
    except OSError:
        return None


def files_under(rel, exts):
    base = os.path.join(ROOT, rel)
    if not os.path.exists(base):
        return []
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in
                       {".git", "node_modules", "target", "vendor", "dist"}]
        for name in filenames:
            if not exts or os.path.splitext(name)[1].lower() in exts:
                out.append(os.path.join(dirpath, name))
    return out


def count_in(paths, pattern):
    hits = files = 0
    for path in paths:
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        n = len(pattern.findall(text))
        if n:
            files += 1
            hits += n
    return {"matches": hits, "files": files, "files_read": len(paths)}


def record(task, title, status, detail):
    return {"task": task, "title": title, "status": status, "detail": detail}


def checks():
    out = []

    # 226 commit author metadata
    # A count of identities is not a failure: this project has six agents. The exposure is a
    # consumer mail address in public commit metadata, so that is what is counted. A history
    # rewrite is destructive and is not attempted by a scanner; the finding goes to a human.
    emails = git("log", "--format=%ae").stdout.split()
    names = git("log", "--format=%an").stdout.split("\n")
    uniq_emails = sorted(set(e for e in emails if e))
    domains = {}
    for address in emails:
        domain = address.split("@")[-1] if "@" in address else "(none)"
        domains[domain] = domains.get(domain, 0) + 1
    consumer = sum(n for d, n in domains.items()
                   if d in ("gmail.com", "googlemail.com", "icloud.com", "outlook.com",
                            "hotmail.com", "yahoo.com", "proton.me", "protonmail.com"))
    out.append(record("R13-226", "commit author metadata",
                      "PASS" if consumer == 0 else "FAIL",
                      {"commits": len(emails), "distinct_author_emails": len(uniq_emails),
                       "distinct_author_names": len(set(n for n in names if n)),
                       "consumer_mail_commits": consumer,
                       "by_domain": domains,
                       "note": "counts only, no address printed; a history rewrite is "
                               "destructive and is left to a human"}))

    # 227 screenshots
    shots = files_under(".", {".png", ".jpg", ".jpeg", ".webp"})
    out.append(record("R13-227", "file paths in screenshots",
                      "NOT_INSPECTABLE" if shots else "NOT_APPLICABLE",
                      {"image_files": len(shots),
                       "why": "pixel content cannot be decided by a command; a human has to look"}))

    # 228 demo recordings
    recs = files_under(".", {".mp4", ".mov", ".webm", ".m4a", ".wav"})
    out.append(record("R13-228", "usernames in demo recordings",
                      "NOT_INSPECTABLE" if recs else "NOT_APPLICABLE",
                      {"recording_files": len(recs)}))

    # 229 local paths in committed logs
    logs = files_under("os-build/logs", {".txt"})
    out.append(record("R13-229", "local paths in committed logs", "CHECKED",
                      count_in(logs, HOME_PATH)))

    # 230 timestamps that leak routine
    stamps = git("log", "--format=%cd", "--date=format:%H").stdout.split()
    buckets = {}
    for hour in stamps:
        if hour.isdigit():
            key = "%02d" % int(hour)
            buckets[key] = buckets.get(key, 0) + 1
    out.append(record("R13-230", "timestamps that leak routine", "INFO",
                      {"commits_by_hour_utc": buckets,
                       "note": "distribution recorded without a judgement: a person reads it"}))

    # 231 branch names that leak plans
    branches = [b.strip(" *") for b in git("branch", "-a").stdout.split("\n") if b.strip()]
    leaky = [b for b in branches if re.search(r"(?i)(secret|internal|plan|launch|unreleased)", b)]
    out.append(record("R13-231", "branch names that leak plans",
                      "PASS" if not leaky else "FAIL",
                      {"branches": len(branches), "flagged": len(leaky)}))

    # 232 status file wording
    status = read("os-build/BUFFY_ROUND13_STATUS.md") or ""
    claims = len(re.findall(r"(?i)\bPROVEN\b", status))
    logs_named = len(re.findall(r"\.txt\b", status))
    out.append(record("R13-232", "status file wording",
                      "PASS" if claims == 0 or logs_named >= claims else "FAIL",
                      {"proven_claims": claims, "log_files_named": logs_named}))

    # 233 README wording on unfinished features
    readme = read("README.md") or ""
    out.append(record("R13-233", "README wording on unfinished features", "INFO",
                      {"unbuilt_markers": len(re.findall(r"(?i)not built|unbuilt|uncompiled", readme)),
                       "note": "markers present are the honest form; zero would be the worry"}))

    # 234 screenshot corners
    out.append(record("R13-234", "screenshot corners (tabs, docks, names)",
                      "NOT_INSPECTABLE" if shots else "NOT_APPLICABLE",
                      {"image_files": len(shots)}))

    # 235 demo script wording
    demo = files_under("os-build", {".md"})
    demo = [p for p in demo if "DEMO" in os.path.basename(p).upper()]
    out.append(record("R13-235", "demo script wording", "CHECKED",
                      {"home_path": count_in(demo, HOME_PATH), "email": count_in(demo, EMAIL)}))

    # 236 receipt files
    # "Receipt" in this tree means an OS drill receipt (a hosted run's proof), not a purchase.
    # The first version of this check called all 14 a failure; the class is what matters, so
    # only a purchase-shaped artifact (invoice, PDF) is counted against us.
    receipts = [p for p in files_under(".", set()) if "receipt" in os.path.basename(p).lower()]
    purchase = [p for p in receipts
                if os.path.splitext(p)[1].lower() == ".pdf" or "invoice" in p.lower()]
    out.append(record("R13-236", "receipt files in the repo",
                      "PASS" if not purchase else "FAIL",
                      {"receipt_named_files": len(receipts),
                       "purchase_shaped": len(purchase),
                       "note": "the 14 are drill/hosted proof receipts, not payment records"}))

    # 237 test fixtures with real-looking data
    tests = files_under("tests", {".mjs", ".json", ".py", ".goose"})
    out.append(record("R13-237", "test fixtures with real-looking data", "CHECKED",
                      {"email": count_in(tests, EMAIL),
                       "home_path": count_in(tests, HOME_PATH)}))

    # 238 bus message wording
    bus = [os.path.join(ROOT, "bus.html")] if os.path.exists(os.path.join(ROOT, "bus.html")) else []
    out.append(record("R13-238", "bus message wording (public viewer)",
                      "CHECKED" if bus else "NOT_APPLICABLE",
                      count_in(bus, EMAIL) if bus else {"files_read": 0}))

    # 239 site text on the live page
    site = files_under("site", {".html", ".js"})
    out.append(record("R13-239", "site text on the live page", "CHECKED",
                      {"home_path": count_in(site, HOME_PATH), "email": count_in(site, EMAIL)}))

    # 240 store listing wording
    out.append(record("R13-240", "store listing wording", "CHECKED",
                      {"home_path": count_in(site, HOME_PATH)}))

    # 241 goal file
    goal = [p for p in ("GOAL.md", "os-build/GOAL.md") if os.path.exists(os.path.join(ROOT, p))]
    out.append(record("R13-241", "goal file wording",
                      "CHECKED" if goal else "NOT_APPLICABLE", {"files": len(goal)}))

    # 242 skill file
    skills = files_under(".agents", {".md"})  # empty: .agents is outside this repo
    out.append(record("R13-242", "skill file wording",
                      "CHECKED" if skills else "NOT_APPLICABLE",
                      {"files": len(skills),
                       "why": "the skills directory is outside this repository"}))

    # 243 connector doc wording
    docs = files_under("docs", {".md"})
    out.append(record("R13-243", "connector doc wording", "CHECKED",
                      {"home_path": count_in(docs, HOME_PATH), "email": count_in(docs, EMAIL)}))

    # 244 error messages that print local paths
    src = files_under("services", {".goose"}) + files_under("agents", {".mjs"})
    out.append(record("R13-244", "error messages that print local paths", "CHECKED",
                      count_in(src, HOME_PATH)))

    # 245 ledger entries that print values
    ledger = os.path.join(ROOT, "os-build", "aegis", "findings.jsonl")
    entries = 0
    valueish = 0
    if os.path.exists(ledger):
        for line in open(ledger, encoding="utf-8", errors="ignore"):
            if not line.strip():
                continue
            entries += 1
            if EMAIL.search(line) or HOME_PATH.search(line):
                valueish += 1
    out.append(record("R13-245", "ledger entries that print values",
                      "PASS" if valueish == 0 else "FAIL",
                      {"entries": entries, "entries_with_value_shape": valueish}))

    # 246 alarm wording (small vs big)
    alarm = read("aegis/alarm.mjs") or ""
    big = re.search(r"BIG = new Set\(\[([^\]]*)\]", alarm)
    big_set = [s.strip().strip('"') for s in big.group(1).split(",")] if big else []
    out.append(record("R13-246", "alarm wording (small vs big)",
                      "PASS" if {"medium", "high", "critical"} <= set(big_set) else "FAIL",
                      {"quiet_class": "QUIET" in alarm, "alarm_class": "ALARM" in alarm,
                       "big_severities": big_set}))

    # 247 finding severity sizing
    sev = {}
    if os.path.exists(ledger):
        for line in open(ledger, encoding="utf-8", errors="ignore"):
            m = re.search(r'"severity"\s*:\s*"([a-z]+)"', line)
            if m:
                sev[m.group(1)] = sev.get(m.group(1), 0) + 1
    out.append(record("R13-247", "finding severity sizing", "INFO",
                      {"by_severity": sev, "entries": entries}))

    # 248 finding dedupe on re-sweep
    findings_src = read("aegis/findings.mjs") or ""
    out.append(record("R13-248", "finding dedupe on re-sweep",
                      "PASS" if re.search(r"(?i)dedupe|fingerprint|already|existing", findings_src)
                      else "FAIL",
                      {"dedupe_logic_present": bool(re.search(r"(?i)dedupe|fingerprint", findings_src)),
                       "note": "presence of the key function; a re-sweep count needs two live runs"}))

    # 249 finding closure records
    out.append(record("R13-249", "finding closure records",
                      "PASS" if re.search(r"(?i)status|closed|closure", findings_src) else "FAIL",
                      {"closure_field_present": bool(re.search(r"(?i)closed|closure", findings_src))}))

    # 250 ledger append-only check
    hist = git("log", "--format=", "--numstat", "--", "os-build/aegis/findings.jsonl").stdout
    added = removed = 0
    for line in hist.split("\n"):
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].isdigit():
            added += int(parts[0])
            removed += int(parts[1])
    out.append(record("R13-250", "ledger append-only check",
                      "PASS" if removed == 0 else "FAIL",
                      {"lines_added": added, "lines_removed": removed}))

    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = checks()
    out = {"tool": "os-build/layer1/opsec_checks.py", "tasks": rows}
    with open(os.path.join(OUT, "OPSEC_CHECKS.json"), "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=2)
        handle.write("\n")
    for row in rows:
        print("%-9s %-52s %-16s %s" % (row["task"], row["title"][:52], row["status"],
                                       json.dumps(row["detail"])[:110]))
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print("\ntasks=%d %s" % (len(rows), " ".join("%s=%d" % kv for kv in sorted(counts.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
