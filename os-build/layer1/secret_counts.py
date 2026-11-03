#!/usr/bin/env python3
"""R13-151..175 — secret-hygiene count passes. Counts only, never a value.

The rule from AEGIS_SPEC.md and from `aegis/secrets.mjs`: a match is recorded as where and
what kind, never as what. This tool goes further than the tree scanner because 15 of the 25
tasks name **commit ranges**: it reads `git log -p` for the added lines only and reports
counts. No path, no line number, no matched text reaches the record.

Two guards make an empty result checkable:
  * `files_read` and `lines_read` are reported, so "0 matches" cannot mean "0 bytes opened".
  * a self-check re-scans the finished record with every pattern in this file and refuses to
    write if anything matches. A counts record that trips its own scanner is the leak.

Pattern honesty: some of the 25 named patterns have no distinct local definition (upstash,
firebase, sendgrid keys are shapes, not formats this tree contains). Those use a stated
regex -- stated here, in the tool that is committed -- and the record carries that regex's
SHA-256 rather than its text, so a later run can tell whether a count moved because the tree
changed or because the definition did, without the record holding a pattern a scanner would
have to read past.

Usage: python3 os-build/layer1/secret_counts.py
Exit: 0 wrote a record that passed its own self-check, 4 self-check failed (record not written).
"""
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "os-build", "round13", "aegis")

SKIP_DIRS = {".git", "node_modules", "target", "vendor", "dist", ".next", "build"}
TEXT_EXT = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".json", ".jsonl", ".md", ".txt", ".yml",
            ".yaml", ".toml", ".rs", ".go", ".py", ".sh", ".css", ".html", ".htm", ".svg",
            ".goose", ".lobster", ".c", ".h", ".lock", ".ini", ".cfg", ".conf", ".xml",
            ".env"}

