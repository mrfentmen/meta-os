// Musica listening harness: HN-039. The A/B page must be blind
// (no take ids in labels or file paths) and the pick must land in
// the take log as a human verdict on the winner.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, rmSync} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-harness-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("blind A/B page hides identities and records the pick", () => {
  rmSync(staging, { recursive: true, force: true });
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "3", "--seed-base", "9400"]);
  py("keepers.py", [staging]);
  py("catalogue.py", [staging]);
  const log0 = readFileSync(join(staging, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  const keepers = log0.filter((t) => t.verdict === "keeper");
  assert.ok(keepers.length >= 2);
  const pairDir = join(staging, "ab", "pair-001");
  py("harness.py", ["make-pair", staging,
    "--takes", keepers[0].take_id, keepers[1].take_id,
    "--seed", "42", "--out", pairDir]);
  const page = readFileSync(join(pairDir, "ab.html"), "utf8");
  assert.ok(!page.includes(keepers[0].take_id), "page leaks take id");
  assert.ok(!page.includes(keepers[1].take_id), "page leaks take id");
  assert.ok(page.includes('<audio controls src="A.wav">'));
  assert.ok(page.includes('<audio controls src="B.wav">'));
  const sidecar = JSON.parse(readFileSync(join(pairDir, "ab.json"), "utf8"));
  py("harness.py", ["record-pick", pairDir, "--pick", "A"]);
  const log1 = readFileSync(join(staging, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  const winner = log1.find((t) => t.take_id === sidecar.a_take);
  assert.ok(winner.human_verdict, "winner has no human verdict");
  assert.equal(winner.human_verdict.pick, sidecar.a_take);
  assert.equal(winner.human_verdict.pair_id, "pair-001");
  // The log must still validate after the verdict lands.
  execFileSync("python3", ["-"], {
    input: `import sys; sys.path.insert(0, ${JSON.stringify(runtime)}); `
      + `from take_log import read_log; `
      + `read_log(${JSON.stringify(join(staging, "take_log.jsonl"))}); `
      + `print("LOG-VALID")`,
    encoding: "utf8",
  });
});
