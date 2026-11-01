// Musica demo cut: HN-054. The cut must land on its target
// length from real keeper excerpts, with every segment labelled
// by its source take.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, rmSync} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-demo-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("demo cut lands on target from labelled keeper excerpts", () => {
  rmSync(staging, { recursive: true, force: true });
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "5", "--seed-base", "1000"]);
  py("keepers.py", [staging]);
  py("catalogue.py", [staging]);
  py("normalize.py", [staging]);
  py("demo_cut.py", [staging, "--target", "10",
    "--out", join(staging, "demo-cut.wav")]);
  const manifest = JSON.parse(readFileSync(join(staging, "demo-cut.json"), "utf8"));
  assert.equal(manifest.target_s, 10);
  assert.ok(Math.abs(manifest.actual_s - 10) <= 0.05, JSON.stringify(manifest));
  assert.ok(manifest.segments.length >= 2);
  const total = manifest.segments.reduce((sum, s) => sum + s.excerpt_s, 0);
  assert.ok(Math.abs(total - 10) <= 0.05);
  for (const seg of manifest.segments) {
    assert.ok(seg.take_id);
    assert.ok(seg.session_id);
  }
});
