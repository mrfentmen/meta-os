"""CB-085, CB-086, CB-089 — pure Musica theory, no pretty_midi import."""

import os
import sys
import unittest

RUNTIME = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "os", "worlds", "musica", "runtime"))
sys.path.insert(0, RUNTIME)

from theory import (  # noqa: E402
    MAJOR_INTERVALS,
    MODES,
    RhythmError,
    build_scale,
    freq_to_name,
    midi_name,
    midi_to_freq,
    validate_measure,
)


class TestNoteMath(unittest.TestCase):
    def test_frequency_to_name_round_trips_across_piano(self):
        for midi in range(21, 109):
            self.assertEqual(freq_to_name(midi_to_freq(midi)), midi_name(midi), midi)

    def test_a4_is_440(self):
        self.assertEqual(round(midi_to_freq(69), 6), 440.0)
        self.assertEqual(freq_to_name(440.0), "A4")


class TestRhythm(unittest.TestCase):
    def test_exact_measure_passes(self):
        self.assertEqual(validate_measure(1, [1.0, 1.0, 1.0, 1.0]), 4.0)

    def test_short_measure_names_the_measure(self):
        with self.assertRaises(RhythmError) as ctx:
            validate_measure(7, [1.0, 1.0, 0.5])
        self.assertIn("measure 7", str(ctx.exception))
        self.assertIn("2.5", str(ctx.exception))


class TestScale(unittest.TestCase):
    def test_every_mode_derives_from_the_parent_scale(self):
        parent = {n % 12 for n in [0 + i for i in MAJOR_INTERVALS]}
        for mode in MODES:
            notes = build_scale(0, mode)
            self.assertEqual(len(notes), 7, mode)
            self.assertEqual({n % 12 for n in notes}, parent, mode)

    def test_dorian_is_the_second_rotation(self):
        self.assertEqual(build_scale(0, "dorian"), [2, 4, 5, 7, 9, 11, 12])


if __name__ == "__main__":
    unittest.main()
