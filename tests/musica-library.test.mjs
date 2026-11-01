// Musica prompt library: HN-043. Keeper rates must be computed
// from the logs, never invented.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-library-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("prompt library reports keeper rates from the logs", () => {
  const a = join(staging, "sessions", "lib-a");
  const b = join(staging, "sessions", "lib-b");
  py("compose.py", ["--session-dir", a, "--brief-id", "chipsynth",
    "--brief-text", "prompt alpha", "--takes", "2", "--seed-base", "15000"]);
  py("compose.py", ["--session-dir", b, "--brief-id", "chipsynth",
    "--brief-text", "prompt beta", "--takes", "2", "--seed-base", "16000"]);
  py("keepers.py", [a]);
  py("keepers.py", [b]);
  py("library.py", [staging, "--out", join(staging, "prompts", "library.json")]);
  const library = JSON.parse(readFileSync(join(staging, "prompts", "library.json"), "utf8"));
  assert.equal(library.prompts.length, 2);
  for (const group of library.prompts) {
    assert.equal(group.takes, 2);
    assert.equal(group.keeper_rate, group.keepers / group.takes);
    assert.ok(group.keeper_take_ids.length === group.keepers);
  }
});
