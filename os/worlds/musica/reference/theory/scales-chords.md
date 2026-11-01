# Scales and chords

[source: pack `runtime/compose.py` — read, not paraphrased from
elsewhere. Numbers below are the loop's own constants.]

## Scales (semitone offsets from C)

The loop walks a pentatonic-flavoured scale, not a full diatonic
scale. Degree numbers count up the list, wrapping around.

- minor: `[0, 3, 5, 7, 10, 12, 15]`
- major: `[0, 2, 4, 7, 9, 12, 14]`

## Keys (semitone offset from C)

C 0, C#/Db 1, D 2, Eb 3, E 4, F 5, F#/Gb 6, G 7, Ab 8, A 9,
Bb 10, B 11.

Base frequency is C3 = 130.81 Hz. A note's frequency is
`130.81 * 2^(semitone / 12)`.

## Chord progressions (one root per bar, scale degrees, 0 = tonic)

- minor: `[0, 5, 3, 4]` — tonic, then the 5th, 3rd, 4th degrees.
- major: `[0, 4, 5, 3]`

The pad plays the chord tones (root, third, fifth degrees) of the
bar's root. The bass plays the bar's root. The closing bar of a
brief lands back on the tonic (degree 0).

## Melody walk

One note per beat. Each step moves the melody degree by a seeded
choice from `[-2, -1, -1, 0, 1, 1, 2]` — small steps, so the
melody walks instead of jumping. About 1 beat in 5 is a rest
(20% rest chance). Rests are what keep a melody from turning
into a solid block of notes; losing them is one way a take gets
flagged for repetition (see `../lessons/keeper-history.md`).

## How to reuse this

- A new brief needs: a mode (minor or major), a key, and a
  progression from the lists above or a new one written in the
  same degree format. Do not write a progression in note names
  without its degree form — the loop works in degrees.
- Changing the scale list changes every melody the loop makes.
  That is a brief-level decision, not a per-take tweak: record
  it in the brief file, not in a take record.
