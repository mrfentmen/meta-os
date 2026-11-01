// labs/music3d/notes-data.mjs — single source of truth for scale, heights,
// frequencies. Imported by index.html AND by tests/validate.test.mjs, so the
// test guards the exact data the page plays.
export const A4 = 440;
const NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
export function freqOf(name) {
  const m = /^([A-G]#?)(\d)$/.exec(name);
  const semis = NAMES.indexOf(m[1]) + (parseInt(m[2], 10) + 1) * 12;
  return A4 * Math.pow(2, (semis - 69) / 12);
}
// C major ascending + descending; value = note type (whole|half|quarter|eighth).
export const SCALE = [
  { n: "C4", v: "whole" }, { n: "D4", v: "half" },
  { n: "E4", v: "quarter" }, { n: "F4", v: "quarter" },
  { n: "G4", v: "quarter" }, { n: "A4", v: "eighth" },
  { n: "B4", v: "eighth" }, { n: "C5", v: "whole" },
  { n: "B4", v: "quarter" }, { n: "A4", v: "quarter" },
  { n: "G4", v: "quarter" }, { n: "F4", v: "quarter" },
  { n: "E4", v: "half" }, { n: "D4", v: "half" }, { n: "C4", v: "whole" },
];
// Second voice: the same scale one octave up (NB-041), rendered smaller.
export function octaveUp(name) {
  const m = /^([A-G]#?)(\d)$/.exec(name);
  return m[1] + (parseInt(m[2], 10) + 1);
}
// Staff height map: diatonic steps from E4 (bottom line), half-spacings.
// Covers C4 (2 steps below) to C6 (top of second voice).
const STEP = { F3: -6, G3: -5, A3: -4, B3: -3, C4: -2, D4: -1, E4: 0, F4: 1, G4: 2, A4: 3, B4: 4, C5: 5,
  D5: 6, E5: 7, F5: 8, G5: 9, A5: 10, B5: 11, C6: 12 };
export const NOTE_Y = {};
for (const [k, s] of Object.entries(STEP)) NOTE_Y[k] = s;
export const BEATS = { whole: 4, half: 2, quarter: 1, eighth: 0.5 };
// A natural minor, ascending + descending (NC-049 second playable row).
export const MINOR_SCALE = [
  { n: "A4", v: "quarter" }, { n: "B4", v: "quarter" },
  { n: "C5", v: "quarter" }, { n: "D5", v: "quarter" },
  { n: "E5", v: "quarter" }, { n: "F5", v: "quarter" },
  { n: "G5", v: "quarter" }, { n: "A5", v: "whole" },
  { n: "G5", v: "quarter" }, { n: "F5", v: "quarter" },
  { n: "E5", v: "quarter" }, { n: "D5", v: "quarter" },
  { n: "C5", v: "quarter" }, { n: "B4", v: "quarter" },
  { n: "A4", v: "whole" },
];
// Chord stacks (NC-050): three-note columns, root position.
export const CHORDS = {
  C: [{ n: "C4", v: "half" }, { n: "E4", v: "half" }, { n: "G4", v: "half" }],
  G: [{ n: "G3", v: "half" }, { n: "B3", v: "half" }, { n: "D4", v: "half" }],
  Am: [{ n: "A3", v: "half" }, { n: "C4", v: "half" }, { n: "E4", v: "half" }],
  F: [{ n: "F3", v: "half" }, { n: "A3", v: "half" }, { n: "C4", v: "half" }],
};
export const CHORD_ORDER = ["C", "G", "Am", "F"];
