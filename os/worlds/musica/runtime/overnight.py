"""musica overnight pipeline (HN-040).

One unattended session, end to end, as a single runnable job:

  python3 overnight.py --session-dir SESSIONS/overnight-001
      --brief-file BRIEFS/chipsynth.md --takes 100 --seed-base 10000

Stages: compose -> keeper pass -> variation pass -> catalogue
(--no-copy: the catalogue points at the reproducible take files,
so a 100-take session does not bloat the repo with audio copies)
-> rights check (enforced) -> board. Writes overnight-report.json
in the session dir: takes, keepers, rejects, reject rate, and the
catalogue delta (keepers this run added).

Exit code 0 on a completed run, even with rejects: rejects are a
normal outcome, not an error.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import render_board  # noqa: E402
from catalogue import build_catalogue  # noqa: E402
from compose import load_brief, run_session  # noqa: E402
from keepers import apply_keepers  # noqa: E402
from rights import check_catalogue  # noqa: E402
from similarity import apply_variation  # noqa: E402
from take_log import read_log  # noqa: E402


def run_overnight(session_dir, brief_id, brief_file, takes, seed_base):
    """Run the full pipeline. Returns the report dict."""
    started = time.time()
    params, brief_text = load_brief(brief_file)
    run_session(session_dir, brief_id, brief_text, params, takes,
                seed_base)
    keeper_summary = apply_keepers(session_dir)
    variation_summary = apply_variation(session_dir)
    catalogue = build_catalogue(session_dir, copy=False)
    violations = check_catalogue(session_dir, enforce=True)
    board = render_board(session_dir)
    with open(os.path.join(session_dir, "board.html"), "w",
              encoding="utf-8") as fh:
        fh.write(board)
    takes_logged = read_log(os.path.join(session_dir, "take_log.jsonl"))
    final_keepers = len(catalogue["tracks"])
    report = {
        "session_id": os.path.basename(os.path.abspath(session_dir)),
        "brief_id": brief_id,
        "takes": len(takes_logged),
        "keepers": final_keepers,
        "rejects": len(takes_logged) - final_keepers,
        "keeper_rejects": keeper_summary["rejects"],
        "clones": variation_summary["clones"],
        "catalogue_tracks": final_keepers,
        "catalogue_delta": final_keepers,
        "rights_violations": len(violations),
        "reject_rate": round(
            (len(takes_logged) - final_keepers) / len(takes_logged), 4)
        if takes_logged else 0,
        "elapsed_s": round(time.time() - started, 1),
    }
    with open(os.path.join(session_dir, "overnight-report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
    return report


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica overnight run")
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--brief-id", default="chipsynth")
    parser.add_argument("--brief-file", required=True)
    parser.add_argument("--takes", type=int, default=100)
    parser.add_argument("--seed-base", type=int, default=10000)
    args = parser.parse_args(argv)
    report = run_overnight(args.session_dir, args.brief_id,
                           args.brief_file, args.takes, args.seed_base)
    print("overnight takes=%d keepers=%d rejects=%d reject_rate=%.4f "
          "catalogue_delta=%d elapsed=%.1fs"
          % (report["takes"], report["keepers"], report["rejects"],
             report["reject_rate"], report["catalogue_delta"],
             report["elapsed_s"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
