#!/usr/bin/env python3
"""Science-lab selftest (tasks 73-74): molecule data + cycle parser.

Validates every embedded molecule JSON against data/meta.json (counts,
bond endpoints, element symbols, formula tally) and parses
labs/cycles/ledger.jsonl the way science-lab-review/index.html does
(required fields, verdict vocabulary, recorded levels, per-claim
source files present, score.md verdict agreement).

Headless-safe: stdlib only, no browser, no network. Exit 0 on pass.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOL = ROOT / "labs" / "molecules" / "data"
CYCLES = ROOT / "labs" / "cycles"
REVIEW = ROOT / "labs" / "science-lab-review" / "index.html"

FAILURES = []


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)
    return cond


def tally_formula(symbols):
    counts = Counter(symbols)
    order = ["C", "H"] + sorted(s for s in counts if s not in ("C", "H"))
    parts = []
    for s in order:
        if s not in counts:
            continue
        n = counts[s]
        parts.append(s if n == 1 else "%s%d" % (s, n))
    return "".join(parts)


def test_molecules():
    meta = json.loads((MOL / "meta.json").read_text())
    compounds = meta.get("compounds", [])
    check(len(compounds) > 0, "molecule meta.json carries no compounds")
    seen = set()
    for c in compounds:
        for k in ("id", "name", "cid", "formula", "weight"):
            check(k in c, "meta %s missing %s" % (c.get("id", "?"), k))
        p = MOL / ("%s.json" % c["id"])
        check(p.exists(), "missing data file %s" % p.name)
        if not p.exists():
            continue
        mol = json.loads(p.read_text())
        check(mol.get("cid") == c["cid"], "%s cid %s != meta %s" % (c["id"], mol.get("cid"), c["cid"]))
        atoms, bonds = mol.get("atoms", []), mol.get("bonds", [])
        check(len(atoms) > 0, "%s has no atoms" % c["id"])
        for i, a in enumerate(atoms):
            check(all(isinstance(a.get(k), (int, float)) for k in ("x", "y", "z")),
                  "%s atom %d coords" % (c["id"], i))
            check(a.get("sym") in ("C", "H", "O", "N"), "%s atom %d sym %r" % (c["id"], i, a.get("sym")))
        for i, b in enumerate(bonds):
            check(isinstance(b.get("a"), int) and 0 <= b["a"] < len(atoms),
                  "%s bond %d endpoint a" % (c["id"], i))
            check(isinstance(b.get("b"), int) and 0 <= b["b"] < len(atoms),
                  "%s bond %d endpoint b" % (c["id"], i))
            check(b.get("o") in (1, 2, 3), "%s bond %d order" % (c["id"], i))
        tally = tally_formula([a["sym"] for a in atoms])
        check(tally == c["formula"], "%s formula tally %s != meta %s" % (c["id"], tally, c["formula"]))
        seen.add(c["id"])
    check(seen == {p.stem for p in MOL.glob("*.json") if p.name != "meta.json"},
          "meta.json compound set != data/*.json files")


def test_cycles():
    ledger = CYCLES / "ledger.jsonl"
    check(ledger.exists(), "labs/cycles/ledger.jsonl missing")
    if not ledger.exists():
        return
    entries = []
    for n, line in enumerate(ledger.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError as ex:
            check(False, "ledger line %d not JSON: %s" % (n, ex))
            continue
        entries.append(e)
        for k in ("cycle_id", "verdict", "level", "metric", "observed", "expected"):
            check(k in e, "ledger line %d missing %s" % (n, k))
        check(e.get("verdict") in ("MATCH", "DIFFER"), "ledger line %d verdict %r" % (n, e.get("verdict")))
        check(isinstance(e.get("level"), int) and 1 <= e["level"] <= 3,
              "ledger line %d level %r not a recorded 1-3" % (n, e.get("level")))
    check(len(entries) > 0, "ledger.jsonl carries no entries")
    for e in entries:
        d = CYCLES / e["cycle_id"]
        check(d.is_dir(), "missing cycle directory labs/cycles/%s (empty-state path)" % e["cycle_id"])
        if not d.is_dir():
            continue
        for f in ("score.md", "record.md", "prereg.md", "run.py"):
            check((d / f).exists(), "%s missing source file %s" % (e["cycle_id"], f))
        score = (d / "score.md").read_text() if (d / "score.md").exists() else ""
        m = re.search(r"Verdict:\s*(MATCH|DIFFER)", score)
        check(m is not None, "%s score.md carries no Verdict line" % e["cycle_id"])
        if m:
            check(m.group(1) == e["verdict"],
                  "%s score verdict %s != ledger %s" % (e["cycle_id"], m.group(1), e["verdict"]))


def test_review_page_honesty():
    src = REVIEW.read_text() if REVIEW.exists() else ""
    check(REVIEW.exists(), "science-lab-review/index.html missing")
    if not src:
        return
    for pat in ("level + 1", "level+1", "level +1", "Math.max(level", "level || 3"):
        check(pat not in src, "review page may upgrade levels (%r found)" % pat)
    check("never" in src and "recorded" in src, "review page states the recorded-level rule")
    check('data-empty="no-such-cycle"' in src, "review page has the missing-cycle empty state")


def main():
    test_molecules()
    test_cycles()
    test_review_page_honesty()
    if FAILURES:
        print("SELFTEST FAIL (%d):" % len(FAILURES))
        for f in FAILURES:
            print(" - " + f)
        return 1
    print("SELFTEST PASS: molecules + cycles + review honesty")
    return 0


if __name__ == "__main__":
    sys.exit(main())
