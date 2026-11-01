// Musica Spark assist: HN-034. Prompts must follow the repo's
// builder contract (JSON-only, limitations stated), and every
// attempt must be recorded in the take log -- with no live call
// from the sandbox (held/not_configured, never a fabricated reply).
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-spark-test");

const driver = `
import hashlib, os, sys
sys.path.insert(0, ${JSON.stringify(runtime)})
from spark_assist import (build_structure_prompt, build_lyric_prompt,
                          request_assist)
from take_log import validate_take

structure = build_structure_prompt("chipsynth", "fast square-wave chip", 4)
assert "JSON ONLY" in structure and "chipsynth" in structure
assert "copyrighted" in structure
lyrics = build_lyric_prompt("night drive", 4)
assert "JSON ONLY" in lyrics and "night drive" in lyrics
assert "original" in lyrics

held = request_assist(structure, env={})
assert held["status"] == "held"
assert held["prompt_sha256"] == hashlib.sha256(structure.encode()).hexdigest()
nocfg = request_assist(structure, env={"ASSESS_LIVE_MODEL": "1"})
assert nocfg["status"] == "not_configured"

# A take carrying a recorded assist attempt must still validate.
take = {
    "take_id": "take-001", "session_id": "s1",
    "timestamp": "2026-11-01T06:00:00Z", "brief_id": "chipsynth",
    "prompt": "chipsynth brief", "seed": 1,
    "params": {"tempo": 132, "key": "C", "mode": "minor",
               "waveform": "square", "bars": 4},
    "duration_s": 7.273, "file": "takes/take-001.wav",
    "sha256": "0" * 64, "verdict": "pending", "reason": "",
    "spark_assist": held, "human_verdict": None,
}
assert validate_take(take) == [], validate_take(take)
print("SPARK-OK")
`;

test("spark builders follow the repo contract and record attempts", () => {
  const out = execFileSync("python3", ["-"], { input: driver, encoding: "utf8" });
  assert.match(out, /SPARK-OK/);
});

test("loop with --spark-assist records an attempt per take", () => {
  execFileSync("python3", [join(runtime, "compose.py"),
    "--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "2", "--seed-base", "6000", "--spark-assist", "structure"],
    { encoding: "utf8" });
  const log = readFileSync(join(staging, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  assert.equal(log.length, 2);
  for (const take of log) {
    assert.ok(take.spark_assist, "spark_assist missing");
    assert.ok(["held", "not_configured"].includes(take.spark_assist.status));
    assert.match(take.spark_assist.prompt_sha256, /^[0-9a-f]{64}$/);
  }
});
