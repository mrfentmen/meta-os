// Musica first catalogue: HN-031. Keepers export with a licence
// and provenance line per track; rejects never appear.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-catalogue-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("catalogue exports keepers with licence and provenance", () => {
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "4", "--seed-base", "9000"]);
  py("keepers.py", [staging]);
  const out = py("catalogue.py", [staging]);
  const catalogue = JSON.parse(readFileSync(join(staging, "catalogue.json"), "utf8"));
  assert.match(out, /catalogue tracks=\d+/);
  assert.ok(catalogue.tracks.length >= 1, "expected at least one keeper");
  assert.ok(catalogue.tracks.length <= 4);
  for (const track of catalogue.tracks) {
    assert.match(track.licence, /own/);
    assert.match(track.provenance, /compose\.py/);
    assert.match(track.provenance, /seed \d+/);
    assert.ok(existsSync(join(staging, track.file)), track.file);
    assert.match(track.sha256, /^[0-9a-f]{64}$/);
  }
  const log = readFileSync(join(staging, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  const keeperIds = new Set(log.filter((t) => t.verdict === "keeper").map((t) => t.take_id));
  assert.deepEqual(
    new Set(catalogue.tracks.map((t) => t.take_id)), keeperIds);
});
