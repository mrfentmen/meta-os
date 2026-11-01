"""musica catalogue export (HN-031).

Exports a session's keepers as catalogue.json: one entry per keeper
with a licence and provenance line. Licence for every studio track
is the studio's own generated material -- no third-party material
enters the catalogue (HN-035 enforces this: a track with an empty
rights line is rejected, never exported).

Keeper audio is copied to keepers/ inside the session dir; that dir
IS committed (unlike working takes/, which is reproducible from
the log). Catalogue entries point at the keepers/ files.
"""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import read_log  # noqa: E402

OWN_LICENCE = "own — generated in-studio by Meta Musica; no third-party material"


def build_catalogue(session_dir, studio_name="Meta Musica", copy=True):
    """Export keepers to catalogue.json. Returns the catalogue dict.

    With copy=True (default) keeper audio is copied to keepers/
    inside the session dir. With copy=False the catalogue points
    at the take's original file (used for large sessions, where
    the audio is reproducible from the log and copying would
    bloat the repo).
    """
    import datetime
    log_path = os.path.join(session_dir, "take_log.jsonl")
    takes = read_log(log_path)
    keepers_dir = os.path.join(session_dir, "keepers")
    os.makedirs(keepers_dir, exist_ok=True)
    tracks = []
    for take in takes:
        if take["verdict"] != "keeper":
            continue
        if copy:
            src = os.path.join(session_dir, take["file"])
            name = "%s.wav" % take["take_id"]
            dst = os.path.join(keepers_dir, name)
            if os.path.exists(src):
                shutil.copyfile(src, dst)
            file_ref = "keepers/%s" % name
        else:
            file_ref = take["file"]
        tracks.append({
            "take_id": take["take_id"],
            "session_id": take["session_id"],
            "title": "%s %s" % (take["brief_id"], take["take_id"]),
            "brief_id": take["brief_id"],
            "file": file_ref,
            "duration_s": take["duration_s"],
            "sha256": take["sha256"],
            "licence": OWN_LICENCE,
            "provenance": "rendered by os/worlds/musica/runtime/compose.py "
                          "from brief %s, seed %d, params %s"
                          % (take["brief_id"], take["seed"],
                             json.dumps(take["params"], sort_keys=True)),
        })
    catalogue = {
        "studio": studio_name,
        "session_id": os.path.basename(os.path.abspath(session_dir)),
        "generated": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "tracks": tracks,
    }
    with open(os.path.join(session_dir, "catalogue.json"), "w",
              encoding="utf-8") as fh:
        json.dump(catalogue, fh, indent=2, sort_keys=True)
    return catalogue


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica catalogue export")
    parser.add_argument("session_dir")
    parser.add_argument("--studio", default="Meta Musica")
    parser.add_argument("--no-copy", action="store_true")
    args = parser.parse_args(argv)
    catalogue = build_catalogue(args.session_dir, args.studio,
                                copy=not args.no_copy)
    print("catalogue tracks=%d" % len(catalogue["tracks"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
