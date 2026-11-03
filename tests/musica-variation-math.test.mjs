// CB2-465/466 — Musica variation math: seeded, in scale, data only.
//
// The generator is pure: the seed is its only source of variation, so a test can
// pin the exact bar and prove that two runs of the same session agree.
import test from "node:test";
import assert from "node:assert/strict";
import { PITCH_CLASSES } from "../os/worlds/musica/note_math.mjs";
import { scalePool, variationNoteNames, variationNotes } from "../os/worlds/musica/variation.mjs";

// A minor pentatonic in one octave, the studio's most-used bar.
const SCALE = ["C", "D#", "F", "G", "A#"];

test("CB2-465 the same seed and input produce the same variation", () => {
  const a = variationNotes({ seed: 7, scale: SCALE, length: 16 });
  const b = variationNotes({ seed: 7, scale: SCALE, length: 16 });
  assert.deepEqual(a, b, "same seed, same notes");

  // Determinism is per call, not per module: a second run in the same process
  // must not be affected by the first.
  const c = variationNotes({ seed: 7, scale: SCALE, length: 16 });
  assert.deepEqual(a, c);

  // The first note is the scale root, so a bar starts where it should.
  assert.equal(a[0], 60);

  // A different seed walks a different bar. Same seed twice above; this only
  // asserts that the seed is actually used.
  const other = variationNotes({ seed: 8, scale: SCALE, length: 16 });
  assert.notDeepEqual(a, other);

  // Short and long bars are prefixes of each other only by seed, never by luck:
  // the same seed always starts the same way.
  assert.deepEqual(
    variationNotes({ seed: 7, scale: SCALE, length: 4 }),
    variationNotes({ seed: 7, scale: SCALE, length: 16 }).slice(0, 4),
  );
});

test("CB2-466 every generated note stays inside the scale's pitch set", () => {
  const allowed = new Set(SCALE.map((name) => PITCH_CLASSES.indexOf(name)));
  for (const seed of [1, 2, 3, 99, 12345]) {
    const notes = variationNotes({ seed, scale: SCALE, length: 32, low: 48, high: 72 });
    assert.equal(notes.length, 32, "length is respected");
    for (const semitone of notes) {
      assert.ok(
        allowed.has(((semitone % 12) + 12) % 12),
        "seed " + seed + " emitted a note outside the scale: " + semitone,
      );
      assert.ok(semitone >= 48 && semitone <= 72, "note stayed in range: " + semitone);
    }
  }

  // The pool is exactly the scale notes in the range, in order.
  assert.deepEqual(scalePool(["C", "E", "G"], 60, 64), [60, 64]);

  // A name the scale does not know is refused, never skipped.
  assert.throws(() => scalePool(["C", "H"], 60, 72), /unknown scale note "H"/);
  assert.throws(() => scalePool([], 60, 72), /a scale is required/);
  assert.throws(() => scalePool(["C"], 61, 62), /no scale note falls between 61 and 62/);
  assert.throws(() => variationNotes({ seed: 1.5, scale: SCALE }), /seed must be an integer/);
  assert.throws(() => variationNotes({ seed: 1, scale: SCALE, length: 0 }), /length must be a positive integer/);

  // Names and numbers describe the same bar.
  const names = variationNoteNames({ seed: 4, scale: SCALE, length: 8 });
  const numbers = variationNotes({ seed: 4, scale: SCALE, length: 8 });
  names.forEach((name, i) => {
    const midi = 12 * (Number(name.slice(-1)) + 1) + PITCH_CLASSES.indexOf(name.slice(0, -1));
    assert.equal(midi, numbers[i], name + " is the same pitch as " + numbers[i]);
  });
});
