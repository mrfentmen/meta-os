// Musica studio board v2: HN-041. The studio-wide board must
// browse every session's catalogue with a rights column and
// session history, from records only.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, rmSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const stagingMusica = join(root, "..", "staging", "musica-studio");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("studio board browses all session catalogues with rights", () => {
  rmSync(stagingMusica, { recursive: true, force: true });
  for (const id of ["studio-a", "studio-b"]) {
    py("overnight.py", ["--session-dir", join(stagingMusica, "sessions", id),
      "--brief-id", "chipsynth",
      "--brief-file", join(root, "os/worlds/musica/briefs/chipsynth.md"),
      "--takes", "3", "--seed-base", id === "studio-a" ? 12000 : 13000]);
  }
  py("board.py", ["--studio", stagingMusica,
    "--out", join(stagingMusica, "board", "board.html")]);
  const board = readFileSync(join(stagingMusica, "board", "board.html"), "utf8");
  for (const id of ["studio-a", "studio-b"]) {
    assert.ok(board.includes(`Session ${id}`), id);
  }
  assert.ok(board.includes("Rights"));
  assert.ok(board.includes("own — generated in-studio"));
  assert.ok(board.includes("Keeper pass:"));
  assert.ok(board.includes("Variation pass:"));
});
