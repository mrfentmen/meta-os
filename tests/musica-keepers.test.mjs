// Musica keeper rules: HN-030. The bar must pass a real take and
// reject degenerate audio (silent, truncated, single-bar loop).
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");

const driver = `
import os, struct, sys, wave
sys.path.insert(0, ${JSON.stringify(runtime)})
from compose import render_take
from keepers import measure, keeper_verdict

staging = os.path.join(${JSON.stringify(join(root, "..", "staging"))}, "musica-keeper-test")
os.makedirs(staging, exist_ok=True)
params = {"tempo": 132, "key": "C", "mode": "minor", "waveform": "square", "bars": 4}
dur, sha = render_take(params, 777, os.path.join(staging, "real.wav"))
v, r = keeper_verdict(measure(os.path.join(staging, "real.wav"), params))
assert v == "keeper", (v, r)

def write_wav(path, samples, sr=22050):
    with wave.open(path, "wb") as fh:
        fh.setnchannels(1); fh.setsampwidth(2); fh.setframerate(sr)
        fh.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in samples))

# Silent 8s take: must fail loudness + silence.
write_wav(os.path.join(staging, "silent.wav"), [0.0] * (22050 * 8))
v, r = keeper_verdict(measure(os.path.join(staging, "silent.wav"), params))
assert v == "reject" and "loudness" in r and "silence" in r, (v, r)

# Truncated 1s take: must fail duration.
write_wav(os.path.join(staging, "short.wav"), [0.5] * 22050)
v, r = keeper_verdict(measure(os.path.join(staging, "short.wav"), params))
assert v == "reject" and "duration" in r, (v, r)

# One bar of tone repeated 4x: must fail repetition.
import math
bar = [0.4 * math.sin(2 * math.pi * 220 * i / 22050) for i in range(int(4 * 60 / 132 * 22050))]
write_wav(os.path.join(staging, "loop.wav"), bar * 4)
v, r = keeper_verdict(measure(os.path.join(staging, "loop.wav"), params))
assert v == "reject" and "repetition" in r, (v, r)
print("KEEPERS-OK")
`;

test("keeper bar passes real takes and rejects degenerate audio", () => {
  const out = execFileSync("python3", ["-"], { input: driver, encoding: "utf8" });
  assert.match(out, /KEEPERS-OK/);
});
