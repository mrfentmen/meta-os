#!/usr/bin/env python3
"""Edge-case contract for the xcheck runner (NC-046).
Run: python3 tests/edge_check.py [--list]
- empty SMILES -> ValueError (explicit, not silent zero)
- salts (multi-fragment, e.g. Na+.[Cl-]) -> computes on the whole (documented behavior)
- charged species (e.g. acetate) -> computes (charge is not a Delaney input)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from xcheck import predict  # noqa: E402


def main():
    if "--list" in sys.argv:
        print("edge cases: empty SMILES; salt Na+.[Cl-]; charged acetate CC(=O)[O-]")
        return 0
    cases = [
        ("empty", "", True),
        ("salt", "[Na+].[Cl-]", False),
        ("charged", "CC(=O)[O-]", False),
    ]
    ok = True
    for name, smi, want_fail in cases:
        try:
            v = predict(smi)
            result = "computed logS=%+.3f" % v
            failed = want_fail
        except ValueError as e:
            result = "ValueError: %s" % e
            failed = not want_fail
        print("%s %-8s %s" % ("FAIL" if failed else "ok", name, result))
        ok = ok and not failed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
