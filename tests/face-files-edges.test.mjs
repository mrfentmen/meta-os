// CB2-423 — Files rules, tested against face/logic.mjs.
//
// The Files window lists from the same filter and renders its header through
// the same path guard, so an escape it refuses is one the window cannot show.
import test from "node:test";
import assert from "node:assert/strict";
import { filesIn, resolvePath, withinRoot } from "../face/logic.mjs";

const store = [
  { id: 1, name: "README.txt", folder: "Home", trashed: false },
  { id: 2, name: "K7-boot.txt", folder: "Home/logs", trashed: false },
  { id: 3, name: "old.txt", folder: "Home", trashed: true },
];

test("CB2-423 the window lists the right tree and refuses a path that escapes its root", () => {
  assert.deepEqual(filesIn(store, false).map((f) => f.id), [1, 2], "live files only");
  assert.deepEqual(filesIn(store, true).map((f) => f.id), [3], "trash is its own list");
  assert.deepEqual(filesIn([], false), [], "an empty store lists nothing");

  // A path inside the root resolves with one separator, no doubled slashes.
  assert.equal(resolvePath("Home", "logs/K7-boot.txt"), "Home/logs/K7-boot.txt");
  assert.equal(resolvePath("Home/", "logs//K7-boot.txt"), "Home/logs/K7-boot.txt");
  assert.equal(resolvePath("Home", "./logs/./K7-boot.txt"), "Home/logs/K7-boot.txt");
  assert.equal(resolvePath("Home", "logs/../README.txt"), "Home/README.txt", "a step back inside the root is fine");

  // Anything that would leave the root is refused, not normalised away.
  assert.throws(() => resolvePath("Home", "../secrets.txt"), /escapes the root/);
  assert.throws(() => resolvePath("Home", "logs/../../secrets.txt"), /escapes the root/);
  assert.throws(() => resolvePath("Home", "/etc/passwd"), /absolute paths are refused/);
  assert.throws(() => resolvePath("Home", "C:\\\\Windows\\\\system32"), /absolute paths are refused/);
  assert.throws(() => resolvePath("Home", ""), /a relative path is required/);

  // The boolean form answers instead of throwing, for a header that must render.
  assert.equal(withinRoot("Home", "logs/K7-boot.txt"), true);
  assert.equal(withinRoot("Home", "../secrets.txt"), false);
  assert.equal(withinRoot("Home", "/etc/passwd"), false);
  assert.equal(withinRoot("Home", ""), false);
});
