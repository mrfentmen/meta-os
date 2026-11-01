"""musica composition loop v1 (HN-029).

Renders REAL audio: deterministic seeded synthesis (pad chords, bass,
melody, hats) to 16-bit mono WAV, 22050 Hz, with every attempt
appended to the take log the moment it is rendered. No mock audio:
if this module cannot render, it fails instead of writing a fake file.

Determinism: the same seed + params renders byte-identical audio
(the WAV header carries no timestamps), so any take can be replayed
exactly from its log entry -- see replay_take(). Keeper audio is
committed with the catalogue; every other take is reproducible from
its log entry on demand.

Layout of a session dir:
  session.json    session id, brief id, seed base, counts
  take_log.jsonl  one JSON take record per line (take_log.py schema)
  takes/          rendered WAV files (working output)

CLI:
  python3 compose.py --session-dir DIR --brief-id chipsynth
      --brief-text "..." --tempo 132 --key C --mode minor
      --waveform square --bars 4 --takes 12 --seed-base 1000
  python3 compose.py --replay LOG TAKE_ID OUT.wav
"""

import argparse
import json
import math
import os
import random
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import append_take, read_log, sha256_file  # noqa: E402

SAMPLE_RATE = 22050

# Semitone offsets from C for minor/major pentatonic-flavoured walks.
SCALE = {
    "minor": [0, 3, 5, 7, 10, 12, 15],
    "major": [0, 2, 4, 7, 9, 12, 14],
}
KEY_SEMITONE = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11,
}
# Chord roots per bar, in scale degrees (0 = tonic).
PROGRESSIONS = {
    "minor": [0, 5, 3, 4],
    "major": [0, 4, 5, 3],
}
BASE_FREQ = 130.81  # C3


def _freq(key, mode, degree):
    semitone = KEY_SEMITONE[key] + SCALE[mode][degree % len(SCALE[mode])]
    return BASE_FREQ * (2.0 ** (semitone / 12.0))


def _add(buf, start, samples, gain):
    for i, value in enumerate(samples):
        pos = start + i
        if pos < len(buf):
            buf[pos] += value * gain


def _tone(freq, count, wave_type, attack=0.01, decay=0.4):
    """One note: sine/triangle/square at freq for count samples."""
    out = []
    attack_n = max(1, int(count * attack))
    for i in range(count):
        phase = 2.0 * math.pi * freq * i / SAMPLE_RATE
        if wave_type == "square":
            value = 1.0 if math.sin(phase) >= 0 else -1.0
            value = value * 0.5 + 0.25 * math.sin(phase)
        elif wave_type == "triangle":
            value = (2.0 / math.pi) * math.asin(math.sin(phase))
        else:
            value = math.sin(phase)
        if i < attack_n:
            env = i / attack_n
        else:
            env = max(0.0, 1.0 - (i - attack_n) / (count * decay + 1))
        out.append(value * env)
    return out


def render_samples(params, seed):
    """Render the full take as float samples in [-1, 1]. Deterministic."""
    tempo = params["tempo"]
    bars = params["bars"]
    key = params["key"]
    mode = params["mode"]
    wave_type = params["waveform"]
    rng = random.Random(seed)
    beat = 60.0 / tempo
    bar_samples = int(4 * beat * SAMPLE_RATE)
    total = bars * bar_samples
    buf = [0.0] * total
    prog = PROGRESSIONS[mode]
    melody_degree = 0
    for bar in range(bars):
        start = bar * bar_samples
        chord_root = prog[bar % len(prog)]
        # Pad: chord tones (root, third, fifth degrees) across the bar.
        for step in (0, 2, 4):
            freq = _freq(key, mode, chord_root + step) * 2.0
            _add(buf, start, _tone(freq, bar_samples, "triangle",
                                   attack=0.3, decay=1.0), 0.10)
        # Bass: root on each beat.
        beat_samples = int(beat * SAMPLE_RATE)
        for beat_i in range(4):
            freq = _freq(key, mode, chord_root) / 2.0
            _add(buf, start + beat_i * beat_samples,
                 _tone(freq, beat_samples, "sine", attack=0.02, decay=0.6), 0.35)
        # Melody: one seeded note per beat, occasional rest.
        for beat_i in range(4):
            if rng.random() < 0.2:
                continue
            melody_degree += rng.choice([-2, -1, -1, 0, 1, 1, 2])
            freq = _freq(key, mode, melody_degree) * 2.0
            _add(buf, start + beat_i * beat_samples,
                 _tone(freq, beat_samples, wave_type, attack=0.01, decay=0.5),
                 0.30)
        # Hats: noise bursts on offbeats, quieter on major (ambient).
        hat_gain = 0.06 if mode == "major" else 0.12
        for half in (1, 3, 5, 7):
            pos = start + int(half * beat_samples / 2)
            length = int(0.03 * SAMPLE_RATE)
            for i in range(length):
                if pos + i < total:
                    buf[pos + i] += (rng.random() * 2.0 - 1.0) * hat_gain * (
                        1.0 - i / length)
    peak = max(max(buf), -min(buf), 1e-9)
    return [max(-1.0, min(1.0, v * 0.89 / peak)) for v in buf]


