"""musica failure museum (HN-042).

The reject log rendered as a page: every rejected take across
every session, with its reason, so the studio's taste is visible
in what it throws away. Fed by the take logs only.

  python3 museum.py MUSICA_DIR [--out board/museum.html]

Reason categories are read off the recorded reason text:
keeper-rule failures (duration, loudness, silence, repetition),
near-identical clones, and anything else as "other".
"""

import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import read_log  # noqa: E402


def _esc(value):
    return html.escape(str(value))


def category_of(reason):
    """Bucket a reject reason into a display category."""
    text = (reason or "").lower()
    if "near-identical" in text:
        return "clone"
    for key in ("duration", "loudness", "silence", "repetition"):
        if key in text:
            return key
    return "other"


def render_museum(musica_dir):
    """Return museum HTML for all sessions under a musica dir."""
    sessions_dir = os.path.join(musica_dir, "sessions")
    rows = []
    counts = {}
    for session_id in sorted(os.listdir(sessions_dir)):
        sdir = os.path.join(sessions_dir, session_id)
        if not os.path.isdir(sdir):
            continue
        log_path = os.path.join(sdir, "take_log.jsonl")
        if not os.path.exists(log_path):
            continue
        for take in read_log(log_path):
            if take["verdict"] != "reject":
                continue
            cat = category_of(take["reason"])
            counts[cat] = counts.get(cat, 0) + 1
            measurement = take.get("measurement", {})
            rows.append(
                "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                "<td>%s</td></tr>"
                % (_esc(take["take_id"]), _esc(session_id),
                   _esc(take["brief_id"]), _esc(cat),
                   _esc(take["reason"])))
    summary = "".join("<li>%s: %d</li>" % (_esc(k), v)
                      for k, v in sorted(counts.items()))
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        "<title>Meta Musica — failure museum</title></head><body>"
        "<h1>Meta Musica failure museum</h1>"
        "<p>What the studio throws away, and why. Every row is a "
        "rejected take from a real session log.</p>"
        "<h2>Rejects by reason</h2><ul>%s</ul>"
        "<table><tr><th>Take</th><th>Session</th><th>Brief</th>"
        "<th>Category</th><th>Reason</th></tr>%s</table></body></html>"
        % (summary or "<li>(none yet)</li>",
           "".join(rows) or "<tr><td colspan=\"5\">No rejects yet.</td></tr>"))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica failure museum")
    parser.add_argument("musica_dir")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    out = args.out or os.path.join(args.musica_dir, "board", "museum.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render_museum(args.musica_dir))
    print("museum written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
