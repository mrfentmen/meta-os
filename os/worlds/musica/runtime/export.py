"""musica catalogue export bundle (HN-049).

One command produces a single downloadable bundle (a zip) with the
session's tracks, catalogue, and rights:

  python3 export.py SESSION_DIR [--out exports/musica-SESSION.zip]

The zip holds catalogue.json, rights.json, normalization.json and
midi.json when they exist, the board page, and every audio/MIDI
file the catalogue references. Files that do not exist on disk
(for example reproducible take audio that was never rendered in
this checkout) are NOT silently skipped: they are listed under
"missing" in the bundle.json manifest inside the zip, so the
bundle never pretends to be complete when it is not.
"""

import datetime
import json
import os
import sys
import zipfile


def export_bundle(session_dir, out_path):
    """Build the bundle zip. Returns the manifest dict."""
    session_id = os.path.basename(os.path.abspath(session_dir))
    catalogue_path = os.path.join(session_dir, "catalogue.json")
    with open(catalogue_path, encoding="utf-8") as fh:
        catalogue = json.load(fh)
    members = []
    missing = []

    def add(rel_path, arcname=None):
        src = os.path.join(session_dir, rel_path)
        if os.path.exists(src):
            members.append((src, arcname or rel_path))
            return True
        missing.append(rel_path)
        return False

    for doc in ("catalogue.json", "rights.json", "normalization.json",
                "midi.json", "board.html", "session.json"):
        add(doc)
    for track in catalogue.get("tracks", []):
        add(track["file"])
        if track.get("normalized_file"):
            add(track["normalized_file"])
        if track.get("midi_file"):
            add(track["midi_file"])
    manifest = {
        "session_id": session_id,
        "generated": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "members": [arc for _src, arc in members],
        "missing": missing,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as fh:
        with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED) as zf:
            for src, arc in members:
                zf.write(src, arc)
            zf.writestr("bundle.json", json.dumps(manifest, indent=2,
                                                   sort_keys=True))
    return manifest


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica bundle export")
    parser.add_argument("session_dir")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    session_id = os.path.basename(os.path.abspath(args.session_dir))
    out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(args.session_dir)), "..",
        "exports", "musica-%s-bundle.zip" % session_id)
    manifest = export_bundle(args.session_dir, out)
    print("bundle %s members=%d missing=%d"
          % (out, len(manifest["members"]), len(manifest["missing"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
