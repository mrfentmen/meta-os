// Musica silence audit: HN-052. A clean catalogue must audit
// clean; a silenced track and a duplicated file must be caught
// by name and issue type.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, copyFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-audit-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

function audit(session) {
  return spawnSync("python3", [join(runtime, "audit.py"), session],
    { encoding: "utf8" });
}

test("audit passes a clean catalogue and catches silence + duplicates", () => {
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "3", "--seed-base", "22000"]);
  py("keepers.py", [staging]);
  py("catalogue.py", [staging]);
  const clean = audit(staging);
  assert.equal(clean.status, 0, clean.stdout + clean.stderr);
  assert.match(clean.stdout, /issues=0/);
  const catalogue = JSON.parse(readFileSync(join(staging, "catalogue.json"), "utf8"));
  assert.ok(catalogue.tracks.length >= 2);
  const first = catalogue.tracks[0];
  const second = catalogue.tracks[1];
  // Step 1: silence the first track's audio -> "silent" issue.
  const wav = readFileSync(join(staging, first.file));
  const silent = Buffer.from(wav);
  silent.fill(0, 44);
  writeFileSync(join(staging, first.file), silent);
  const silenced = audit(staging);
  assert.equal(silenced.status, 1);
  let auditJson = JSON.parse(readFileSync(join(staging, "audit.json"), "utf8"));
  assert.ok(auditJson.issues.some((i) => i.take_id === first.take_id && i.issue === "silent"));
  // Step 2: copy the second track's file over the first's -> the
  // first track now mismatches its catalogue hash and duplicates
  // the second track's hash.
  copyFileSync(join(staging, second.file), join(staging, first.file));
  const dirty = audit(staging);
  assert.equal(dirty.status, 1);
  auditJson = JSON.parse(readFileSync(join(staging, "audit.json"), "utf8"));
  const kinds = new Set(auditJson.issues.map((i) => i.issue));
  assert.ok(kinds.has("duplicate hash"));
  assert.ok(kinds.has("hash mismatch"));
});
