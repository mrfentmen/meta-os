// Musica studio board v1: HN-032. The page must show the live
// session from real records: real take ids, real counts, and an
// audio element pointing at a real keeper file.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-board-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("board shows the live session from real records", () => {
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "3", "--seed-base", "9100"]);
  py("keepers.py", [staging]);
  py("catalogue.py", [staging]);
  py("board.py", [staging]);
  const board = readFileSync(join(staging, "board.html"), "utf8");
  const log = readFileSync(join(staging, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  for (const take of log) {
    assert.ok(board.includes(take.take_id), take.take_id);
    assert.ok(board.includes(take.sha256.slice(0, 12)), take.take_id);
  }
  const keepers = log.filter((t) => t.verdict === "keeper");
  assert.ok(keepers.length >= 1);
  assert.ok(board.includes(`<audio controls src="keepers/${keepers[0].take_id}.wav">`));
  assert.ok(board.includes(`Keepers: ${keepers.length}`));
});
