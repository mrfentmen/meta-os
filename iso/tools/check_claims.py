#!/usr/bin/env python3
"""check_claims.py — fail when a document claims a count the tree no longer has.

A number written into a doc goes stale the moment the tree changes, and nobody
re-reads the doc to notice. This does: each claim in `iso/claims.json` names a
document, a pattern that finds its number, and the source that decides the
real value. The tool recomputes the source and compares.

    python3 iso/tools/check_claims.py            the repo
    python3 iso/tools/check_claims.py --json     for a script

Sources: `checker` (the static checker's pass count), `doctor` (rows passing
against a fresh staging install), `tests` (ISO test files), and
`glob:<pattern>` (files matching a glob, relative to the root).

A claim whose pattern no longer matches is MISSING, not OK: a doc rewritten
out from under the check must fail loudly, or the check is decoration.

Exit 0 when every claim is true, 1 when any is stale or missing, 2 on bad
usage. It reads; the only thing it writes is a temp staging tree.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ISO = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ISO.parent

WORDS = {word: value for value, word in enumerate(
    ("zero", "one", "two", "three", "four", "five",
     "six", "seven", "eight", "nine", "ten"), start=0)}


def as_number(found, kind):
    if kind == "word":
        return WORDS.get(found.lower())
    try:
        return int(found)
    except ValueError:
        return None


def compute(source, root, cache):
    if source in cache:
        return cache[source]

    if source == "checker":
        run = subprocess.run(
            [sys.executable, str(root / "iso" / "tools" / "check_iso_config.py"), "--json"],
            capture_output=True, text=True)
        value = json.loads(run.stdout)["counts"]["pass"]
    elif source == "doctor":
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["bash", str(root / "iso" / "tools" / "apply.sh"), "--root", tmp],
                           capture_output=True, text=True, check=True)
            run = subprocess.run(
                [sys.executable, str(root / "iso" / "base" / "meta-doctor.py"),
                 "--root", tmp, "--json"], capture_output=True, text=True)
            value = json.loads(run.stdout)["summary"]["pass"]
    elif source == "tests":
        value = len(list((root / "tests").glob("test_iso_*.py")))
    elif source.startswith("glob:"):
        value = len(list(root.glob(source[5:])))
    else:
        raise ValueError("unknown source %r" % source)

    cache[source] = value
    return value


def main(argv):
    root = DEFAULT_ROOT
    claims_path = None
    as_json = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--root" and i + 1 < len(argv):
            root = Path(argv[i + 1]).expanduser().resolve()
            i += 2
        elif arg == "--claims" and i + 1 < len(argv):
            claims_path = Path(argv[i + 1]).expanduser().resolve()
            i += 2
        elif arg == "--json":
            as_json = True
            i += 1
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        else:
            print("claims: unknown argument %s" % arg, file=sys.stderr)
            return 2

    claims_path = claims_path or (root / "iso" / "claims.json")
    try:
        claims = json.loads(claims_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("claims: no claims file at %s" % claims_path, file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print("claims: %s does not parse (%s)" % (claims_path, exc), file=sys.stderr)
        return 2

    cache, results = {}, []
    for claim in claims:
        doc = root / claim["doc"]
        entry = {"id": claim["id"], "doc": claim["doc"], "line": None,
                 "source": claim["source"], "said": None, "tree": None,
                 "verdict": "OK"}
        if not doc.is_file():
            entry["verdict"] = "MISSING"
            entry["said"] = "document does not exist"
            results.append(entry)
            continue
        text = doc.read_text(encoding="utf-8")
        match = re.search(claim["pattern"], text)
        if not match:
            entry["verdict"] = "MISSING"
            entry["said"] = "pattern not found"
            results.append(entry)
            continue

        entry["line"] = text.count("\n", 0, match.start()) + 1
        entry["said"] = match.group(1)
        try:
            value = compute(claim["source"], root, cache)
        except Exception as exc:  # noqa: BLE001
            entry["verdict"] = "ERROR"
            entry["said"] = "%s (%s)" % (entry["said"], exc)
            results.append(entry)
            continue
        entry["tree"] = value

        said = as_number(match.group(1), claim.get("kind", "number"))
        if said is None or said != value:
            entry["verdict"] = "STALE"
        results.append(entry)

    stale = [r for r in results if r["verdict"] != "OK"]

    if as_json:
        print(json.dumps({"checked": len(results), "not_ok": stale,
                          "results": results}, indent=2))
    else:
        print("claims: %d checked against %s" % (len(results), root))
        for r in results:
            where = "%s:%s" % (r["doc"], r["line"]) if r["line"] else r["doc"]
            said = "says %s" % r["said"] if r["said"] is not None else ""
            tree = "tree has %s" % r["tree"] if r["tree"] is not None else ""
            print("%-8s %-42s %-18s %s %s"
                  % (r["verdict"], where, r["id"], said, tree))
        print()
        print("CLAIMS: %s" % ("OK — every claim matches the tree" if not stale
                              else "%d claim(s) wrong" % len(stale)))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
