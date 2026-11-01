"""musica variation engine (HN-037).

The loop must not repeat a near-identical take. Stated method:
each keeper's fingerprint is its per-beat RMS plus its per-beat
spectrum in 8 bands (500-4200 Hz, the melody/hat range, not the
shared pad/bass), L2-normalised; two takes are near-identical
when their cosine similarity exceeds the threshold.

Threshold 0.98, calibrated on the HN-029 session: distinct-seed
keepers score at most 0.9242 pairwise, while a gain-changed copy
of a keeper scores 0.9997. A take over threshold against any
earlier keeper is rejected into the reject log with the matching
take and the similarity on the record.

apply_variation() runs after the keeper pass and only checks
takes the keeper pass kept; keeper rejects stay rejected.
"""

import json
import math
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import read_log  # noqa: E402

BANDS = (500, 700, 900, 1200, 1600, 2200, 3000, 4200)
THRESHOLD = 0.98


def _goertzel(samples, sr, freq):
    coeff = 2.0 * math.cos(2.0 * math.pi * freq / sr)
    s1 = s2 = 0.0
    for x in samples:
        s0 = x + coeff * s1 - s2
        s2, s1 = s1, s0
    return (s1 * s1 + s2 * s2 - coeff * s1 * s2) / max(1, len(samples))


def fingerprint(path, tempo, bars):
    """Per-beat RMS + normalised band spectrum, L2-normalised."""
    with wave.open(path, "rb") as fh:
        n = fh.getnframes()
        sr = fh.getframerate()
        raw = fh.readframes(n)
    samples = [x / 32768.0 for x in struct.unpack("<%dh" % n, raw)]
    beat = int(60.0 / tempo * sr)
    vec = []
    for b in range(bars * 4):
        window = samples[b * beat:(b + 1) * beat]
        if not window:
            break
        rms = math.sqrt(sum(x * x for x in window) / len(window))
        spec = [_goertzel(window, sr, f) for f in BANDS]
        total = sum(spec) or 1.0
        vec.append(rms)
        vec.extend(x / total for x in spec)
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def similarity(a, b):
    return sum(x * y for x, y in zip(a, b))


def apply_variation(session_dir, threshold=THRESHOLD):
    """Reject keeper takes that near-duplicate an earlier keeper."""
    import datetime
    log_path = os.path.join(session_dir, "take_log.jsonl")
    takes = read_log(log_path)
    accepted = []
    clones = 0
    for take in takes:
        if take["verdict"] != "keeper":
            continue
        audio = os.path.join(session_dir, take["file"])
        fp = fingerprint(audio, take["params"]["tempo"],
                         take["params"]["bars"])
        best = (0.0, None)
        for other_id, other_fp in accepted:
            sim = similarity(fp, other_fp)
            if sim > best[0]:
                best = (sim, other_id)
        if best[0] > threshold:
            take["verdict"] = "reject"
            take["reason"] = ("near-identical to %s (similarity %.4f)"
                              % (best[1], best[0]))
            take["clone_of"] = best[1]
            take["similarity"] = round(best[0], 4)
            clones += 1
        else:
            accepted.append((take["take_id"], fp))
    with open(log_path, "w", encoding="utf-8") as fh:
        for take in takes:
            fh.write(json.dumps(take, sort_keys=True) + "\n")
    session_path = os.path.join(session_dir, "session.json")
    session = {}
    if os.path.exists(session_path):
        with open(session_path, encoding="utf-8") as fh:
            session = json.load(fh)
    session["variation_pass"] = {
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "threshold": threshold,
        "clones": clones,
    }
    with open(session_path, "w", encoding="utf-8") as fh:
        json.dump(session, fh, indent=2, sort_keys=True)
    return {"clones": clones, "takes": len(takes)}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica variation pass")
    parser.add_argument("session_dir")
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    args = parser.parse_args(argv)
    summary = apply_variation(args.session_dir, args.threshold)
    print("variation clones=%d takes=%d"
          % (summary["clones"], summary["takes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
