"""musica demo cut (HN-054).

A montage of real keepers for the platform film, labelled with
its source sessions. The cut is exactly --target seconds (default
60.00): whole keeper tracks in catalogue order, plus a trimmed
tail from the next keeper to land on the target sample. No loops,
no padding, no silence filler: if the keepers cannot fill the
target, the command fails instead of faking the length.

Sources prefer the normalised files (HN-036) for consistent
loudness. The manifest (demo-cut.json) lists every segment with
its take id, session id, source file, and excerpt length.

  python3 demo_cut.py SESSION_DIR [--target 60] [--out demo-cut.wav]
"""

import json
import os
import subprocess
import sys


def _duration(path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("ffprobe failed for %s" % path)
    return float(proc.stdout.strip())


def build_demo_cut(session_dir, target=60.0, out_path=None):
    """Build the montage. Returns the manifest dict."""
    catalogue_path = os.path.join(session_dir, "catalogue.json")
    with open(catalogue_path, encoding="utf-8") as fh:
        catalogue = json.load(fh)
    tracks = catalogue.get("tracks", [])
    if not tracks:
        raise ValueError("no catalogue tracks to cut from")
    segments = []
    remaining = target
    for track in tracks:
        if remaining <= 0:
            break
        src = os.path.join(session_dir,
                           track.get("normalized_file") or track["file"])
        if not os.path.exists(src):
            continue
        full = _duration(src)
        take = min(full, remaining)
        segments.append({"take_id": track["take_id"],
                         "session_id": track["session_id"],
                         "file": os.path.relpath(src, session_dir),
                         "excerpt_s": round(take, 3)})
        remaining = round(remaining - take, 3)
    if remaining > 0.05:
        raise ValueError("keepers total %.2fs, cannot fill %.2fs without "
                         "looping or padding" % (target - remaining, target))
    out = out_path or os.path.join(session_dir, "demo-cut.wav")
    inputs = []
    filters = []
    for i, seg in enumerate(segments):
        src = os.path.join(session_dir, seg["file"])
        inputs += ["-i", src]
        filters.append("[%d:a]atrim=0:%.3f,asetpts=PTS-STARTPTS[a%d]"
                       % (i, seg["excerpt_s"], i))
    concat = "".join("[a%d]" % i for i in range(len(segments)))
    filters.append("%sconcat=n=%d:v=0:a=1[out]"
                   % (concat, len(segments)))
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y"] + inputs + [
        "-filter_complex", ";".join(filters),
        "-map", "[out]", "-ar", "22050", "-ac", "1", out]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(out):
        raise RuntimeError("demo cut failed: %s" % proc.stderr[-500:])
    actual = _duration(out)
    manifest = {"session_id": catalogue.get("session_id",
                                            os.path.basename(
                                                os.path.abspath(session_dir))),
                "target_s": target, "actual_s": round(actual, 3),
                "segments": segments}
    manifest_path = os.path.join(session_dir, "demo-cut.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return manifest


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica demo cut")
    parser.add_argument("session_dir")
    parser.add_argument("--target", type=float, default=60.0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    manifest = build_demo_cut(args.session_dir, args.target, args.out)
    print("demo cut actual=%.3fs segments=%d"
          % (manifest["actual_s"], len(manifest["segments"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
