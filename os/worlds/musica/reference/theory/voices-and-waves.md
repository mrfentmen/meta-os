# Voices and waves

[source: pack `runtime/compose.py` — the loop's own voice table.]

## The four voices

Every take is four voices added into ONE buffer, then written as
one file. There are no stem files in this pack. The separation
the loop keeps is the note list (kind, start, duration, MIDI),
which is what the MIDI export replays.

| Voice | Wave | Gain | Shape |
|---|---|---|---|
| Pad | triangle | 0.10 | chord tones across the whole bar, slow attack (0.3), long decay (1.0) |
| Bass | sine | 0.35 | bar root on each beat, fast attack (0.02), decay 0.6, one octave below the pad root |
| Melody | brief's waveform | 0.30 | one note per beat, attack 0.01, decay 0.5 |
| Hats | noise burst | 0.12 minor / 0.06 major | 0.03 s bursts on the offbeats (half-beats 1, 3, 5, 7), fading out |

Gains are relative: pad sits behind, bass and melody lead, hats
stay quiet. Major mode gets quieter hats than minor mode.

## Wave shapes

- sine: smooth, round — used for bass. No edge.
- triangle: soft, a little hollow — used for pads, and for
  melody in ambient and boom-bap briefs.
- square: bright, buzzy, edged — used for melody in the
  chipsynth brief. Square is what makes chipsynth sound like
  chipsynth.
- noise: no pitch, just a burst — used for hats only.

## Output format

Mono WAV, 16-bit, 22050 Hz. Samples are peak-normalised to
0.89 before writing. A take's length is bars × 4 beats at the
brief's tempo (e.g. 4 bars at 132 BPM ≈ 7.27 s).

## Reproducibility

Same seed + same params = byte-identical audio. The WAV header
carries no timestamps, so any take can be replayed exactly from
its take-log entry (`compose.py --replay LOG TAKE_ID OUT.wav`).
If a file is missing, replay it from the log before claiming
anything about it.
