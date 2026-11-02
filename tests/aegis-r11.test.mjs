// Round 11 finish — Aegis: confusables (233), lifecycle (236), alarm split (238), unreadable
// manifests (283). No network: the sweep parts here are the local planner and a stub client.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { scanName, scanNames } from "../aegis/confusables.mjs";
import { openFinding, acknowledgeFinding, closeFinding, chainOf } from "../aegis/lifecycle.mjs";
import { classify, render, QUIET, ALARM } from "../aegis/alarm.mjs";
import { buildPlan } from "../aegis/sweep.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "aegis-r11-"));

test("R11-233 a Cyrillic lookalike in a Latin name is a finding, with its code point", () => {
  const r = scanName("p\u0430ypal");   // Cyrillic a
  assert.equal(r.hits.length, 1);
  assert.equal(r.hits[0].index, 1);
  assert.equal(r.hits[0].codePoint, "U+0430");
  assert.equal(r.hits[0].looksLike, "a");
  assert.equal(r.mixedScript, true);
});

test("R11-233 a name wholly in another script is not a spoof, and invisible marks are findings", () => {
  assert.equal(scanName("\u0449\u0438\u0442").hits.length, 0);   // no Latin lookalike
  const zw = scanName("osv\u200b-mcp");
  assert.equal(zw.hits[0].invisible, true);
  const batch = scanNames([{ name: "osv", kind: "gateway" }, { name: "cisakev", kind: "tray" }]);
  assert.equal(batch.scanned, 2);
  assert.equal(batch.findings.length, 0);
});

test("R11-236 the chain is open, acknowledge, close — and illegal steps are refused and recorded", () => {
  const file = path.join(tmp(), "findings-lifecycle.jsonl");
  assert.equal(openFinding(file, { id: "f1", title: "one", severity: "low" }).ok, true);
  assert.equal(acknowledgeFinding(file, "f1", { by: "milo" }).ok, true);
  assert.equal(closeFinding(file, "f1", { by: "milo", note: "fixed" }).ok, true);
  const chain = chainOf(file, "f1");
  assert.equal(chain.state, "closed");
  assert.deepEqual(chain.events.map((e) => e.event), ["open", "acknowledge", "close"]);

  assert.equal(openFinding(file, { id: "f2", title: "two" }).ok, true);
  const early = closeFinding(file, "f2", { by: "milo" });
  assert.equal(early.ok, false);
  assert.equal(early.reason, "needs-acknowledged");
  assert.equal(chainOf(file, "f2").state, "open", "a refusal cannot move the state");
  assert.equal(acknowledgeFinding(file, "ghost").reason, "unknown-finding");
  const refused = chainOf(file, "f2").events.filter((e) => e.event === "refused");
  assert.equal(refused.length, 1);
});

test("R11-238 a low finding is a quiet note; a medium-or-above finding is the full alarm", () => {
  const small = classify([{ severity: "low" }, { severity: "info" }]);
  assert.equal(small.mode, QUIET);
  assert.match(render(small), /^Aegis note:/);
  const big = classify([{ severity: "high" }]);
  assert.equal(big.mode, ALARM);
  assert.match(render(big), /^Aegis alarm:/);
  assert.equal(classify([{ severity: "medium" }]).mode, ALARM);
  assert.equal(classify([]).mode, QUIET, "an empty run is a note, not an alarm");
});

test("R11-283 one unreadable manifest is named and skipped; the rest of the plan still builds", () => {
  const root = tmp();
  fs.writeFileSync(path.join(root, "package.json"), "{ not json");
  fs.mkdirSync(path.join(root, "ok"));
  fs.writeFileSync(path.join(root, "ok", "package.json"), JSON.stringify({ dependencies: { left: "^1.0.0", right: "^2.0.0" } }));
  const plan = buildPlan(root);
  assert.equal(plan.unreadable.length, 1);
  assert.equal(plan.unreadable[0].manifest, "package.json");
  assert.equal(plan.unversioned.length, 1);
  assert.equal(plan.unversioned[0].manifest, "ok/package.json");
  assert.equal(plan.unversioned[0].count, 2);
});
