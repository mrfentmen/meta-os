"""musica gate packet builder (HN-055).

Assembles everything Milo needs to gate-1 the lane in one folder:
the pack, the records, the catalogues, the board paths, and the
test results. The packet is lean on purpose: audio is NOT copied
(every take replays byte-identically from its log entry; the
hn029 bundle in exports/ holds the flagship session's audio).

  python3 gate_packet.py MUSICA_DIR [--out gate-packet]
      [--musica-tests tests/musica-*.test.mjs ...]
      [--full-suite-note "node suite: X run / Y pass / Z fail"]

The packet holds: README.md (gate instructions, status, limits),
pack.json, PACK.md, ADOPTIONS.md, briefs/, board.html,
museum.html, prompts/library.json, docs/DUET_SCOPE.md,
config/budget.json, records.json (per-session counts from the
logs), catalogues/ (one catalogue.json per catalogued session),
and test-results.txt (the musica test run output).
"""

import glob
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import read_log  # noqa: E402


def repo_root(musica_dir):
    """Repo root for a musica dir (…/os/worlds/musica)."""
    return os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(musica_dir))))


def build_packet(musica_dir, out_dir, musica_tests, full_suite_note=""):
    """Assemble the gate packet. Returns the packet dir."""
    os.makedirs(out_dir, exist_ok=True)
    for rel in ("pack.json", "PACK.md", "ADOPTIONS.md",
                "config/budget.json", "docs/DUET_SCOPE.md",
                "prompts/library.json"):
        src = os.path.join(musica_dir, rel)
        if os.path.exists(src):
            dst = os.path.join(out_dir, os.path.basename(rel))
            shutil.copyfile(src, dst)
    for sub, name in (("briefs", "briefs"), ("board", "board")):
        src_dir = os.path.join(musica_dir, sub)
        if os.path.isdir(src_dir):
            dst_dir = os.path.join(out_dir, name)
            os.makedirs(dst_dir, exist_ok=True)
            for fname in sorted(os.listdir(src_dir)):
                fsrc = os.path.join(src_dir, fname)
                if os.path.isfile(fsrc):
                    shutil.copyfile(fsrc, os.path.join(dst_dir, fname))
    sessions_dir = os.path.join(musica_dir, "sessions")
    records = []
    os.makedirs(os.path.join(out_dir, "catalogues"), exist_ok=True)
    for session_id in sorted(os.listdir(sessions_dir)):
        sdir = os.path.join(sessions_dir, session_id)
        if not os.path.isdir(sdir):
            continue
        log_path = os.path.join(sdir, "take_log.jsonl")
        takes = read_log(log_path) if os.path.exists(log_path) else []
        catalogue_path = os.path.join(sdir, "catalogue.json")
        tracks = 0
        if os.path.exists(catalogue_path):
            with open(catalogue_path, encoding="utf-8") as fh:
                tracks = len(json.load(fh).get("tracks", []))
            shutil.copyfile(catalogue_path, os.path.join(
                out_dir, "catalogues", "%s-catalogue.json" % session_id))
        records.append({
            "session_id": session_id,
            "takes": len(takes),
            "keepers": sum(1 for t in takes if t["verdict"] == "keeper"),
            "rejects": sum(1 for t in takes if t["verdict"] == "reject"),
            "catalogue_tracks": tracks,
        })
    with open(os.path.join(out_dir, "records.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"sessions": records}, fh, indent=2, sort_keys=True)
    root = repo_root(musica_dir)
    test_files = sorted(glob.glob(os.path.join(root, "tests",
                                                "musica-*.test.mjs")))
    if musica_tests:
        test_files = [t for t in test_files
                      if os.path.basename(t) in musica_tests]
    proc = subprocess.run(["node", "--test"] + test_files,
                          cwd=root, capture_output=True, text=True)
    with open(os.path.join(out_dir, "test-results.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(proc.stdout)
        fh.write(proc.stderr)
    total_takes = sum(r["takes"] for r in records)
    total_keepers = sum(r["keepers"] for r in records)
    readme = (
        "# Meta Musica gate packet (HN-055)\n\n"
        "Everything needed to gate-1 the Musica lane (HN-026..HN-055)\n"
        "in one folder. Branch: hana/musica. No merge without the\n"
        "boss's word.\n\n"
        "## How to gate\n\n"
        "1. Read PACK.md (status PARTIAL) and ADOPTIONS.md.\n"
        "2. Re-run the lane tests: `node --test tests/musica-*.test.mjs`\n"
        "   (their output is filed here as test-results.txt).\n"
        "3. Replay any take from its log entry:\n"
        "   `python3 os/worlds/musica/runtime/compose.py --replay \\\n"
        "   os/worlds/musica/sessions/<session>/take_log.jsonl "
        "<take-id> out.wav`\n"
        "   and compare sha256 with the log entry.\n"
        "4. Open board/board.html (studio board), board/museum.html\n"
        "   (failure museum), and the session boards under sessions/.\n"
        "5. Check the flagship bundle: "
        "os/worlds/musica/exports/musica-hn029-chipsynth-bundle.zip.\n\n"
        "## Lane totals (from records.json)\n\n"
        "- Sessions: %d\n- Takes logged: %d\n- Keepers: %d\n"
        "- Rejects: %d\n\n"
        "## Full suite note\n\n%s\n\n"
        "## Known limits (honest, not hidden)\n\n"
        "- Spark-assisted composition is builders only: no key in\n"
        "  this sandbox, no live calls sent, no model reply recorded.\n"
        "- Board audio playback is not verified in a real browser\n"
        "  (no browser in this sandbox; the pages are static HTML).\n"
        "- The Mac gate needs ffmpeg and pretty_midi installed\n"
        "  (pip install pretty_midi, MIT).\n"
        "- Catalogue audio for sessions after hn029 is reproducible\n"
        "  from the log, not committed (repo-lean policy).\n"
        "- Duet mode is scoping only (docs/DUET_SCOPE.md), no code.\n"
        "- Openverse API is unverified from this sandbox (bot check).\n"
        % (len(records), total_takes, total_keepers,
           total_takes - total_keepers,
           full_suite_note or "Full suite run: see the lane report; "
           "musica tests are filed as test-results.txt."))
    with open(os.path.join(out_dir, "README.md"), "w",
              encoding="utf-8") as fh:
        fh.write(readme)
    return out_dir


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica gate packet")
    parser.add_argument("musica_dir")
    parser.add_argument("--out", default=None)
    parser.add_argument("--musica-tests", nargs="*", default=None)
    parser.add_argument("--full-suite-note", default="")
    args = parser.parse_args(argv)
    out = args.out or os.path.join(args.musica_dir, "gate-packet")
    build_packet(args.musica_dir, out, args.musica_tests,
                 args.full_suite_note)
    print("gate packet written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
