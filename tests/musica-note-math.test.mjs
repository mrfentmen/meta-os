// CB2-460/461/462 — Musica note math, as data only: no audio, no MIDI library.
import test from "node:test";
import assert from "node:assert/strict";
import {
  PITCH_CLASSES,
  noteToSemitone,
  semitoneToNote,
  transpose,
  transposeOctaves,
} from "../os/worlds/musica/note_math.mjs";

test("CB2-460 the twelve pitch classes map to their semitones", () => {
  assert.equal(PITCH_CLASSES.length, 12);
  // C4 is MIDI 60, A4 is 69: the two anchors every other value hangs from.
  assert.equal(noteToSemitone("C4"), 60);
  assert.equal(noteToSemitone("A4"), 69);

  PITCH_CLASSES.forEach((name, index) => {
    assert.equal(noteToSemitone(name + "4"), 60 + index, name + "4 sits at 60+" + index);
  });

  // Flats are the same pitch under another spelling.
  assert.equal(noteToSemitone("Bb4"), noteToSemitone("A#4"));
  assert.equal(noteToSemitone("Db3"), noteToSemitone("C#3"));
  assert.equal(noteToSemitone("Gb5"), noteToSemitone("F#5"));
  // A flat outside the supported set is refused, not guessed: Cb4 is B3 in a
  // real score, and mapping it as a bare pitch class would place it an octave
  // too high, so this module does not claim to spell it.
  assert.throws(() => noteToSemitone("Cb4"), /unknown note/);

  // Round trip through the number and back to a name.
  for (const note of ["C4", "F#3", "A5"]) {
    assert.equal(semitoneToNote(noteToSemitone(note)), note);
  }
});

test("CB2-461 an octave transposition shifts every semitone by 12", () => {
  const tune = ["C4", "E4", "G4", "Bb4"];
  const up = transpose(tune, 12);
  assert.deepEqual(up, ["C5", "E5", "G5", "A#5"]);
  tune.forEach((note, i) => {
    assert.equal(noteToSemitone(up[i]) - noteToSemitone(note), 12, note + " moved exactly 12");
  });

  const down = transpose(tune, -12);
  assert.deepEqual(down, ["C3", "E3", "G3", "A#3"]);
  tune.forEach((note, i) => {
    assert.equal(noteToSemitone(down[i]) - noteToSemitone(note), -12);
  });

  // Whole-octave transposition keeps the spelling, which `transpose` does not.
  assert.deepEqual(transposeOctaves(["Bb4", "Db5"], 1), ["Bb5", "Db6"]);
  assert.deepEqual(transposeOctaves(tune, 0), tune);
});

test("CB2-462 an unknown note name is refused, never guessed", () => {
  for (const bad of ["H4", "C", "C#", "C4x", "", "4C", "C##4", "c#b4"]) {
    assert.throws(
      () => noteToSemitone(bad),
      /unknown note|must be a string/,
      "refused: " + JSON.stringify(bad),
    );
  }
  assert.throws(() => noteToSemitone(60), /note: must be a string/);
  assert.throws(() => noteToSemitone(null), /note: must be a string/);
  assert.throws(() => transpose(["C4", "nope"], 12), /unknown note/);
  assert.throws(() => semitoneToNote(128), /out of MIDI range/);
  assert.throws(() => semitoneToNote(1.5), /must be an integer/);
});
