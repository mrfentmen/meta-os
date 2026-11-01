"""musica loudness normalisation (HN-036).

Catalogue tracks are normalised to a stated LUFS target with
ffmpeg loudnorm (single-pass linear). Before/after integrated
loudness is measured per track with the loudnorm print pass and
recorded in normalization.json; the catalogue entry gains
normalized_file + loudness {target, before, after}. Originals are
kept; the normalised files are what the demo cut (HN-054) uses.

Target: -16.0 LUFS, true peak -1.5 dB, LRA 11. Tolerance for the
single-pass result is +/-1.0 LUFS, reported per track, never
rounded into compliance.
"""

import json
import os
import re
import subprocess
import sys

TARGET_LUFS = -16.0
TRUE_PEAK_DB = -1.5
LRA = 11
TOLERANCE_LUFS = 1.0


def _run_loudnorm_measure(path):
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-i", path,
           "-vn", "-sn", "-dn",
           "-af", "loudnorm=I=%s:TP=%s:LRA=%s:print_format=json"
                  % (TARGET_LUFS, TRUE_PEAK_DB, LRA),
           "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    match = re.search(r"\{[^}]*\"input_i\"[^}]*\}", proc.stderr)
    if not match:
        raise RuntimeError("loudnorm measure failed for %s: %s"
                           % (path, proc.stderr[-500:]))
    return json.loads(match.group(0))


def measure_lufs(path):
    """Integrated loudness (LUFS) of a file, via ffmpeg loudnorm."""
    return float(_run_loudnorm_measure(path)["input_i"])


def normalize_file(src, dst, target=TARGET_LUFS):
    """Single-pass linear loudnorm to target. Returns output LUFS."""
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", src,
           "-af", "loudnorm=linear=true:I=%s:TP=%s:LRA=%s"
                  % (target, TRUE_PEAK_DB, LRA),
           "-ar", "22050", dst]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError("loudnorm failed for %s: %s"
                           % (src, proc.stderr[-500:]))
    return measure_lufs(dst)


def normalize_session(session_dir, target=TARGET_LUFS):
    """Normalise every catalogue track. Returns the normalization rows."""
    catalogue_path = os.path.join(session_dir, "catalogue.json")
    with open(catalogue_path, encoding="utf-8") as fh:
        catalogue = json.load(fh)
    rows = []
    for track in catalogue.get("tracks", []):
        src = os.path.join(session_dir, track["file"])
        dst = os.path.join(session_dir, "normalized",
                           "%s.wav" % track["take_id"])
        before = measure_lufs(src)
        after = normalize_file(src, dst, target)
        track["normalized_file"] = "normalized/%s.wav" % track["take_id"]
        track["loudness"] = {"target_lufs": target,
                             "before_lufs": round(before, 2),
                             "after_lufs": round(after, 2)}
        rows.append({"take_id": track["take_id"],
                     "before_lufs": round(before, 2),
                     "after_lufs": round(after, 2),
                     "target_lufs": target,
                     "within_tolerance": abs(after - target) <= TOLERANCE_LUFS})
    with open(catalogue_path, "w", encoding="utf-8") as fh:
        json.dump(catalogue, fh, indent=2, sort_keys=True)
    with open(os.path.join(session_dir, "normalization.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"target_lufs": target, "tolerance_lufs": TOLERANCE_LUFS,
                   "tracks": rows}, fh, indent=2, sort_keys=True)
    return rows


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica loudness normalise")
    parser.add_argument("session_dir")
    parser.add_argument("--target", type=float, default=TARGET_LUFS)
    args = parser.parse_args(argv)
    rows = normalize_session(args.session_dir, args.target)
    for row in rows:
        print("%s before=%.2f after=%.2f target=%.1f within=%s"
              % (row["take_id"], row["before_lufs"], row["after_lufs"],
                 row["target_lufs"], row["within_tolerance"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
