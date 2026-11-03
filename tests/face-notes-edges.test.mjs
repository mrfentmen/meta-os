// CB2-412..414 — notes rules, tested against face/logic.mjs.
//
// The store is an in-memory array in these tests; the window keeps the same
// array in localStorage. The rules are the same functions.
import test from "node:test";
import assert from "node:assert/strict";
import { deleteNote, findNote, newNote, updateNote } from "../face/logic.mjs";

test("CB2-412 a note can be created, listed and deleted", () => {
  let notes = [];
  notes = newNote(notes, 1, "Welcome", "hello");
  notes = newNote(notes, 2, "Second", "more");

  // Newest first, as the window shows them.
  assert.deepEqual(notes.map((n) => n.id), [2, 1]);
  assert.equal(findNote(notes, 1).title, "Welcome");
  assert.equal(findNote(notes, 99), null, "a missing note is null, never a blank one");

  notes = deleteNote(notes, 2);
  assert.deepEqual(notes.map((n) => n.id), [1]);
  assert.equal(findNote(notes, 2), null);
  // Deleting the last note leaves an empty list, not a phantom entry.
  notes = deleteNote(notes, 1);
  assert.deepEqual(notes, []);
});

test("CB2-413 an empty note body is allowed and pinned as the app's rule", () => {
  let notes = newNote([], 7);
  assert.deepEqual(notes[0], { id: 7, title: "Untitled", text: "" }, "a new note starts empty");

  // Saving an emptied body is a real save, not a refusal: the window has no
  // "empty note" error, and the note keeps its identity.
  notes = updateNote(notes, 7, { text: "" });
  assert.equal(findNote(notes, 7).text, "");
  notes = updateNote(notes, 7, { text: "   " });
  assert.equal(findNote(notes, 7).text, "   ", "whitespace is stored as typed, not trimmed");

  // An id that is not an integer is refused at creation; the window passes
  // Date.now(), so this only guards a caller mistake.
  assert.throws(() => newNote([], "7"), /id must be an integer/);
});

test("CB2-414 a saved note serialises with id, title and text and reloads intact", () => {
  let notes = newNote([], 11, "Kernel", "boot log");
  notes = updateNote(notes, 11, { title: "Kernel record" });
  const saved = JSON.stringify(notes);
  const back = JSON.parse(saved);

  assert.deepEqual(back, notes);
  assert.deepEqual(Object.keys(back[0]).sort(), ["id", "text", "title"], "exactly three fields");
  assert.equal(back[0].id, 11);
  assert.equal(back[0].title, "Kernel record");

  // Updating never rewrites the id, even when the patch carries one.
  const patched = updateNote(notes, 11, { id: 999, text: "changed" });
  assert.equal(patched[0].id, 11);
  assert.equal(patched[0].text, "changed");

  // The update is a copy: the array passed in is untouched.
  assert.equal(notes[0].text, "boot log");
});
