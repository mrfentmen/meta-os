// Round 12 — hosted loop coverage (R12-009, R12-010, R12-026).
//
// The registry is the contract: every entry either runs a real command or says draft and why.
// This suite checks the coverage record names every hosted entry, and that every hosted entry
// still refuses a STOP filed before it starts.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { hostedLoops, stopDrill } from "../agents/hosted.mjs";

const ROOT = path.resolve(import.meta.dirname, "..");
const agents = JSON.parse(fs.readFileSync(path.join(ROOT, "agents", "registry.json"), "utf8")).agents;
const hosted = hostedLoops(agents);

test("R12-009 the Cadence entry is the watchman one-pass command, not a placeholder", () => {
  const watch = agents.find((a) => a.name === "watch");
  assert.ok(watch, "watch entry exists");
  assert.equal(watch.draft, undefined, "not draft");
  assert.equal(watch.hosted, true);
  assert.deepEqual(watch.command, ["repo:node", "agents/watchman.mjs", "--once"]);
  assert.ok(fs.existsSync(path.join(ROOT, "agents", "watchman.mjs")));
});

test("R12-010 the coverage record names every hosted loop and both uncovered programs", () => {
  const md = fs.readFileSync(path.join(ROOT, "os-build", "layer1", "r12", "CHAOS_COVERAGE.md"), "utf8");
  for (const a of hosted) assert.ok(md.includes("`" + a.name + "`"), a.name + " is in the coverage record");
  assert.match(md, /Musica[\s\S]*NOT COVERED/);
  assert.match(md, /Officina[\s\S]*NOT COVERED/);
});

test("R12-023 every hosted loop refuses a STOP filed before it starts", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "r12-stop-"));
  for (const a of hosted) {
    const drill = stopDrill(a, { root: dir });
    assert.equal(drill.refused.ok, false, a.name);
    assert.equal(drill.refused.reason, "stop-filed", a.name);
    drill.cleared();
  }
});

test("R12-026 no hosted entry carries a draft flag; every draft entry says why", () => {
  for (const a of hosted) assert.equal(a.draft, undefined, a.name + " is hosted and must not be draft");
  const drafts = agents.filter((a) => a.draft === true);
  assert.ok(drafts.length > 0);
  for (const a of drafts) {
    assert.equal(a.hosted, false, a.name);
    assert.ok(a.draftReason && a.draftReason.length > 20, a.name + " has a reason");
  }
});
