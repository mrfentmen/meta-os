// Musica overnight run: HN-040. The pipeline job must run end
// to end on a small session and report honest counts.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync, rmSync} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-overnight-test");

test("overnight pipeline runs and reports honest counts", () => {
  rmSync(staging, { recursive: true, force: true });
  const out = execFileSync("python3", [join(runtime, "overnight.py"),
    "--session-dir", staging, "--brief-id", "chipsynth",
    "--brief-file", join(root, "os/worlds/musica/briefs/chipsynth.md"),
    "--takes", "5", "--seed-base", "11000"], { encoding: "utf8" });
  assert.match(out, /overnight takes=5/);
  const report = JSON.parse(readFileSync(join(staging, "overnight-report.json"), "utf8"));
  assert.equal(report.takes, 5);
  assert.equal(report.keepers + report.rejects, 5);
  assert.equal(report.catalogue_delta, report.keepers);
  assert.equal(report.rights_violations, 0);
  assert.ok(report.reject_rate >= 0 && report.reject_rate <= 1);
  assert.ok(existsSync(join(staging, "catalogue.json")));
  assert.ok(existsSync(join(staging, "board.html")));
});
