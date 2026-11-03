// CB2-368: one board note, validated as data.
//
// The note record board.mjs stores (both `messageToNote`'s adapted relay
// message and a post from POST /rooms/<room>/posts):
//
//   {id, room, title, author, text, ts, deleted}
//
// The caps are the board's own (MAX_TITLE_CHARS 200, MAX_NICK_CHARS 40,
// MAX_TEXT_CHARS 2000), so a note accepted here is one the board would
// have accepted. `text` may be empty -- the board allows a title-only
// post; `title` may not.
//
// Returns named errors; [] when the note is valid. Never echoes the text.

export const ROOM_RE = /^[a-z0-9-]{1,32}$/;
export const MAX_AUTHOR_CHARS = 40;
export const MAX_TITLE_CHARS = 200;
export const MAX_TEXT_CHARS = 2000;

const NOTE_KEYS = ["id", "room", "title", "author", "text", "ts", "deleted"];

function isSingleLine(value, maxChars) {
  return (
    typeof value === "string" &&
    value.length >= 1 &&
    value.length <= maxChars &&
    !/[\u0000-\u001f\u007f]/.test(value)
  );
}

export function validateNoteRecord(note) {
  if (!note || typeof note !== "object" || Array.isArray(note)) {
    return ["note: must be an object"];
  }
  const errors = [];
  if (!("id" in note)) {
    errors.push("id: missing");
  } else if (typeof note.id !== "string" || note.id.trim() === "") {
    errors.push("id: must be a non-empty string");
  }
  if (!("room" in note)) {
    errors.push("room: missing");
  } else if (typeof note.room !== "string" || !ROOM_RE.test(note.room)) {
    errors.push("room: must match [a-z0-9-]{1,32}");
  }
  if (!("title" in note)) {
    errors.push("title: missing");
  } else if (!isSingleLine(note.title, MAX_TITLE_CHARS)) {
    errors.push(`title: must be a single line of 1-${MAX_TITLE_CHARS} chars`);
  }
  if (!("author" in note)) {
    errors.push("author: missing");
  } else if (!isSingleLine(note.author, MAX_AUTHOR_CHARS)) {
    errors.push(`author: must be a single line of 1-${MAX_AUTHOR_CHARS} chars`);
  }
  if (!("text" in note)) {
    errors.push("text: missing");
  } else if (
    typeof note.text !== "string" ||
    note.text.length > MAX_TEXT_CHARS ||
    /[\u0000-\u001f\u007f]/.test(note.text)
  ) {
    errors.push(`text: must be a single line of 0-${MAX_TEXT_CHARS} chars`);
  }
  if (!("ts" in note)) {
    errors.push("ts: missing");
  } else if (!Number.isInteger(note.ts) || note.ts < 0) {
    errors.push("ts: must be a non-negative integer of epoch seconds");
  }
  if (!("deleted" in note)) {
    errors.push("deleted: missing");
  } else if (typeof note.deleted !== "boolean") {
    errors.push("deleted: must be a boolean");
  }
  for (const key of Object.keys(note)) {
    if (!NOTE_KEYS.includes(key)) errors.push(`unexpected field: ${key}`);
  }
  return errors;
}
