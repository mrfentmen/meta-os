// Musica composition loop v1: HN-029. The loop must render real
// WAV audio, log every take, render deterministically, and replay a
// logged take byte-identically.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync, rmSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-loop-test");

function run(args) {
  return execFileSync("python3", [join(runtime, "compose.py"), ...args], {
    encoding: "utf8",
  });
}

test("loop renders real WAV takes and logs each one", () => {
  rmSync(staging, { recursive: true, force: true });
  run([
    "--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "3", "--seed-base", "5000",
  ]);
  const log = readFileSync(join(staging, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  assert.equal(log.length, 3);
  for (const take of log) {
    assert.equal(take.verdict, "pending");
    assert.ok(take.duration_s > 0);
    assert.match(take.sha256, /^[0-9a-f]{64}$/);
    const wav = readFileSync(join(staging, take.file));
    assert.equal(wav.subarray(0, 4).toString(), "RIFF");
    assert.ok(wav.length > 100000, "WAV too small to be real audio");
  }
  const hashes = new Set(log.map((t) => t.sha256));
  assert.equal(hashes.size, 3, "takes must differ by seed");
});

test("loop is deterministic and replays a logged take byte-identically", () => {
  const out = join(staging, "replay.wav");
  const printed = run([
    "--replay", join(staging, "take_log.jsonl"), "take-001", out,
  ]);
  const logged = JSON.parse(
    readFileSync(join(staging, "take_log.jsonl"), "utf8").trim().split("\n")[0]);
  assert.match(printed, new RegExp(logged.sha256));
  assert.ok(existsSync(out));
  rmSync(staging, { recursive: true, force: true });
});
