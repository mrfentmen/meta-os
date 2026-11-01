// labs/music3d/tests/validate.test.mjs — node:test, no dependencies.
// Validates the note-to-height map covers C4..C5, the playback order
// matches the scale data, and the octave row is +12 semitones.
// Run: node --test labs/music3d/tests/validate.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { SCALE, NOTE_Y, BEATS, freqOf, octaveUp } from "../notes-data.mjs";

test("height map covers C4 to C5 in order", () => {
  const names = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"];
  let prev = -Infinity;
  for (const n of names) {
    assert.ok(Number.isFinite(NOTE_Y[n]), `${n} has a height`);
    assert.ok(NOTE_Y[n] > prev, `${n} sits above the previous note`);
    prev = NOTE_Y[n];
  }
});

test("playback order matches the scale data", () => {
  assert.ok(SCALE.length > 0);
  assert.equal(SCALE[0].n, "C4");
  assert.equal(SCALE[SCALE.length - 1].n, "C4");
  for (const e of SCALE) {
    assert.ok(BEATS[e.v] > 0, `${e.n} has a positive beat value`);
    assert.ok(Number.isFinite(freqOf(e.n)), `${e.n} has a frequency`);
  }
});

test("octave row is a true octave above", () => {
  for (const e of SCALE) {
    const up = octaveUp(e.n);
    assert.ok(Math.abs(freqOf(up) / freqOf(e.n) - 2) < 1e-9, `${up} is 2x ${e.n}`);
    assert.ok(Number.isFinite(NOTE_Y[up]), `${up} has a height`);
  }
});
