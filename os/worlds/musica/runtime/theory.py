#!/usr/bin/env python3
"""Pure Musica theory (CB-085, CB-086, CB-089).

No audio, no pretty_midi, no file I/O. These are the note, measure and
scale rules the renderer already assumes, made checkable on their own.
"""

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
MODES = {
    "ionian": 0,
    "dorian": 1,
    "phrygian": 2,
    "lydian": 3,
    "mixolydian": 4,
    "aeolian": 5,
    "locrian": 6,
}


class RhythmError(ValueError):
    pass


def midi_to_freq(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def freq_to_midi(freq):
    if freq <= 0:
        raise ValueError("frequency must be > 0")
    return int(round(69 + 12 * __import__("math").log2(freq / 440.0)))


def midi_name(midi):
    return NOTE_NAMES[midi % 12] + str(midi // 12 - 1)


def freq_to_name(freq):
    return midi_name(freq_to_midi(freq))


def validate_measure(measure_no, beats, expected=4.0):
    total = sum(beats)
    if abs(total - expected) > 1e-9:
        raise RhythmError(
            "measure %s: beats sum %s, expected %s" % (measure_no, total, expected)
        )
    return total


def build_scale(root, mode):
    """Seven notes derived by rotating the parent major scale."""
    if mode not in MODES:
        raise ValueError("unknown mode: %s" % mode)
    offset = MODES[mode]
    notes = []
    for i in range(7):
        degree = (offset + i) % 7
        octave = 12 if offset + i >= 7 else 0
        notes.append(root + MAJOR_INTERVALS[degree] + octave)
    return notes
