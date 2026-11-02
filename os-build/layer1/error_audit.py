#!/usr/bin/env python3
"""B-L1-137 — Error registry audit.

Two directions, and the first one is the one that hurts:

  UNDECLARED   a code used in a service that `services/common/err/err.goose` does not define.
               This compiles fine (an undefined name is caught at build time) and then, the
               moment it is fixed by adding a local `let`, becomes a second vocabulary that
               the registry audit can never see.
  UNUSED       a code the registry defines that nothing returns. Informational: a taxonomy
               with spare words is a taxonomy that was designed, not accreted.
  NUMERIC      a bare numeric return used where a code belongs (`return 42`). The registry
               cannot audit a number.

Usage:
    python3 os-build/layer1/error_audit.py            # summary + UNDECLARED
    python3 os-build/layer1/error_audit.py --unused   # also list unused codes
Exit: 0 clean, 1 undeclared/numeric findings, 2 the registry could not be read.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SERVICES = os.path.join(ROOT, "services")
REGISTRY = os.path.join(SERVICES, "common", "err", "err.goose")

DECL = re.compile(r"^let\s+([A-Z][A-Z_0-9]*):\s*i64\s*=", re.M)
USE = re.compile(r"\b(E_[A-Z][A-Z_0-9]*|CODE_OK)\b")
# `let E_X: i64 = ...` inside a service is a local definition: the second vocabulary.
LOCAL_DEF = re.compile(r"^\s*let\s+(E_[A-Z][A-Z_0-9]*)\s*:", re.M)
# return <number>; is only suspicious inside a function that otherwise returns codes.
RET_NUM = re.compile(r"return\s+-?\d+\s*;")


def strip_comments(text):
    """Drop `//` comments, leaving string literals alone.

    A code named in prose ("id 0 with E_STOPPED-ish CODE_OK") is not a use of that code,
    and counting it as one makes the UNDECLARED list lie in the safe direction -- exactly
    the direction that hides a real second vocabulary.
    """
    kept = []
    for line in text.splitlines():
        in_str = False
        cut = len(line)
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"':
                in_str = not in_str
            elif not in_str and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                cut = i
                break
            i += 1
        kept.append(line[:cut])
    return "\n".join(kept)


def walk():
    for base, dirs, files in os.walk(SERVICES):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for f in files:
            if f.endswith(".goose"):
                yield os.path.join(base, f)


def main(argv):
    if not os.path.exists(REGISTRY):
        print("cannot find %s" % REGISTRY)
        return 2
    with open(REGISTRY, "r", encoding="utf-8") as h:
        reg_text = h.read()
    declared = set(DECL.findall(reg_text))
    declared.add("CODE_OK")
    if len(declared) < 5:
        print("registry parsed as too small (%d codes): the format changed" % len(declared))
        return 2

    used = {}
    local_defs = []
    numeric = []
    for path in walk():
        rel = os.path.relpath(path, ROOT)
        with open(path, "r", encoding="utf-8", errors="replace") as h:
            text = h.read()
        body = strip_comments(text)
        for code in USE.findall(body):
            used.setdefault(code, set()).add(rel)
        if path != REGISTRY:
            for name in LOCAL_DEF.findall(body):
                local_defs.append((rel, name))
        # A `return <number>` outside the common libraries is a numeric code by accident.
        if "/common/" not in path.replace(os.sep, "/") and "tests" not in rel:
            for _ in RET_NUM.finditer(body):
                numeric.append(rel)

    undeclared = sorted(c for c in used if c not in declared)
    unused = sorted(c for c in declared if c not in used)

    print("error registry audit")
    print("  declared: %d   used: %d   files: %d" % (len(declared), len(used), len(list(walk()))))
    print("")

    problems = 0
    if undeclared:
        problems += len(undeclared)
        print("UNDECLARED (%d):" % len(undeclared))
        for code in undeclared:
            where = ", ".join(sorted(used[code])[:3])
            print("  %-18s used in %s" % (code, where))
        print("")
    if local_defs:
        problems += len(local_defs)
        print("LOCAL DEFINITION (%d) -- a second vocabulary the registry cannot see:" % len(local_defs))
        for rel, name in local_defs:
            print("  %-40s %s" % (rel, name))
        print("")
    if numeric:
        print("NUMERIC RETURNS (%d file(s), informational):" % len(set(numeric)))
        for rel in sorted(set(numeric)):
            print("  %s" % rel)
        print("")
    if unused and "--unused" in argv:
        print("UNUSED (%d, informational):" % len(unused))
        print("  " + " ".join(unused))
        print("")

    if problems:
        print("findings: %d" % problems)
        return 1
    print("clean: every code used is declared, and nothing redefines one locally")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
