"""musica prompt library (HN-043).

The prompts that produced keepers, filed as a reusable library
with their keeper rates. Built from the take logs only: every
distinct prompt string groups its takes, and the keeper rate is
keepers / takes for that group. No rate is invented: a prompt
with no keepers files at 0.0, and a prompt with no takes does
not appear at all.

  python3 library.py MUSICA_DIR [--out prompts/library.json]
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import read_log  # noqa: E402


def build_library(musica_dir):
    """Scan all session logs into prompt groups with keeper rates."""
    sessions_dir = os.path.join(musica_dir, "sessions")
    groups = {}
    for session_id in sorted(os.listdir(sessions_dir)):
        sdir = os.path.join(sessions_dir, session_id)
        if not os.path.isdir(sdir):
            continue
        log_path = os.path.join(sdir, "take_log.jsonl")
        if not os.path.exists(log_path):
            continue
        for take in read_log(log_path):
            group = groups.setdefault(take["prompt"], {
                "prompt": take["prompt"],
                "brief_id": take["brief_id"],
                "takes": 0,
                "keepers": 0,
                "keeper_take_ids": [],
                "sessions": [],
            })
            group["takes"] += 1
            if take["verdict"] == "keeper":
                group["keepers"] += 1
                group["keeper_take_ids"].append(
                    "%s/%s" % (session_id, take["take_id"]))
            if session_id not in group["sessions"]:
                group["sessions"].append(session_id)
    library = []
    for group in groups.values():
        group["keeper_rate"] = round(
            group["keepers"] / group["takes"], 4) if group["takes"] else 0.0
        library.append(group)
    library.sort(key=lambda g: (-g["keeper_rate"], -g["takes"]))
    return {"prompts": library}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica prompt library")
    parser.add_argument("musica_dir")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    out = args.out or os.path.join(args.musica_dir, "prompts",
                                   "library.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    library = build_library(args.musica_dir)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(library, fh, indent=2, sort_keys=True)
    for group in library["prompts"]:
        print("%s takes=%d keepers=%d rate=%.4f"
              % (group["brief_id"], group["takes"], group["keepers"],
                 group["keeper_rate"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
