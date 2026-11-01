"""musica session report (HN-050).

The studio's daily page, generated from records: takes, keepers,
rejects, reject rate, and the best prompt. "Best prompt" is the
prompt group in this session with the highest keeper rate (ties
broken by most takes); every number comes from the session's take
log, nothing is estimated or rounded into a better story.

  python3 report.py SESSION_DIR [--out report.html]
"""

import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import read_log  # noqa: E402


def _esc(value):
    return html.escape(str(value))


def build_report(session_dir):
    """Compute the session report dict from the take log."""
    log_path = os.path.join(session_dir, "take_log.jsonl")
    takes = read_log(log_path) if os.path.exists(log_path) else []
    keepers = [t for t in takes if t["verdict"] == "keeper"]
    rejects = [t for t in takes if t["verdict"] == "reject"]
    groups = {}
    for take in takes:
        group = groups.setdefault(take["prompt"], {"takes": 0, "keepers": 0})
        group["takes"] += 1
        if take["verdict"] == "keeper":
            group["keepers"] += 1
    best = None
    for prompt, group in groups.items():
        rate = group["keepers"] / group["takes"] if group["takes"] else 0.0
        candidate = {"prompt": prompt, "takes": group["takes"],
                     "keepers": group["keepers"], "rate": round(rate, 4)}
        if best is None or (candidate["rate"], candidate["takes"]) > (
                best["rate"], best["takes"]):
            best = candidate
    reasons = {}
    for take in rejects:
        reasons[take["reason"]] = reasons.get(take["reason"], 0) + 1
    spark_attempts = sum(1 for t in takes if t.get("spark_assist"))
    return {
        "session_id": os.path.basename(os.path.abspath(session_dir)),
        "takes": len(takes),
        "keepers": len(keepers),
        "rejects": len(rejects),
        "reject_rate": round(len(rejects) / len(takes), 4) if takes else 0,
        "best_prompt": best,
        "keeper_take_ids": [t["take_id"] for t in keepers],
        "reject_reasons": reasons,
        "spark_attempts": spark_attempts,
    }


def render_report(session_dir):
    """Return the session report page HTML."""
    report = build_report(session_dir)
    best = report["best_prompt"]
    best_html = ("<p>No prompts logged yet.</p>" if best is None else
                 "<p>Best prompt: %s<br>Takes: %d · Keepers: %d · "
                 "Rate: %.4f</p>"
                 % (_esc(best["prompt"]), best["takes"], best["keepers"],
                    best["rate"]))
    reasons = "".join("<li>%s: %d</li>" % (_esc(r), n) for r, n in
                      sorted(report["reject_reasons"].items()))
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        "<title>Meta Musica — session report %s</title></head><body>"
        "<h1>Meta Musica session report</h1>"
        "<p>Session: %s</p>"
        "<p>Takes: %d · Keepers: %d · Rejects: %d · "
        "Reject rate: %.4f</p>"
        "<h2>Best prompt</h2>%s"
        "<h2>Keepers</h2><p>%s</p>"
        "<h2>Reject reasons</h2><ul>%s</ul>"
        "<p>Spark assist attempts recorded: %d</p></body></html>"
        % (_esc(report["session_id"]), _esc(report["session_id"]),
           report["takes"], report["keepers"], report["rejects"],
           report["reject_rate"], best_html,
           _esc(", ".join(report["keeper_take_ids"]) or "(none)"),
           reasons or "<li>(none)</li>", report["spark_attempts"]))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica session report")
    parser.add_argument("session_dir")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    out = args.out or os.path.join(args.session_dir, "report.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render_report(args.session_dir))
    report = build_report(args.session_dir)
    print("report takes=%d keepers=%d rejects=%d best_rate=%s"
          % (report["takes"], report["keepers"], report["rejects"],
             report["best_prompt"]["rate"]
             if report["best_prompt"] else "n/a"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
