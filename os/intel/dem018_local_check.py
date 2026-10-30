"""DEM-018 (partial): local pre-check for every demo audio asset.

DEM-018's acceptance is a listening check logged with the demo machine
named — speakers and headphones on the actual demo hardware. This VM has
no demo machine attached (no named demo hardware, no speakers/headphones
to listen on), so that check is still OPEN and nothing here closes it.

What this script does prove, on this machine, for all 12 audio assets
the lane owns: each file is an MP3, decodes cleanly through ffmpeg, has
a sane duration, and peaks below 0 dB (no clipping). It is the
pre-check that makes the demo-machine session a listen, not a debug: if
anything here failed, the asset would be fixed before anyone books time
on demo hardware. The per-file table it prints is the record the
listening session starts from.

Usage: python3 intel/dem018_local_check.py  (exit 0 = all checks pass)
"""

import os
import re
import subprocess
import sys

ASSETS = [
    # Narration takes (WDG-030/WDG-031) and the provisional final mix.
    "demo-assets/audio/wdg030-watchdog-segment-take1.mp3",
    "demo-assets/audio/wdg030-watchdog-segment-take2.mp3",
    "demo-assets/audio/wdg031-opening-framing-take1.mp3",
    "demo-assets/audio/wdg031-opening-framing-take2.mp3",
    "demo-assets/audio/dem014-final-mix.mp3",
    # Fallback track, caption voiceover, ambient bed, stingers.
    "demo-assets/audio/wdg033-fallback-full-demo.mp3",
    "demo-assets/audio/dem015-caption-watchdog-moment.mp3",
    "demo-assets/audio/dem017-ambient-bed.mp3",
    "demo-assets/audio/wdg034-alert-sting.mp3",
    "demo-assets/audio/wdg034-success-sting.mp3",
    # Boot audio (OS-039, submission assets).
    "submission-assets/audio/os039-boot-sting.mp3",
    "submission-assets/audio/os039-boot-voice-line.mp3",
]

FAILURES = []


def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILURES.append(name)


def run(cmd, timeout=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def probe_duration(path):
    result = run(["ffprobe", "-v", "error", "-show_entries",
                  "format=duration",
                  "-of", "default=noprint_wrappers=1", path])
    for line in result.stdout.splitlines():
        if line.startswith("duration="):
            return float(line.split("=", 1)[1])
    raise RuntimeError("no duration for " + path)


def max_volume(path):
    result = run(["ffmpeg", "-i", path, "-af", "volumedetect",
                  "-vn", "-sn", "-dn", "-f", "null", "/dev/null"])
    match = re.search(r"max_volume:\s*(-?[\d.]+) dB", result.stderr)
    if not match:
        raise RuntimeError("no volumedetect output for " + path)
    return float(match.group(1))


def main():
    missing = [path for path in ASSETS if not os.path.isfile(path)]
    check("all 12 expected assets present", not missing,
          "missing: " + ", ".join(missing) if missing else "12/12")
    peaks = {}
    for path in ASSETS:
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as handle:
            head = handle.read(3)
        check(path + " is MP3", head == b"ID3", repr(head))
        decoded = run(["ffmpeg", "-v", "error", "-i", path,
                       "-f", "null", "-"])
        check(path + " decodes clean", decoded.returncode == 0,
              decoded.stderr.strip()[:200])
        duration = probe_duration(path)
        check(path + " duration sane (>0 s)", duration > 0,
              f"{duration:.2f} s")
        peak = max_volume(path)
        peaks[path] = peak
        check(path + " no clipping (peak < 0 dB)", peak < 0.0,
              f"max {peak} dB")
        print(f"  {path}: {duration:.2f} s, peak {peak} dB")
    if peaks:
        spread = max(peaks.values()) - min(peaks.values())
        print(f"peak spread across assets: {spread:.1f} dB "
              f"(loudest {max(peaks, key=peaks.get)}, "
              f"quietest {min(peaks, key=peaks.get)})")
        print("NOTE: spread is reported, not gated — stingers and the "
              "ambient bed are meant to sit quieter than narration.")
    print("DEM-018 status: LOCAL PRE-CHECK ONLY — the demo-machine "
          "listening check (speakers + headphones, machine named) "
          "remains OPEN.")
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED")
        return 1
    print("all local checks PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
