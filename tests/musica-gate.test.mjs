// Musica gate packet: HN-055. The builder must assemble a
// packet with the pack, the records, the catalogues, and test
// results in one folder.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const musica = join(root, "os/worlds/musica");
const staging = join(root, "..", "staging", "musica-gate-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("gate packet assembles pack, records, catalogues, tests", () => {
  py("gate_packet.py", [musica, "--out", staging,
    "--musica-tests", "musica-pack.test.mjs"]);
  assert.ok(existsSync(join(staging, "README.md")));
  const readme = readFileSync(join(staging, "README.md"), "utf8");
  assert.ok(readme.includes("gate-1"));
  assert.ok(existsSync(join(staging, "pack.json")));
  assert.ok(existsSync(join(staging, "PACK.md")));
  assert.ok(existsSync(join(staging, "test-results.txt")));
  const records = JSON.parse(readFileSync(join(staging, "records.json"), "utf8"));
  const hn029 = records.sessions.find((s) => s.session_id === "hn029-chipsynth");
  assert.ok(hn029, "hn029 missing from records");
  assert.equal(hn029.takes, 12);
  assert.equal(hn029.keepers, 11);
  assert.ok(existsSync(join(staging, "catalogues", "hn029-chipsynth-catalogue.json")));
});
