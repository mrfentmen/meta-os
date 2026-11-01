// Musica variation engine: HN-037. Distinct-seed takes must pass;
// a gain-changed copy of a keeper must be rejected as a clone.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-variation-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

const driver = `
import json, os, struct, sys, wave
sys.path.insert(0, ${JSON.stringify(runtime)})
from compose import render_take
from keepers import apply_keepers
from similarity import apply_variation

staging = ${JSON.stringify(staging)}
params = {"tempo": 132, "key": "C", "mode": "minor", "waveform": "square", "bars": 4}
render_take(params, 4001, os.path.join(staging, "takes", "take-001.wav"))
# Clone: gain-changed copy of take-001, logged as a second take.
with wave.open(os.path.join(staging, "takes", "take-001.wav")) as fh:
    n = fh.getnframes(); sr = fh.getframerate(); raw = fh.readframes(n)
s = struct.unpack(f"<{n}h", raw)
with wave.open(os.path.join(staging, "takes", "take-002.wav"), "wb") as fh:
    fh.setnchannels(1); fh.setsampwidth(2); fh.setframerate(sr)
    fh.writeframes(b"".join(struct.pack("<h", max(-32767, min(32767, int(x * 0.9)))) for x in s))
import hashlib
def sha(p):
    d = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(65536), b""): d.update(c)
    return d.hexdigest()
base = {"session_id": "variation-test", "timestamp": "2026-11-01T06:00:00Z",
        "brief_id": "chipsynth", "prompt": "chipsynth brief",
        "params": params, "duration_s": 7.273, "verdict": "keeper",
        "reason": "passes length, loudness, silence, repetition",
        "spark_assist": None, "human_verdict": None}
os.makedirs(os.path.join(staging, "takes"), exist_ok=True)
t1 = dict(base, take_id="take-001", seed=4001, file="takes/take-001.wav",
          sha256=sha(os.path.join(staging, "takes", "take-001.wav")))
t2 = dict(base, take_id="take-002", seed=4002, file="takes/take-002.wav",
          sha256=sha(os.path.join(staging, "takes", "take-002.wav")))
with open(os.path.join(staging, "take_log.jsonl"), "w") as fh:
    for t in (t1, t2): fh.write(json.dumps(t, sort_keys=True) + "\\n")
summary = apply_variation(staging)
assert summary["clones"] == 1, summary
with open(os.path.join(staging, "take_log.jsonl")) as fh:
    takes = [json.loads(l) for l in fh]
assert takes[0]["verdict"] == "keeper"
assert takes[1]["verdict"] == "reject", takes[1]
assert takes[1]["clone_of"] == "take-001"
assert "near-identical" in takes[1]["reason"]
print("VARIATION-OK")
`;

test("variation pass rejects a near-identical clone", () => {
  const out = execFileSync("python3", ["-"], { input: driver, encoding: "utf8" });
  assert.match(out, /VARIATION-OK/);
});
