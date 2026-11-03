// Musica note math — pure data, no audio, no MIDI library.
//
// The studio names notes the way a musician does (`C4`, `F#3`, `Bb5`), and the
// composer needs one number per note to transpose, compare and render. This
// module is that mapping and nothing else: MIDI semitone numbers, 12 pitch
// classes, and a refusal for a name it does not know. A guessed note is worse
// than a refused one: it plays the wrong pitch and sounds deliberate.

const SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

// Flats are the same pitch classes under another name. Both spellings are
// accepted because a score in Bb writes Bb, not A#.
const FLATS = {
  Db: "C#",
  Eb: "D#",
  Gb: "F#",
  Ab: "G#",
  Bb: "A#",
};

export const PITCH_CLASSES = SHARPS.slice();

const NOTE = /^([A-Ga-g])([#b]?)(-?\d+)$/;

// `C4` is MIDI 60, so octave -1 is the bottom of the MIDI range.
export function noteToSemitone(note) {
  if (typeof note !== "string") throw new TypeError("note: must be a string");
  const match = NOTE.exec(note.trim());
  if (!match) throw new Error("unknown note: " + JSON.stringify(note));

  const letter = match[1].toUpperCase();
  const accidental = match[2];
  const octave = Number(match[3]);

  const spelled = letter + accidental;
  const pitch = accidental === "b" ? FLATS[spelled] : spelled;
  const index = pitch === undefined ? -1 : SHARPS.indexOf(pitch);
  if (index < 0) throw new Error("unknown note: " + JSON.stringify(note));

  return 12 * (octave + 1) + index;
}

export function semitoneToNote(semitone) {
  if (!Number.isInteger(semitone)) throw new TypeError("semitone: must be an integer");
  if (semitone < 0 || semitone > 127) throw new RangeError("semitone out of MIDI range: " + semitone);
  const octave = Math.floor(semitone / 12) - 1;
  return SHARPS[semitone % 12] + octave;
}

// Transpose a list of notes by whole semitones. An octave shift is 12, so the
// same call covers "up an octave" and "up a fifth" (7).
export function transpose(notes, semitones) {
  if (!Array.isArray(notes)) throw new TypeError("notes: must be an array");
  if (!Number.isInteger(semitones)) throw new TypeError("semitones: must be an integer");
  return notes.map((note) => semitoneToNote(noteToSemitone(note) + semitones));
}

// Transpose by whole octaves only: a spelling-preserving helper for the
// arranger, which must not silently turn `Bb` into `A#`.
export function transposeOctaves(notes, octaves) {
  if (!Number.isInteger(octaves)) throw new TypeError("octaves: must be an integer");
  if (!Array.isArray(notes)) throw new TypeError("notes: must be an array");
  return notes.map((note) => {
    const match = NOTE.exec(note.trim());
    if (!match) throw new Error("unknown note: " + JSON.stringify(note));
    const octave = Number(match[3]) + octaves;
    const rebuilt = match[1].toUpperCase() + match[2] + octave;
    noteToSemitone(rebuilt); // refuse a name the transposer would have made up
    return rebuilt;
  });
}
