"""musica keeper rules as code (HN-030).

A take passes or fails measurably. Measurement is pure Python on
the rendered WAV (no invented numbers, no model judgement):

  duration_s      from the WAV header
  rms_dbfs        RMS loudness of all samples
  silence_ratio   fraction of 50 ms windows below -50 dBFS
  repetition      bar fingerprints: Goertzel energy in 6 bands per
                  bar; a bar counts as a repeat when its fingerprint
                  has cosine similarity > 0.95 to another bar.
                  repetition = repeated bars / total bars.

The bar (stated, measured from the HN-029 session: RMS -13.8..-14.7
dBFS, silence 0.000, duration 7.27 s):
  duration 5..12 s, RMS -24..-8 dBFS, silence < 0.25, repetition < 0.75.

apply_keepers() rewrites verdict/reason in place in the take log
(prompt, seed, file, and hash are never touched) and stamps the
session with the pass counts.
"""

import json
import math
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import read_log  # noqa: E402

DURATION_MIN, DURATION_MAX = 5.0, 12.0
RMS_MIN_DBFS, RMS_MAX_DBFS = -24.0, -8.0
SILENCE_MAX = 0.25
REPETITION_MAX = 0.75
SILENCE_DBFS = -50.0
SIMILARITY = 0.95
BANDS = (100, 200, 400, 800, 1600, 3200)


def read_samples(path):
    with wave.open(path, "rb") as fh:
        n = fh.getnframes()
        sr = fh.getframerate()
        raw = fh.readframes(n)
    samples = [x / 32768.0 for x in struct.unpack("<%dh" % n, raw)]
    return samples, sr


def _goertzel(samples, sr, freq):
    coeff = 2.0 * math.cos(2.0 * math.pi * freq / sr)
    s1 = s2 = 0.0
    for x in samples:
        s0 = x + coeff * s1 - s2
        s2, s1 = s1, s0
    energy = s1 * s1 + s2 * s2 - coeff * s1 * s2
    return energy / max(1, len(samples))


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def measure(path, params):
    """Measure one rendered take. Returns a dict of measurements."""
    samples, sr = read_samples(path)
    n = len(samples)
    duration = n / sr
    rms = math.sqrt(sum(x * x for x in samples) / n) if n else 0.0
    rms_db = 20 * math.log10(rms) if rms > 0 else -99.0
    win = int(sr * 0.05)
    silent = total = 0
    for j in range(0, n - win + 1, win):
        w = samples[j:j + win]
        wr = math.sqrt(sum(x * x for x in w) / len(w)) if w else 0.0
        total += 1
        if wr == 0 or 20 * math.log10(wr) < SILENCE_DBFS:
            silent += 1
    silence_ratio = silent / total if total else 1.0
    # Bar fingerprints from the params tempo (4 beats per bar).
    bar_len = int(4 * 60.0 / params["tempo"] * sr)
    prints = []
    for start in range(0, n - bar_len + 1, bar_len):
        bar = samples[start:start + bar_len]
        prints.append([_goertzel(bar, sr, f) for f in BANDS])
    repeated = 0
    for i, a in enumerate(prints):
        if any(_cosine(a, b) > SIMILARITY
               for j, b in enumerate(prints) if j != i):
            repeated += 1
    repetition = repeated / len(prints) if prints else 1.0
    return {
        "duration_s": round(duration, 3),
        "rms_dbfs": round(rms_db, 1),
        "silence_ratio": round(silence_ratio, 3),
        "repetition": round(repetition, 3),
    }


def keeper_verdict(m):
    """Apply the bar. Returns (verdict, reason)."""
    fails = []
    if not DURATION_MIN <= m["duration_s"] <= DURATION_MAX:
        fails.append("duration %.2fs outside %.0f..%.0fs"
                     % (m["duration_s"], DURATION_MIN, DURATION_MAX))
    if not RMS_MIN_DBFS <= m["rms_dbfs"] <= RMS_MAX_DBFS:
        fails.append("loudness %.1f dBFS outside %.0f..%.0f dBFS"
                     % (m["rms_dbfs"], RMS_MIN_DBFS, RMS_MAX_DBFS))
    if m["silence_ratio"] >= SILENCE_MAX:
        fails.append("silence ratio %.3f >= %.2f"
                     % (m["silence_ratio"], SILENCE_MAX))
    if m["repetition"] >= REPETITION_MAX:
        fails.append("repetition %.3f >= %.2f"
                     % (m["repetition"], REPETITION_MAX))
    if fails:
        return "reject", "; ".join(fails)
    return ("keeper", "passes length, loudness, silence, repetition")


def apply_keepers(session_dir):
    """Run the keeper pass over a session's take log in place."""
    import datetime
    log_path = os.path.join(session_dir, "take_log.jsonl")
    takes = read_log(log_path)
    keepers = rejects = 0
    for take in takes:
        audio = os.path.join(session_dir, take["file"])
        m = measure(audio, take["params"])
        verdict, reason = keeper_verdict(m)
        take["verdict"] = verdict
        take["reason"] = reason
        take["measurement"] = m
        if verdict == "keeper":
            keepers += 1
        else:
            rejects += 1
    with open(log_path, "w", encoding="utf-8") as fh:
        for take in takes:
            fh.write(json.dumps(take, sort_keys=True) + "\n")
    session_path = os.path.join(session_dir, "session.json")
    session = {}
    if os.path.exists(session_path):
        with open(session_path, encoding="utf-8") as fh:
            session = json.load(fh)
    session["keeper_pass"] = {
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "keepers": keepers,
        "rejects": rejects,
    }
    with open(session_path, "w", encoding="utf-8") as fh:
        json.dump(session, fh, indent=2, sort_keys=True)
    return {"keepers": keepers, "rejects": rejects, "takes": len(takes)}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica keeper pass")
    parser.add_argument("session_dir")
    args = parser.parse_args(argv)
    summary = apply_keepers(args.session_dir)
    print("keepers=%d rejects=%d takes=%d" % (
        summary["keepers"], summary["rejects"], summary["takes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
