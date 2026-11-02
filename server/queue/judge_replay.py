#!/usr/bin/env python3
"""Offline judge replay harness (CB2-050).

Reads JSONL records shaped like:
  {"division": "vigiles", "first_category": "person down",
   "review_category": "person down", "review_ok": true}
and prints outcome counts only. No network, no model call.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_common  # noqa: E402
import judge  # noqa: E402


def replay_counts(rows):
    counts = {}
    for row in rows:
        verdict, _reasons = judge.combine(
            row.get("division"), row.get("first_category"),
            row.get("review_category"), row.get("review_ok", True),
            crew_common.is_flagged_category)
        counts[verdict] = counts.get(verdict, 0) + 1
    return counts


def replay_lines(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return replay_counts(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="judge_replay.py")
    parser.add_argument("path", help="JSONL file of reading pairs")
    args = parser.parse_args(argv)
    with open(args.path) as handle:
        counts = replay_lines(handle.read())
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
