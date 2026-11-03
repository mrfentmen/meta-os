// Musica data validators — pure functions over records, no I/O.
//
// The catalogue and library files are written by runtime/catalogue.py and
// runtime/library.py. These validators exist so a hand-edited or merged
// file can be checked before it is published: they return named errors and
// never repair a record.

const isNonEmptyString = (v) => typeof v === "string" && v.trim() !== "";

// A catalogue is the studio's published list. Each track carries the
// take it came from, a title, a duration, and the licence line the
// studio asserts over its own generated material.
export function validateCatalogue(catalogue) {
  const errors = [];
  if (!catalogue || typeof catalogue !== "object" || Array.isArray(catalogue)) {
    return ["catalogue: must be an object"];
  }
  if (!isNonEmptyString(catalogue.session_id)) {
    errors.push("catalogue.session_id: must be a non-empty string");
  }
  if (!Array.isArray(catalogue.tracks)) {
    errors.push("catalogue.tracks: must be an array");
    return errors;
  }

  const seen = new Map();
  catalogue.tracks.forEach((track, i) => {
    const at = "catalogue.tracks[" + i + "]";
    if (!track || typeof track !== "object") {
      errors.push(at + ": must be an object");
      return;
    }
    if (!isNonEmptyString(track.take_id)) {
      errors.push(at + ".take_id: must be a non-empty string");
    } else if (seen.has(track.take_id)) {
      errors.push(
        at + ".take_id: duplicate id " + JSON.stringify(track.take_id) +
        " (first seen at tracks[" + seen.get(track.take_id) + "])",
      );
    } else {
      seen.set(track.take_id, i);
    }
    if (!isNonEmptyString(track.title)) {
      errors.push(at + ".title: must be a non-empty string");
    }
    if (typeof track.duration_s !== "number" || !Number.isFinite(track.duration_s) || track.duration_s <= 0) {
      errors.push(at + ".duration_s: must be a positive number");
    }
    if (!isNonEmptyString(track.licence)) {
      errors.push(at + ".licence: must be a non-empty string");
    }
  });
  return errors;
}

// A library holding is a prompt the studio ran, with the counts it
// produced and the takes it kept. Rights are data: every holding must
// carry the licence it was kept under.
export function validateLibrary(library) {
  const errors = [];
  if (!library || typeof library !== "object" || Array.isArray(library)) {
    return ["library: must be an object"];
  }
  if (!Array.isArray(library.prompts)) {
    errors.push("library.prompts: must be an array");
    return errors;
  }
  library.prompts.forEach((holding, i) => {
    const at = "library.prompts[" + i + "]";
    if (!holding || typeof holding !== "object") {
      errors.push(at + ": must be an object");
      return;
    }
    if (!isNonEmptyString(holding.brief_id)) {
      errors.push(at + ".brief_id: must be a non-empty string");
    }
    if (typeof holding.keeper_rate !== "number" || !Number.isFinite(holding.keeper_rate)) {
      errors.push(at + ".keeper_rate: must be a number");
    }
    if (!Array.isArray(holding.keeper_take_ids)) {
      errors.push(at + ".keeper_take_ids: must be an array");
    }
    if (!isNonEmptyString(holding.licence)) {
      errors.push(at + ".licence: rights missing — every holding needs its licence line");
    }
  });
  return errors;
}

// Title normalisation is a pure text transform: trim the ends, collapse
// internal runs of whitespace, and title-case each word. It is idempotent,
// so a title already written by the studio passes through unchanged.
export function normalizeTitle(title) {
  if (typeof title !== "string") throw new TypeError("title: must be a string");
  return title
    .trim()
    .replace(/\s+/g, " ")
    .split(" ")
    .map((word) => (word === "" ? word : word[0].toUpperCase() + word.slice(1).toLowerCase()))
    .join(" ");
}
