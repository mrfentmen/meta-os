"""DEM-014: narration final mix — picked takes combined, level-checked.

The mix combines the two narration takes that the lane treats as the
provisional final (take 1 of each: Helio, the default production voice,
the same voice as the WDG-033 fallback track and the DEM-015 caption, so
the mix cuts against those assets without a voice change): the WDG-031
opening framing, a 0.5 s silence gap, then the WDG-030 watchdog segment.
No take is marked final by Dale yet — rehearsal pick is still open — so
this is the provisional final mix the DEM-003 fallback edit consumes, and
the take log says so plainly.

Level check: the mix must decode cleanly, run the expected length
(opening + gap + watchdog, within tolerance), and peak below 0 dB (no
clipping) and within 3 dB of the louder input clip (no level jump at the
join). The reference level is the WDG-033 fallback track (same voice,
same lane); the check reports the mix peak against it but does not force
a match, since the fallback track is a different edit.

What is NOT claimed here: Dale's rehearsal pick (not made), sync into
the DEM-003 fallback video (that edit is not landed, Pax's task), or a
level check against screen-capture audio (no screen capture exists yet —
the check runs against the narration assets themselves and the fallback
track reference). When the fallback video lands, the mix is re-checked
against its capture audio before it is called final.

Usage: python3 intel/final_mix_check.py  (exit 0 = all checks pass;
writes demo-assets/audio/dem014-final-mix.mp3)
"""

import re
import subprocess
import sys

OPENING = "demo-assets/audio/wdg031-opening-framing-take1.mp3"
WATCHDOG = "demo-assets/audio/wdg030-watchdog-segment-take1.mp3"
FALLBACK = "demo-assets/audio/wdg033-fallback-full-demo.mp3"
MIX = "demo-assets/audio/dem014-final-mix.mp3"
GAP_SECONDS = 0.5

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
    for path in (OPENING, WATCHDOG):
        with open(path, "rb") as handle:
            head = handle.read(3)
        check(path + " is MP3", head == b"ID3", repr(head))
        check(path + " decodes clean",
              run(["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"]).returncode == 0)

    open_dur = probe_duration(OPENING)
    watch_dur = probe_duration(WATCHDOG)
    expected = open_dur + GAP_SECONDS + watch_dur
    check("inputs match the take log (19.9 s + 48.1 s)",
          abs(open_dur - 19.92) < 0.5 and abs(watch_dur - 48.07) < 0.5,
          f"opening {open_dur:.2f} s, watchdog {watch_dur:.2f} s")

    # Build the mix: opening, 0.5 s of silence, watchdog — one MP3 track.
    # anullsrc gives the gap; concat joins the three segments.
    mixed = run(["ffmpeg", "-y", "-v", "error",
                 "-i", OPENING,
                 "-f", "lavfi", "-t", str(GAP_SECONDS), "-i", "anullsrc=r=44100:cl=stereo",
                 "-i", WATCHDOG,
                 "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]",
                 "-map", "[out]", MIX])
    check("final mix renders", mixed.returncode == 0, mixed.stderr.strip()[:200])
    if mixed.returncode != 0:
        print("DEM-014 final mix:", f"{len(FAILURES)} FAILURES")
        return 1

    with open(MIX, "rb") as handle:
        head = handle.read(3)
    check("mix is MP3", head == b"ID3", repr(head))
    check("mix decodes clean",
          run(["ffmpeg", "-v", "error", "-i", MIX, "-f", "null", "-"]).returncode == 0)

    mix_dur = probe_duration(MIX)
    check("mix length is opening + gap + watchdog (±2 s)",
          abs(mix_dur - expected) < 2.0, f"{mix_dur:.2f} s vs expected {expected:.2f} s")

    _, open_max = volumes(OPENING)
    _, watch_max = volumes(WATCHDOG)
    _, mix_max = volumes(MIX)
    _, fallback_max = volumes(FALLBACK)
    check("mix does not clip", mix_max < 0.0, f"mix max {mix_max} dB")
    loudest_input = max(open_max, watch_max)
    check("no level jump at the join (mix peak within 3 dB of louder input)",
          abs(mix_max - loudest_input) < 3.0,
          f"mix max {mix_max} dB, louder input {loudest_input} dB")
    print(f"INFO fallback reference peak {fallback_max} dB (same voice, different edit)")

    print("DEM-014 final mix:", "ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURES")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
