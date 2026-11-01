// Musica board empty states: HN-053. Before any session exists,
// both boards must show the honest "no sessions yet" state,
// never an empty table or a placeholder session.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-empty-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("boards show the honest no-sessions-yet state", () => {
  py("board.py", [join(staging, "sessions", "nothing-here"),
    "--out", join(staging, "session-board.html")]);
  const sessionBoard = readFileSync(join(staging, "session-board.html"), "utf8");
  assert.ok(sessionBoard.includes("No sessions yet"));
  py("board.py", ["--studio", staging,
    "--out", join(staging, "board", "board.html")]);
  const studioBoard = readFileSync(join(staging, "board", "board.html"), "utf8");
  assert.ok(studioBoard.includes("No sessions yet"));
  assert.ok(!studioBoard.includes("Session "));
});