def write_wav(path, samples):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SAMPLE_RATE)
        frames = b"".join(
            struct.pack("<h", int(s * 32767)) for s in samples)
        fh.writeframes(frames)
    return len(samples) / SAMPLE_RATE


def render_take(params, seed, out_path):
    """Render one take; return (duration_s, sha256)."""
    duration = write_wav(out_path, render_samples(params, seed))
    return duration, sha256_file(out_path)


def replay_take(log_path, take_id, out_path):
    """Re-render a logged take exactly; return (duration_s, sha256)."""
    for record in read_log(log_path):
        if record["take_id"] == take_id:
            return render_take(record["params"], record["seed"], out_path)
    raise ValueError("take %s not in log %s" % (take_id, log_path))


def run_session(session_dir, brief_id, brief_text, params, takes,
                seed_base, resume=False):
    """Run takes 1..N, appending each to the take log as rendered.

    With resume=True an existing log is continued after its last
    take; without resume an existing log refuses to run (never
    silently overwrite a session). A take killed between render and
    log-append leaves an orphaned WAV; resume re-renders that take
    number deterministically (same seed, same bytes) and logs it
    once, so no take is lost or duplicated. Returns the new take
    records.
    """
    os.makedirs(session_dir, exist_ok=True)
    log_path = os.path.join(session_dir, "take_log.jsonl")
    existing = read_log(log_path) if os.path.exists(log_path) else []
    if existing and not resume:
        raise ValueError("session log already exists; pass resume=True "
                         "to continue it: %s" % log_path)
    import datetime
    session_id = os.path.basename(os.path.abspath(session_dir))
    made = []
    for n in range(len(existing) + 1, len(existing) + takes + 1):
        take_id = "take-%03d" % n
        seed = seed_base + n
        rel = "takes/%s.wav" % take_id
        out_path = os.path.join(session_dir, rel)
        duration, digest = render_take(params, seed, out_path)
        record = {
            "take_id": take_id,
            "session_id": session_id,
            "timestamp": datetime.datetime.now(
                datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "brief_id": brief_id,
            "prompt": brief_text,
            "seed": seed,
            "params": params,
            "duration_s": round(duration, 3),
            "file": rel,
            "sha256": digest,
            "verdict": "pending",
            "reason": "",
            "spark_assist": None,
            "human_verdict": None,
        }
        append_take(log_path, record)
        made.append(record)
    session = {
        "session_id": session_id,
        "brief_id": brief_id,
        "seed_base": seed_base,
        "takes_logged": len(existing) + len(made),
        "takes_new": len(made),
    }
    with open(os.path.join(session_dir, "session.json"), "w",
              encoding="utf-8") as fh:
        json.dump(session, fh, indent=2, sort_keys=True)
    return made


def main(argv=None):
    parser = argparse.ArgumentParser(description="Musica composition loop")
    parser.add_argument("--session-dir")
    parser.add_argument("--brief-id", default="chipsynth")
    parser.add_argument("--brief-text", default="")
    parser.add_argument("--tempo", type=float, default=132)
    parser.add_argument("--key", default="C")
    parser.add_argument("--mode", default="minor")
    parser.add_argument("--waveform", default="square")
    parser.add_argument("--bars", type=int, default=4)
    parser.add_argument("--takes", type=int, default=12)
    parser.add_argument("--seed-base", type=int, default=1000)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--replay", nargs=3, metavar=("LOG", "TAKE", "OUT"))
    args = parser.parse_args(argv)
    if args.replay:
        duration, digest = replay_take(*args.replay)
        print("replayed %s duration=%.3f sha256=%s"
              % (args.replay[1], duration, digest))
        return 0
    params = {"tempo": args.tempo, "key": args.key, "mode": args.mode,
              "waveform": args.waveform, "bars": args.bars}
    made = run_session(args.session_dir, args.brief_id,
                       args.brief_text or ("%s brief: %.0f bpm %s %s"
                                           % (args.brief_id, args.tempo,
                                              args.key, args.mode)),
                       params, args.takes, args.seed_base, args.resume)
    for record in made:
        print("%s seed=%d duration=%.3f sha256=%s"
              % (record["take_id"], record["seed"], record["duration_s"],
                 record["sha256"][:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
