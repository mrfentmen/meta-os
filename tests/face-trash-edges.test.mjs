// CB2-424 — Trash rules, tested against face/logic.mjs.
//
// Delete and Restore in the Files/Trash windows call these functions, so the
// path a restored file lands on is the path this test pins.
import test from "node:test";
import assert from "node:assert/strict";
import { emptyTrash, filesIn, moveToTrash, restoreFromTrash } from "../face/logic.mjs";

const store = () => [
  { id: 1, name: "README.txt", folder: "Home", trashed: false, content: "a" },
  { id: 2, name: "K7-boot.txt", folder: "Home/logs", trashed: false, content: "b" },
];

test("CB2-424 delete moves a file to Trash and restore returns it to its original folder", () => {
  let fs = moveToTrash(store(), 2);
  assert.deepEqual(filesIn(fs, false).map((f) => f.id), [1], "the file leaves Files");
  assert.deepEqual(filesIn(fs, true).map((f) => f.id), [2], "and lands in Trash");
  assert.equal(fs.find((f) => f.id === 2).folder, "Home/logs", "the original folder is kept while trashed");

  fs = restoreFromTrash(fs, 2);
  assert.deepEqual(filesIn(fs, false).map((f) => f.id), [1, 2]);
  const restored = fs.find((f) => f.id === 2);
  assert.equal(restored.folder, "Home/logs", "restored to the folder it came from");
  assert.equal(restored.name, "K7-boot.txt");
  assert.equal(restored.content, "b", "content is untouched by the round trip");
  assert.equal(restored.trashed, false);

  // Emptying the trash removes only trashed files and is idempotent.
  fs = emptyTrash(moveToTrash(fs, 1));
  assert.deepEqual(fs.map((f) => f.id), [2]);
  assert.deepEqual(emptyTrash(fs).map((f) => f.id), [2], "a second empty changes nothing");
  assert.deepEqual(emptyTrash([]), []);

  // A missing id is refused by name rather than silently deleting nothing.
  assert.throws(() => moveToTrash(store(), 99), /no file with id 99/);
  assert.throws(() => restoreFromTrash(store(), 99), /no file with id 99/);

  // The array passed in is not mutated: the window saves the returned store.
  const before = store();
  moveToTrash(before, 1);
  assert.equal(before[0].trashed, false);
});
