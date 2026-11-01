#!/usr/bin/env python3
"""Frame extractor (NC-171) + scene-change mode (NC-173).
usage:
  python3 extract.py <video> <outdir> --fps 2
  python3 extract.py <video> <outdir> --scene 12.0
Fixed fps: deterministic names <base>-t<SS.sss>.jpg.
Scene mode: emits a frame when mean-abs-diff of 32x32 gray vs last
emitted exceeds the threshold; always emits frame 0.
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops, ImageStat


def grab(video, moment, dest, w=640):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", str(moment), "-i", video,
         "-frames:v", "1", "-vf", "scale=%d:-1" % w, dest],
        check=True)


def duration(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1", video], capture_output=True, text=True,
        check=True)
    return float(out.stdout.strip().split("=")[-1])


def gray_small(path, size=32):
    return Image.open(path).convert("L").resize((size, size))


def mean_diff(a, b):
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


def main(argv):
    if len(argv) < 3:
        print(__doc__.split("\n")[1])
        return 2
    video, outdir = argv[0], argv[1]
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video))[0]
    dur = duration(video)
    made = []
    if "--fps" in argv:
        fps = float(argv[argv.index("--fps") + 1])
        t = 0.0
        while t < dur - 1e-6:
            dest = os.path.join(outdir, "%s-t%07.3f.jpg" % (base, t))
            grab(video, t, dest)
            made.append(dest)
            t += 1.0 / fps
    elif "--scene" in argv:
        thresh = float(argv[argv.index("--scene") + 1])
        tmp = tempfile.mkdtemp()
        # candidate pool at 4 fps; emit on change
        cands, t = [], 0.0
        while t < dur - 1e-6:
            p = os.path.join(tmp, "c-%07.3f.jpg" % t)
            grab(video, t, p)
            cands.append((t, p))
            t += 0.25
        last = None
        for t, p in cands:
            g = gray_small(p)
            if last is None or mean_diff(g, last) >= thresh:
                dest = os.path.join(outdir, "%s-t%07.3f.jpg" % (base, t))
                os.rename(p, dest)
                made.append(dest)
                last = g
    else:
        print("need --fps N or --scene THRESH")
        return 2
    print("extracted %d frames -> %s" % (len(made), outdir))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