PATTERNS = {
    "generic api key pattern": [r"\b(?:api[_-]?key|apikey)\s*[:=]\s*[\"'][^\"'\s]{16,}[\"']"],
    "bearer token pattern": [r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}"],
    "private key block pattern": [r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"],
    "password assignment pattern": [r"\b(?:passwd|password|pwd)\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"],
    "aws-style key pattern": [r"\bAKIA[0-9A-Z]{16}\b"],
    "github token pattern": [r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"],
    "upstash-style token pattern": [r"\bAX[A-Za-z0-9_-]{30,}\b"],
    "stripe-style key pattern": [r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"],
    "jwt pattern": [r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"],
    "basic-auth in URL pattern": [r"[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@"],
    "ssh key path mention": [r"(?:\.ssh/|id_rsa\b|id_ed25519\b)"],
    "env file mention": [r"(?:\.env\b|process\.env\[)"],
    "high-entropy string bucket": [r"[\"'][A-Za-z0-9+/=_-]{40,}[\"']"],
    "webhook secret pattern": [r"\bwhsec_[A-Za-z0-9]{16,}\b"],
    "session cookie pattern": [r"(?:set-cookie\s*:|session[_-]?cookie\s*[:=])"],
    "database connection string pattern": [r"\b(?:postgres|postgresql|mysql|mongodb|redis)://"],
    "oauth client secret pattern": [r"\bclient[_-]?secret\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"],
    "encryption key assignment pattern": [r"\b(?:encryption|aes|fernet)[_-]?key\s*[:=]"],
    "signing secret pattern": [r"\b(?:signing|hmac)[_-]?(?:secret|key)\s*[:=]"],
    "redis URL with embedded password pattern": [r"\bredis://[^@\s/]*:[^@\s]+@"],
    "postgres URL with embedded password pattern": [r"\bpostgres(?:ql)?://[^@\s/]*:[^@\s]+@"],
    "mongodb URL with embedded password pattern": [r"\bmongodb(?:\+srv)?://[^@\s/]*:[^@\s]+@"],
    "firebase-style key pattern": [r"\bAIza[0-9A-Za-z_-]{35}\b"],
    "sendgrid-style key pattern": [r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{20,}\b"],
    "credential pair in config pattern": [r"(?is)\b(?:user|username)\s*[:=][^\n]{0,60}\n[^\n]{0,40}\b(?:pass|password)\s*[:=]"],
}

# task -> (pattern, scope, argument)
#   scope "commits": git log over the range, added lines only
#   scope "tree":    working tree under the given path
TASKS = [
    ("R13-151", "generic api key pattern", "commits", ("2026-10-26", "2026-10-28")),
    ("R13-152", "bearer token pattern", "commits", ("2026-10-29", "2026-10-30")),
    ("R13-153", "private key block pattern", "commits", ("2026-10-31", "2026-10-31")),
    ("R13-154", "password assignment pattern", "commits", ("2026-11-01", "2026-11-01")),
    ("R13-155", "aws-style key pattern", "commits", ("2026-11-02", "2026-11-02")),
    ("R13-156", "github token pattern", "commits", ("2026-10-26", "2026-10-28")),
    ("R13-157", "upstash-style token pattern", "commits", ("2026-10-29", "2026-10-30")),
    ("R13-158", "stripe-style key pattern", "commits", ("2026-10-31", "2026-10-31")),
    ("R13-159", "jwt pattern", "commits", ("2026-11-01", "2026-11-01")),
    ("R13-160", "basic-auth in URL pattern", "commits", ("2026-11-02", "2026-11-02")),
    ("R13-161", "ssh key path mention", "commits", ("2026-10-26", "2026-10-28")),
    ("R13-162", "env file mention", "commits", ("2026-10-29", "2026-10-30")),
    ("R13-163", "high-entropy string bucket", "commits", ("2026-10-31", "2026-10-31")),
    ("R13-164", "webhook secret pattern", "commits", ("2026-11-01", "2026-11-01")),
    ("R13-165", "session cookie pattern", "commits", ("2026-11-02", "2026-11-02")),
    ("R13-166", "database connection string pattern", "tree", ("services",)),
    ("R13-167", "oauth client secret pattern", "tree", ("agents", "relay")),
    ("R13-168", "encryption key assignment pattern", "tree", ("crates",)),
    ("R13-169", "signing secret pattern", "tree", ("board", "site")),
    ("R13-170", "redis URL with embedded password pattern", "tree", ("server",)),
    ("R13-171", "postgres URL with embedded password pattern", "tree", ("os",)),
    ("R13-172", "mongodb URL with embedded password pattern", "tree", ("tests",)),
    ("R13-173", "firebase-style key pattern", "tree", ("face",)),
    ("R13-174", "sendgrid-style key pattern", "tree", ("docs", "os-build")),
    ("R13-175", "credential pair in config pattern", "tree", ("image", ".")),
]


def git(args, stdin=None):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          input=stdin, errors="replace")


def scan_commits(pattern, start, end):
    """Added lines only, across the range. Returns counts, never content."""
    proc = git(["log", "--since=%s 00:00" % start, "--until=%s 23:59" % end,
                "--no-color", "-p", "--unified=0", "--pretty=format:@@%H"])
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[:200], "commits": 0, "lines": 0, "files": 0,
                "matches": 0, "files_with_matches": 0}
    rex = re.compile(pattern)
    commits = set()
    files = set()
    hits = 0
    hit_files = set()
    lines = 0
    current_commit = None
    current_file = None
    for line in proc.stdout.split("\n"):
        if line.startswith("@@"):
            if line.startswith("@@") and len(line) > 2 and re.fullmatch(r"@@[0-9a-f]{7,}", line):
                current_commit = line[2:]
                commits.add(current_commit)
            continue
        if line.startswith("+++ b/"):
            current_file = line[6:]
            files.add(current_file)
            continue
        if line.startswith("+") and not line.startswith("+++"):
            lines += 1
            if rex.search(line):
                hits += 1
                if current_file:
                    hit_files.add(current_file)
    return {"commits": len(commits), "lines": lines, "files": len(files), "matches": hits,
            "files_with_matches": len(hit_files)}


def scan_tree(pattern, roots):
    rex = re.compile(pattern)
    files = lines = hits = 0
    hit_files = 0
    seen = set()
    for root in roots:
        base = os.path.join(ROOT, root)
        if not os.path.exists(base):
            continue
        walker = [(base, [], [os.path.basename(base)])] if os.path.isfile(base) else os.walk(base)
        for dirpath, dirnames, filenames in walker:
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                path = os.path.join(dirpath, name)
                if path in seen:
                    continue
                seen.add(path)
                ext = os.path.splitext(name)[1].lower()
                if ext not in TEXT_EXT and not name.startswith(".env"):
                    continue
                try:
                    if os.path.getsize(path) > 2 * 1024 * 1024:
                        continue
                    text = open(path, "r", encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                files += 1
                file_hits = 0
                for line in text.split("\n"):
                    lines += 1
                    if rex.search(line):
                        hits += 1
                        file_hits += 1
                if file_hits:
                    hit_files += 1
    return {"files": files, "lines": lines, "matches": hits, "files_with_matches": hit_files}


def self_check(record_text):
    """Re-scan the finished record. Any hit means the record carries a value shape."""
    bad = []
    for name, patterns in PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, record_text):
                bad.append(name)
                break
    return bad


def main():
    os.makedirs(OUT, exist_ok=True)
    records = []
    for task, pattern, scope, arg in TASKS:
        rex = PATTERNS[pattern][0]
        if scope == "commits":
            counts = scan_commits(rex, arg[0], arg[1])
            scope_text = "%s..%s commits (added lines)" % arg
        else:
            counts = scan_tree(rex, list(arg))
            scope_text = "working tree: %s" % ", ".join(arg)
        # An empty range and an empty result are different sentences. The tree's first commit
        # is 2026-10-28, so 2026-10-26..27 is a range with no commits in it -- calling that
        # "0 matches" would read as a clean pass over history that was never scanned.
        if scope == "commits" and counts.get("commits", 0) == 0:
            status = "NO_COMMITS_IN_RANGE"
        elif counts.get("error"):
            status = "BLOCKED"
        elif counts.get("files", 0) == 0:
            status = "NO_FILES_READ"
        else:
            status = "SCANNED"
        records.append({
            "task": task,
            "category": pattern,
            "status": status,
            "scope": scope_text,
            "pattern_sha256": hashlib.sha256(rex.encode()).hexdigest()[:16],
            "counts": counts,
            "confidence": "confirmed" if pattern in (
                "private key block pattern", "aws-style key pattern", "github token pattern",
                "stripe-style key pattern", "jwt pattern", "webhook secret pattern",
                "firebase-style key pattern", "sendgrid-style key pattern") else "review",
        })

    out = {
        "tool": "os-build/layer1/secret_counts.py",
        "rule": "counts and file counts only; no value, no matched string, no line",
        "tasks": records,
    }
    text = json.dumps(out, indent=2) + "\n"
    bad = self_check(text)
    if bad:
        print("SELF-CHECK FAILED: the record matches its own patterns: %s" % ", ".join(bad))
        print("record NOT written")
        return 4
    with open(os.path.join(OUT, "SECRET_COUNTS.json"), "w", encoding="utf-8") as handle:
        handle.write(text)

    print("%-9s %-44s %-20s %-22s %s" % ("task", "category", "status", "scope", "matches/files"))
    for rec in records:
        c = rec["counts"]
        print("%-9s %-44s %-20s %-22s %d / %d (read %d files, %d lines)%s" % (
            rec["task"], rec["category"], rec["status"], rec["scope"][:22], c["matches"],
            c["files_with_matches"], c["files"], c["lines"],
            "  ERROR " + c["error"] if c.get("error") else ""))
    total = sum(r["counts"]["matches"] for r in records)
    print("\ntasks=%d matches_total=%d self_check=pass" % (len(records), total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
