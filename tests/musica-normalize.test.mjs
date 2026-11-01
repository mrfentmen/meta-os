// Musica loudness normalisation: HN-036. Every catalogue track
// must be normalised to the stated LUFS target with before/after
// measured per track, and the normalised file must exist.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync, rmSync} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-norm-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("catalogue tracks normalise to -16 LUFS with before/after", () => {
  rmSync(staging, { recursive: true, force: true });
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "3", "--seed-base", "9300"]);
  py("keepers.py", [staging]);
  py("catalogue.py", [staging]);
  py("normalize.py", [staging]);
  const norm = JSON.parse(readFileSync(join(staging, "normalization.json"), "utf8"));
  assert.equal(norm.target_lufs, -16.0);
  assert.ok(norm.tracks.length >= 1);
  for (const row of norm.tracks) {
    assert.ok(Math.abs(row.after_lufs - (-16.0)) <= 1.0, JSON.stringify(row));
    assert.equal(row.within_tolerance, true);
    assert.ok(existsSync(join(staging, "normalized", `${row.take_id}.wav`)));
  }
  const catalogue = JSON.parse(readFileSync(join(staging, "catalogue.json"), "utf8"));
  for (const track of catalogue.tracks) {
    assert.ok(track.normalized_file);
    assert.ok(track.loudness);
  }
});
