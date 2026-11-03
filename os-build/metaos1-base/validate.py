#!/usr/bin/env python3
"""Validate the MetaOS 1.0 base slice (Hana lane, slice 1). Stdlib only.

Checks, each printed as PASS/FAIL:
  1. packages.txt parses: sections KEEP/ADD/REMOVE, package names are
     lowercase archive-style names, no duplicates across sections.
  2. firstboot script passes `sh -n` and contains no prompt (read),
     no credential word, and no network tool.
  3. mimeapps.list maps only plain text, image, and PDF types, and
     every .desktop it names is covered by a package in packages.txt.
  4. No new file in this slice contains a forbidden artwork term or a
     credential-looking assignment.
  5. The working tree touches no frozen path (kernel/src/syscalls.rs).

Exit 0 only if every check passes. This validates internal
consistency only — it does not prove an ISO boots (see README.md).
"""
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
FAILURES = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILURES.append(name)


def main():
    # 1. packages.txt
    pkg_text = (BASE / "packages.txt").read_text()
    sections = {"KEEP": [], "ADD": [], "REMOVE": []}
    current = None
    for raw in pkg_text.splitlines():
        line = raw.strip()
        if line.startswith("# KEEP"):
            current = "KEEP"
        elif line.startswith("# ADD"):
            current = "ADD"
        elif line.startswith("# REMOVE"):
            current = "REMOVE"
        elif not line or line.startswith("#"):
            continue
        elif current is not None:
            sections[current].append(line)
    names = sections["KEEP"] + sections["ADD"] + sections["REMOVE"]
    name_ok = all(re.fullmatch(r"[a-z0-9][a-z0-9.+_-]*", n) for n in names)
    check("packages: names are archive-style", name_ok, str(names))
    check("packages: no duplicates", len(names) == len(set(names)),
          f"duplicates: {[n for n in set(names) if names.count(n) > 1]}")
    check("packages: REMOVE is empty in slice 1", sections["REMOVE"] == [],
          str(sections["REMOVE"]))
    check("packages: ADD is non-empty", len(sections["ADD"]) > 0)

    # 2. firstboot script
    script = BASE / "firstboot" / "metaos1-firstboot.sh"
    syntax = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True)
    check("firstboot: sh -n clean", syntax.returncode == 0, syntax.stderr.strip())
    body = script.read_text()
    # Code lines only: header comments explain what the script does NOT
    # do, so they legitimately name the things it avoids.
    code = "\n".join(l for l in body.splitlines()
                      if not l.strip().startswith("#"))
    check("firstboot: no interactive prompt", "\nread " not in code and "read -" not in code)
    for word in ("password", "passwd", "token", "api_key", "secret", "credential"):
        check(f"firstboot: no credential word '{word}'", word not in code.lower())
    for tool in ("curl", "wget", "ssh", "scp"):
        check(f"firstboot: no network tool '{tool}'", tool not in code)
    unit = (BASE / "firstboot" / "metaos1-firstboot.service").read_text()
    check("firstboot: unit is oneshot + done-marker conditioned",
          "Type=oneshot" in unit and "metaos1-firstboot.done" in unit)
    check("firstboot: unit exec matches script path",
          "ExecStart=/usr/local/bin/metaos1-firstboot" in unit)

    # 3. mimeapps.list
    mime = (BASE / "defaults" / "mimeapps.list").read_text()
    desktop_to_package = {
        "mousepad.desktop": "mousepad",
        "ristretto.desktop": "ristretto",
        "evince.desktop": "evince",
    }
    allowed_types = {"text/plain", "image/png", "image/jpeg", "application/pdf"}
    mapped = {}
    for line in mime.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            mapped[key.strip()] = value.strip()
    check("mimeapps: only plain text, image, PDF types",
          set(mapped) <= allowed_types, str(sorted(set(mapped) - allowed_types)))
    check("mimeapps: no browser type mapped", "text/html" not in mapped)
    uncovered = [d for d in mapped.values()
                 if desktop_to_package.get(d) not in names]
    check("mimeapps: every desktop covered by packages.txt", not uncovered, str(uncovered))

    # 4. forbidden terms / credential-looking assignments in slice files
    forbidden = ("apple", "safari", "macos", "iphone", "ipad")
    cred_re = re.compile(r"(?i)\b(password|api_key|apikey|secret|token)\s*=")
    for path in sorted(BASE.rglob("*")):
        if not path.is_file() or path.name == "validate.py":
            continue
        text = path.read_text(errors="ignore")
        for term in forbidden:
            check(f"no forbidden term '{term}' in {path.relative_to(BASE)}",
                  term not in text.lower())
        check(f"no credential assignment in {path.relative_to(BASE)}",
              cred_re.search(text) is None)

    # 5. frozen path untouched
    status = subprocess.run(["git", "-C", str(BASE.parent.parent),
                             "status", "--porcelain"],
                            capture_output=True, text=True).stdout
    check("frozen kernel/src/syscalls.rs untouched",
          "kernel/src/syscalls.rs" not in status)

    print(f"\n{'OK' if not FAILURES else 'FAILED'}: {len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
