// Musica rights log: HN-035. A track with an empty or
// unrecognised rights line must be rejected, never exported.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, rmSync} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-rights-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("rights check rejects tracks with empty rights lines", () => {
  rmSync(staging, { recursive: true, force: true });
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "3", "--seed-base", "9200"]);
  py("keepers.py", [staging]);
  py("catalogue.py", [staging]);
  // Tamper: blank one track's licence.
  const cataloguePath = join(staging, "catalogue.json");
  const catalogue = JSON.parse(readFileSync(cataloguePath, "utf8"));
  assert.ok(catalogue.tracks.length >= 1);
  catalogue.tracks[0].licence = "";
  writeFileSync(cataloguePath, JSON.stringify(catalogue, null, 2));
  const out = py("rights.py", [staging, "--enforce"]);
  assert.match(out, /violations=1/);
  const after = JSON.parse(readFileSync(cataloguePath, "utf8"));
  assert.equal(after.tracks.length, catalogue.tracks.length - 1);
  const rights = JSON.parse(readFileSync(join(staging, "rights.json"), "utf8"));
  assert.equal(rights.rejected.length, 1);
  assert.equal(rights.rejected[0].take_id, catalogue.tracks[0].take_id);
});
