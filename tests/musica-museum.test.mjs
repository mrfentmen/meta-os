// Musica failure museum: HN-042. Rejects must render with their
// real reasons, grouped by category, from session logs only.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, rmSync} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-museum-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("museum renders real rejects with reasons", () => {
  rmSync(staging, { recursive: true, force: true });
  const session = join(staging, "sessions", "museum-a");
  py("compose.py", ["--session-dir", session, "--brief-id", "chipsynth",
    "--takes", "3", "--seed-base", "14000"]);
  // Silence one take's audio, then the keeper pass must reject it.
  const log = readFileSync(join(session, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  const victim = log[1];
  const wav = readFileSync(join(session, victim.file));
  const silent = Buffer.from(wav);
  silent.fill(0, 44); // keep the RIFF header, zero the samples
  writeFileSync(join(session, victim.file), silent);
  py("keepers.py", [session]);
  py("museum.py", [staging, "--out", join(staging, "board", "museum.html")]);
  const museum = readFileSync(join(staging, "board", "museum.html"), "utf8");
  assert.ok(museum.includes(victim.take_id));
  assert.ok(museum.includes("silence") || museum.includes("loudness"));
  assert.ok(museum.includes("Rejects by reason"));
});
