// Musica scout: HN-046. ADOPTIONS.md must name 5 candidates with
// a licence and a verdict each.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

test("adoptions file covers 5 candidates with licences and verdicts", () => {
  const doc = readFileSync(
    join(root, "os/worlds/musica/ADOPTIONS.md"), "utf8");
  for (const [name, licence] of [
    ["basic-pitch", "Apache-2.0"],
    ["pretty_midi", "MIT"],
    ["librosa", "ISC"],
    ["aubio", "GPL-3.0-or-later"],
    ["Magenta", "Apache-2.0"],
  ]) {
    assert.ok(doc.includes(name), name);
    assert.ok(doc.includes(licence), `${name} licence`);
  }
  assert.match(doc, /ADOPT/);
});
