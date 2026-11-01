"""musica silence audit (HN-052).

A scan proving no catalogue track is silent, truncated, or a
duplicate file hash. For every catalogue track it checks the file
on disk: it exists, its duration matches the logged duration
within 0.05 s (a shorter file is truncated), its RMS is above
-50 dBFS (a quieter file is silent), its sha256 matches the
catalogue entry, and no two tracks share a file hash.

Writes audit.json in the session dir and exits 0 when clean,
1 when any issue is found. In a fresh checkout, take audio that
was never rendered reports as "missing file" -- replay it from
the take log first (sessions README), then re-run the audit.

  python3 audit.py SESSION_DIR
"""

import json
import math
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import sha256_file  # noqa: E402

DURATION_TOLERANCE_S = 0.05
SILENCE_DBFS = -50.0


def _wav_info(path):
    with wave.open(path, "rb") as fh:
        n = fh.getnframes()
        sr = fh.getframerate()
        raw = fh.readframes(n)
    samples = struct.unpack("<%dh" % n, raw)
    rms = math.sqrt(sum(x * x for x in samples) / n) / 32768.0 if n else 0.0
    rms_db = 20 * math.log10(rms) if rms > 0 else -99.0
    return n / sr, rms_db


def audit_session(session_dir):
    """Scan a session catalogue. Returns the audit dict."""
    catalogue_path = os.path.join(session_dir, "catalogue.json")
    with open(catalogue_path, encoding="utf-8") as fh:
        catalogue = json.load(fh)
    log_path = os.path.join(session_dir, "take_log.jsonl")
    logged = {}
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    take = json.loads(line)
                    logged[take["take_id"]] = take
    issues = []
    seen_hashes = {}
    for track in catalogue.get("tracks", []):
        take_id = track["take_id"]
        path = os.path.join(session_dir, track["file"])
        if not os.path.exists(path):
            issues.append({"take_id": take_id, "issue": "missing file",
                           "file": track["file"]})
            continue
        duration, rms_db = _wav_info(path)
        logged_take = logged.get(take_id, {})
        expected = logged_take.get("duration_s", track.get("duration_s"))
        if expected is not None and duration < expected - DURATION_TOLERANCE_S:
            issues.append({"take_id": take_id, "issue": "truncated",
                           "duration_s": round(duration, 3),
                           "expected_s": expected})
        if rms_db < SILENCE_DBFS:
            issues.append({"take_id": take_id, "issue": "silent",
                           "rms_dbfs": round(rms_db, 1)})
        digest = sha256_file(path)
        if digest != track.get("sha256"):
            issues.append({"take_id": take_id, "issue": "hash mismatch",
                           "file": track["file"]})
        if digest in seen_hashes:
            issues.append({"take_id": take_id, "issue": "duplicate hash",
                           "duplicate_of": seen_hashes[digest]})
        else:
            seen_hashes[digest] = take_id
    audit = {"session_id": catalogue.get("session_id",
                                         os.path.basename(
                                             os.path.abspath(session_dir))),
             "tracks_checked": len(catalogue.get("tracks", [])),
             "issues": issues}
    with open(os.path.join(session_dir, "audit.json"), "w",
              encoding="utf-8") as fh:
        json.dump(audit, fh, indent=2, sort_keys=True)
    return audit


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica silence audit")
    parser.add_argument("session_dir")
    args = parser.parse_args(argv)
    audit = audit_session(args.session_dir)
    print("audit tracks=%d issues=%d"
          % (audit["tracks_checked"], len(audit["issues"])))
    for issue in audit["issues"]:
        print("  %s: %s" % (issue["take_id"], issue["issue"]))
    return 1 if audit["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
