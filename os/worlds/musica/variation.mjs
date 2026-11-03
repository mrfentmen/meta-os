// Musica variation math — a seeded note generator, data only.
//
// The studio's variation pass asks whether a take is too close to another take.
// This module is the other half of that question: given a seed and a scale, it
// produces the note sequence a variation bar would play. It is deliberately
// small and pure — no audio, no clock, no Math.random — so the same seed always
// produces the same notes and a test can pin them.
//
// Pitch names come from `note_math.mjs`, so a note this module emits is always a
// note the rest of the studio can read back.
import { PITCH_CLASSES } from "./note_math.mjs";

// mulberry32: a 32-bit generator small enough to read. The seed is the only
// input, so two runs with the same seed cannot drift apart.
function makeRng(seed) {
  let state = seed >>> 0;
  return function next() {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Every semitone in `low..high` whose pitch class is in `scale`.
 * Throws on a scale name that is not a pitch class, an empty scale, or a range
 * that holds no scale note — an empty pool would silently produce a silent bar.
 */
export function scalePool(scale, low, high) {
  if (!Array.isArray(scale) || scale.length === 0) {
    throw new Error("variation: a scale is required");
  }
  if (!Number.isInteger(low) || !Number.isInteger(high)) {
    throw new TypeError("variation: range bounds must be integers");
  }
  if (low > high) throw new RangeError("variation: low " + low + " is above high " + high);

  const classes = new Set();
  for (const name of scale) {
    if (typeof name !== "string") throw new TypeError("variation: scale entries must be strings");
    const index = PITCH_CLASSES.indexOf(name.trim());
    if (index < 0) throw new Error("variation: unknown scale note " + JSON.stringify(name));
    classes.add(index);
  }

  const pool = [];
  for (let semitone = low; semitone <= high; semitone++) {
    if (classes.has(((semitone % 12) + 12) % 12)) pool.push(semitone);
  }
  if (pool.length === 0) {
    throw new RangeError("variation: no scale note falls between " + low + " and " + high);
  }
  return pool;
}

/**
 * A variation bar: `length` notes drawn from the scale, in the given range.
 * `seed` fixes the sequence; the same seed and arguments always give the same
 * notes. The first note is the scale root in the range so a bar starts where the
 * listener expects it, and every later note is a seeded draw from the pool.
 */
export function variationNotes({ seed, scale, length = 16, low = 60, high = 84 } = {}) {
  if (!Number.isInteger(seed)) throw new TypeError("variation: seed must be an integer");
  if (!Number.isInteger(length) || length < 1) {
    throw new RangeError("variation: length must be a positive integer");
  }
  const pool = scalePool(scale, low, high);
  const rng = makeRng(seed);
  const notes = [pool[0]];
  for (let i = 1; i < length; i++) {
    notes.push(pool[Math.floor(rng() * pool.length)]);
  }
  return notes;
}

/** The same notes as names (`C4`, `F#5`), the form the catalogue and score use. */
export function variationNoteNames(options) {
  return variationNotes(options).map((semitone) => PITCH_CLASSES[semitone % 12] + (Math.floor(semitone / 12) - 1));
}
