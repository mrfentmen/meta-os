"""OS-039: boot-audio check — sting + voice line are clean, unclipped, and mixable.

The DEM-003 fallback cut is not landed yet (Pax's task), so this check proves
everything provable without it: both files exist as MP3, decode cleanly, the
sting is short and quiet enough to sit under narration, and a sting-then-voice
mix measures no clipping (max volume below 0 dB). Placement into the DEM-003
cut is still owed when that cut lands; nothing here claims it.

Usage: python3 intel/boot_audio_check.py  (exit 0 = all checks pass)
"""

import re
import subprocess
import sys

STING = "submission-assets/audio/os039-boot-sting.mp3"
VOICE = "submission-assets/audio/os039-boot-voice-line.mp3"
MIX = "/tmp/os039-boot-mix.wav"

FAILURES = []


def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILURES.append(name)


def run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def probe_duration(path):
    result = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                  "-of", "default=noprint_wrappers=1", path])
    for line in result.stdout.splitlines():
        if line.startswith("duration="):
            return float(line.split("=", 1)[1])
    raise RuntimeError("no duration for " + path)


def volumes(path):
    result = run(["ffmpeg", "-i", path, "-af", "volumedetect",
                  "-vn", "-sn", "-dn", "-f", "null", "/dev/null"])
    mean = re.search(r"mean_volume:\s*(-?[\d.]+) dB", result.stderr)
    maximum = re.search(r"max_volume:\s*(-?[\d.]+) dB", result.stderr)
    if not mean or not maximum:
        raise RuntimeError("no volumedetect output for " + path)
    return float(mean.group(1)), float(maximum.group(1))


def main():
    for path in (STING, VOICE):
        with open(path, "rb") as handle:
            head = handle.read(3)
        check(path + " is MP3", head == b"ID3", repr(head))
        check(path + " decodes clean",
              run(["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"]).returncode == 0)

    sting_dur = probe_duration(STING)
    check("sting is short (1.5-2.5 s)", 1.5 <= sting_dur <= 2.5, f"{sting_dur:.2f} s")
    voice_dur = probe_duration(VOICE)
    check("voice line is one short line (under 10 s)", voice_dur < 10.0, f"{voice_dur:.2f} s")

    sting_mean, sting_max = volumes(STING)
    voice_mean, voice_max = volumes(VOICE)
    check("sting peak below voice peak (sits under narration)",
          sting_max < voice_max, f"sting max {sting_max} dB, voice max {voice_max} dB")
    check("sting mean below -20 dB", sting_mean < -20.0, f"{sting_mean} dB")

    # Mix test: sting, then the voice line, one track — the shape the boot
    # shot will use. No clipping means max volume stays below 0 dB.
    mixed = run(["ffmpeg", "-y", "-v", "error", "-i", STING, "-i", VOICE,
                 "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[out]",
                 "-map", "[out]", MIX])
    check("sting+voice concat renders", mixed.returncode == 0, mixed.stderr.strip()[:200])
    if mixed.returncode == 0:
        _, mix_max = volumes(MIX)
        check("mixed track does not clip", mix_max < 0.0, f"mix max {mix_max} dB")

    print("OS-039 boot audio:", "ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURES")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
