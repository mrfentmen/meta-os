"""musica studio board (HN-032 v1, extended HN-041 v2).

Renders a session's board as static HTML from the real records
only: session.json, take_log.jsonl, catalogue.json. Nothing on the
page is invented: every take row, count, and audio source comes
from the session dir. Regenerate after each session change:

  python3 board.py SESSION_DIR [--out board.html]

v1 shows: now playing (first keeper, or an honest none-yet line),
queue (keeper titles in order), and the full take log with verdict
and reason. v2 (HN-041) adds the catalogue browser with a rights
column and session history. With no session dir at all, the board
renders the honest "no sessions yet" state (HN-053).
"""

import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import read_log  # noqa: E402


def _esc(value):
    return html.escape(str(value))


def render_board(session_dir):
    """Return board HTML for a session dir (or the empty state)."""
    session_path = os.path.join(session_dir, "session.json")
    log_path = os.path.join(session_dir, "take_log.jsonl")
    if not os.path.exists(session_path) and not os.path.exists(log_path):
        return ("<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
                "<title>Meta Musica — studio board</title></head><body>"
                "<h1>Meta Musica studio board</h1>"
                "<p>No sessions yet. Run the composition loop to start "
                "the first session; this board will show it here.</p>"
                "</body></html>")
    session = {}
    if os.path.exists(session_path):
        with open(session_path, encoding="utf-8") as fh:
            session = json.load(fh)
    takes = read_log(log_path) if os.path.exists(log_path) else []
    catalogue = {}
    catalogue_path = os.path.join(session_dir, "catalogue.json")
    if os.path.exists(catalogue_path):
        with open(catalogue_path, encoding="utf-8") as fh:
            catalogue = json.load(fh)
    keepers = [t for t in takes if t["verdict"] == "keeper"]
    rejects = [t for t in takes if t["verdict"] == "reject"]
    session_id = session.get("session_id",
                             os.path.basename(os.path.abspath(session_dir)))
    now_playing = ""
    if keepers:
        first = keepers[0]
        keeper_audio = "keepers/%s.wav" % first["take_id"]
        if not os.path.exists(os.path.join(session_dir, keeper_audio)):
            keeper_audio = first["file"]
        now_playing = (
            "<h2>Now playing</h2>"
            "<p>%s</p>"
            "<audio controls src=\"%s\"></audio>"
            % (_esc("%s %s" % (first["brief_id"], first["take_id"])),
               _esc(keeper_audio)))
    else:
        now_playing = ("<h2>Now playing</h2>"
                       "<p>No keepers yet in this session.</p>")
    queue = "".join(
        "<li>%s</li>" % _esc("%s %s" % (t["brief_id"], t["take_id"]))
        for t in keepers) or "<li>(empty)</li>"
    rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (_esc(t["take_id"]), _esc(t["verdict"]), _esc(t["reason"]),
           _esc(t["duration_s"]), _esc(t["sha256"][:12]))
        for t in takes) or "<tr><td colspan=\"5\">No takes logged yet.</td></tr>"
    rights = ""
    if catalogue.get("tracks"):
        cells = "".join(
            "<tr><td>%s</td><td>%s</td></tr>"
            % (_esc(track["title"]), _esc(track["licence"]))
            for track in catalogue["tracks"])
        rights = ("<h2>Catalogue + rights</h2><table>"
                  "<tr><th>Track</th><th>Rights</th></tr>%s</table>" % cells)
    history = ""
    if session.get("keeper_pass"):
        history = ("<h2>Session history</h2><p>Keeper pass: %d keepers, "
                   "%d rejects.</p>"
                   % (session["keeper_pass"]["keepers"],
                      session["keeper_pass"]["rejects"]))
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        "<title>Meta Musica — %s</title></head><body>"
        "<h1>Meta Musica studio board</h1>"
        "<p>Session: %s · Brief: %s · Takes: %d · Keepers: %d · "
        "Rejects: %d</p>"
        "%s<h2>Queue</h2><ol>%s</ol>"
        "<h2>Take log</h2><table>"
        "<tr><th>Take</th><th>Verdict</th><th>Reason</th>"
        "<th>Duration</th><th>Audio hash</th></tr>%s</table>"
        "%s%s</body></html>"
        % (_esc(session_id), _esc(session_id),
           _esc(session.get("brief_id", "—")), len(takes), len(keepers),
           len(rejects), now_playing, queue, rows, rights, history))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica studio board")
    parser.add_argument("session_dir")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    out = args.out or os.path.join(args.session_dir, "board.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render_board(args.session_dir))
    print("board written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
