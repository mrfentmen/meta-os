// Musica MIDI export: HN-048. Keeper MIDI files must carry the
// take's own rendered notes (parsed back via pretty_midi), and the
// take record must gain midi_file in take-log format.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync, rmSync} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-midi-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("MIDI export writes the take's own notes via pretty_midi", () => {
  rmSync(staging, { recursive: true, force: true });
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "2", "--seed-base", "17000"]);
  py("keepers.py", [staging]);
  py("midi.py", [staging]);
  const log = readFileSync(join(staging, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  const keepers = log.filter((t) => t.verdict === "keeper");
  assert.ok(keepers.length >= 1);
  for (const take of keepers) {
    assert.ok(take.midi_file, take.take_id);
    assert.ok(existsSync(join(staging, take.midi_file)), take.midi_file);
  }
  const driver = `
import pretty_midi, sys
midi = pretty_midi.PrettyMIDI(${JSON.stringify(join(staging, keepers[0].midi_file))})
melody = [i for i in midi.instruments if i.program == 80]
bass = [i for i in midi.instruments if i.program == 38]
assert len(melody) == 1 and len(bass) == 1
assert len(melody[0].notes) > 0 and len(bass[0].notes) > 0
print("MIDI-OK", len(melody[0].notes), len(bass[0].notes))
`;
  const out = execFileSync("python3", ["-"], { input: driver, encoding: "utf8" });
  assert.match(out, /MIDI-OK/);
});
