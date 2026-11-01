// Musica genre briefs: HN-038. Three briefs must exist, parse to
// valid loop params, and drive a real logged session each.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, rmSync} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const briefs = join(root, "os/worlds/musica/briefs");

const EXPECTED = {
  chipsynth: { tempo: 132, key: "C", mode: "minor", waveform: "square", bars: 4 },
  ambient: { tempo: 72, key: "F", mode: "major", waveform: "triangle", bars: 2 },
  "boom-bap": { tempo: 90, key: "A", mode: "minor", waveform: "triangle", bars: 3 },
};

for (const [id, params] of Object.entries(EXPECTED)) {
  test(`brief ${id} parses and drives a logged session`, () => {
    const staging = join(root, "..", "staging", `musica-brief-${id}`);
    rmSync(staging, { recursive: true, force: true });
    const out = execFileSync("python3", [join(runtime, "compose.py"),
      "--session-dir", staging, "--brief-id", id,
      "--brief-file", join(briefs, `${id}.md`),
      "--takes", "1", "--seed-base", "8000"], { encoding: "utf8" });
    assert.match(out, /take-001/);
    const take = JSON.parse(
      readFileSync(join(staging, "take_log.jsonl"), "utf8").trim());
    assert.equal(take.brief_id, id);
    assert.equal(take.params.tempo, params.tempo);
    assert.equal(take.params.key, params.key);
    assert.equal(take.params.mode, params.mode);
    assert.equal(take.params.waveform, params.waveform);
    assert.equal(take.params.bars, params.bars);
    assert.ok(take.prompt.includes("brief"));
  });
}
