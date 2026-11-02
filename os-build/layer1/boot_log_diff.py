#!/usr/bin/env python3
"""boot_log_diff.py — compare two boot logs structurally.

Two boots of the same milestone should differ only in the numbers that depend on timing
(tick counts, quiet-line order). A firmware change or a lost program shows up as a
missing key, not as a line that moved.

Differences are classified:

  REGRESSION  a scalar present in A is missing or different in B (alive, a summary)
  NUMBER      same numeric key, different value (frames, ticks, heap)
  LIST        list content differs (program sizes, typed shell commands) — reported, not failed
  EXTRA       a key present only in B

Exit: 0 identical structure, 1 differences found, 2 missing input.
Usage: boot_log_diff.py <a.json|a.log> <b.json|b.log>
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from boot_log_parse import parse  # noqa: E402

CRITICAL = ("alive", "banner", "panic", "timer", "keyboard")


def load(path):
    p = pathlib.Path(path)
    text = p.read_text(errors="replace")
    if p.suffix == ".json":
        return json.loads(text)
    return parse(text)


def flatten(doc, prefix=""):
    out = {}
    for key, value in doc.items():
        if key in ("unparsed", "counts", "source"):
            continue
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, name + "."))
        elif isinstance(value, list):
            # Keep lists as lists: encoding them to strings makes every content
            # difference look like a lost capability.
            out[name] = value
        else:
            out[name] = value
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    for path in argv[:2]:
        if not pathlib.Path(path).is_file():
            print(f"boot_log_diff: missing {path}", file=sys.stderr)
            return 2
    a, b = flatten(load(argv[0])), flatten(load(argv[1]))
    regressions, numbers, extras, lists = [], [], [], []
    for key, value in a.items():
        if key not in b:
            regressions.append(f"{key}: present in A, missing in B (A={value!r})")
        elif b[key] != value:
            if isinstance(value, list) and isinstance(b[key], list):
                # A list difference is content, not a lost capability: two runs
                # load the same programs at slightly different sizes, and a shell
                # may have been typed into one boot and not the other.
                lists.append(f"{key}: {len(value)} -> {len(b[key])} entries")
            elif isinstance(value, (int, float)) and isinstance(b[key], (int, float)):
                numbers.append(f"{key}: {value} -> {b[key]}")
            else:
                regressions.append(f"{key}: {value!r} -> {b[key]!r}")
    for key in b:
        if key not in a:
            extras.append(f"{key}: only in B ({b[key]!r})")

    print(f"boot_log_diff: {argv[0]} vs {argv[1]}")
    print(f"  regressions {len(regressions)}  number changes {len(numbers)}  "
          f"list changes {len(lists)}  extras {len(extras)}")
    for group, label in ((regressions, "REGRESSION"), (numbers, "NUMBER"),
                         (lists, "LIST"), (extras, "EXTRA")):
        for line in group:
            print(f"  {label:10} {line}")
    if regressions:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
