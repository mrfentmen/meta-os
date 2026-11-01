// Musica take-log schema: HN-028. The Python validator is exercised
// through stdin (no temp files, no shell quoting) and must accept a
// well-formed take and reject each broken shape.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");

const driver = `
import json, sys
sys.path.insert(0, ${JSON.stringify(runtime)})
from take_log import validate_take

good = {
    "take_id": "take-001", "session_id": "s1",
    "timestamp": "2026-11-01T06:00:00Z", "brief_id": "chipsynth",
    "prompt": "chipsynth brief", "seed": 7,
    "params": {"tempo": 132, "key": "C", "mode": "minor",
               "waveform": "square", "bars": 4},
    "duration_s": 8.0, "file": "takes/take-001.wav",
    "sha256": "0" * 64, "verdict": "pending", "reason": "",
    "spark_assist": None, "human_verdict": None,
}
assert validate_take(good) == [], validate_take(good)
for mutate, want in [
    ({"verdict": "maybe"}, "verdict"),
    ({"timestamp": "Nov 1 2026"}, "timestamp"),
    ({"seed": -1}, "seed"),
    ({"sha256": "zz"}, "sha256"),
    ({"verdict": "keeper", "reason": ""}, "reason"),
    ({"spark_assist": {"status": "faked", "prompt_sha256": "0" * 64}}, "spark_assist"),
]:
    bad = dict(good); bad.update(mutate)
    errs = validate_take(bad)
    assert errs, mutate
    assert any(want in e for e in errs), (mutate, errs)
print("TAKELOG-OK")
`;

test("take-log schema accepts good takes and rejects broken ones", () => {
  const out = execFileSync("python3", ["-"], { input: driver, encoding: "utf8" });
  assert.match(out, /TAKELOG-OK/);
});
