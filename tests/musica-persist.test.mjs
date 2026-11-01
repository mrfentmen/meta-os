// Musica session persistence: HN-033. Kill and restart must lose
// no takes: resume continues after the last logged take, refuses
// to overwrite without --resume, and re-renders an orphaned take
// (rendered but never logged, as in a mid-take kill) identically.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-persist-test");

function py(args) {
  return execFileSync("python3", [join(runtime, "compose.py"), ...args], {
    encoding: "utf8",
  });
}

function logLines() {
  return readFileSync(join(staging, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
}

test("resume after a simulated mid-take kill loses no takes", () => {
  py(["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "3", "--seed-base", "3000"]);
  const original = logLines();
  assert.equal(original.length, 3);

  // Re-run without --resume must refuse, never overwrite.
  const refused = spawnSync("python3",
    [join(runtime, "compose.py"), "--session-dir", staging,
     "--brief-id", "chipsynth", "--takes", "1", "--seed-base", "3000"],
    { encoding: "utf8" });
  assert.notEqual(refused.status, 0);
  assert.equal(logLines().length, 3);

  // Simulate a kill between render and log-append: drop the last
  // log line but leave its WAV orphaned on disk.
  const orphanHash = original[2].sha256;
  writeFileSync(join(staging, "take_log.jsonl"),
    original.slice(0, 2).map((t) => JSON.stringify(t)).join("\n") + "\n");
  py(["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "2", "--seed-base", "3000", "--resume"]);
  const resumed = logLines();
  assert.deepEqual(
    resumed.map((t) => t.take_id),
    ["take-001", "take-002", "take-003", "take-004"]);
  // The orphaned take re-rendered byte-identically.
  assert.equal(resumed[2].sha256, orphanHash);
});
