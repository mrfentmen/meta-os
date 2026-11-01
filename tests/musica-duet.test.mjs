// Musica duet mode scoping: HN-044. Scoping only: the doc must
// exist, state the never-grade-your-own-work rule, and state
// plainly that no duet code is built.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

test("duet scope doc states the rule and its unbuilt status", () => {
  const doc = readFileSync(
    join(root, "os/worlds/musica/docs/DUET_SCOPE.md"), "utf8");
  assert.match(doc, /SCOPING ONLY, NOT BUILT/);
  assert.match(doc, /never-grade-your-own-work/i);
  assert.match(doc, /NEVER graded by the loop that composed it/);
});
