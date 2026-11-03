// Tests for agents/submit.mjs — real files, real registry, no mocks.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import url from "node:url";

import { SubmitError, submitJob } from "../agents/submit.mjs";

const REPO = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));
const REGISTRY = JSON.parse(fs.readFileSync(path.join(REPO, "agents", "registry.json"), "utf8")).agents;

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "meta-submit-"));
}

function refuses(code, fn) {
  assert.throws(fn, (error) => error instanceof SubmitError && error.code === code);
}

test("a job for a live agent lands as one readable file", () => {
  const root = tmp();
  const result = submitJob({
    root, registry: REGISTRY, agent: "aegis", orders: "sweep the tree", id: "j1",
  });
  const job = JSON.parse(fs.readFileSync(result.path, "utf8"));
  assert.equal(job.id, "j1");
  assert.equal(job.agent, "aegis");
  assert.equal(job.orders, "sweep the tree");
  const entry = REGISTRY.find((candidate) => candidate.name === "aegis");
  assert.equal(job.lane, entry.lane, "the lane is copied from the registry, not invented");
  assert.deepEqual(fs.readdirSync(path.join(root, "jobs")), ["j1.job.json"]);
});

test("a draft agent is refused and no file is written", () => {
  const root = tmp();
  refuses("submit-draft", () =>
    submitJob({ root, registry: REGISTRY, agent: "imperium-patrol", orders: "patrol", id: "j2" })
  );
  assert.equal(fs.existsSync(path.join(root, "jobs", "j2.job.json")), false);
});

test("an unknown agent is refused", () => {
  refuses("submit-agent", () =>
    submitJob({ root: tmp(), registry: REGISTRY, agent: "nobody", orders: "x", id: "j3" })
  );
});

test("empty orders are refused", () => {
  refuses("submit-orders", () =>
    submitJob({ root: tmp(), registry: REGISTRY, agent: "aegis", orders: "   ", id: "j4" })
  );
});

test("an unsafe id is refused", () => {
  refuses("submit-id", () =>
    submitJob({ root: tmp(), registry: REGISTRY, agent: "aegis", orders: "x", id: "../escape" })
  );
  refuses("submit-id", () =>
    submitJob({ root: tmp(), registry: REGISTRY, agent: "aegis", orders: "x", id: "has space" })
  );
});

test("a duplicate id does not overwrite the job already on the board", () => {
  const root = tmp();
  submitJob({ root, registry: REGISTRY, agent: "aegis", orders: "first", id: "dup" });
  refuses("submit-duplicate", () =>
    submitJob({ root, registry: REGISTRY, agent: "aegis", orders: "second", id: "dup" })
  );
  const job = JSON.parse(fs.readFileSync(path.join(root, "jobs", "dup.job.json"), "utf8"));
  assert.equal(job.orders, "first");
});

test("maxContinues is written only when it is a real bound", () => {
  const root = tmp();
  const result = submitJob({
    root, registry: REGISTRY, agent: "aegis", orders: "x", id: "c1", maxContinues: 2,
  });
  assert.equal(result.job.maxContinues, 2);
  const plain = submitJob({ root, registry: REGISTRY, agent: "aegis", orders: "x", id: "c2" });
  assert.equal(plain.job.maxContinues, undefined);
});

test("the CLI exits 0 on a good job and 1 on a draft", () => {
  const root = tmp();
  const good = spawnSync(process.execPath, [
    path.join(REPO, "agents", "submit.mjs"),
    "--root", root, "--agent", "aegis", "--orders", "sweep", "--id", "cli1",
  ], { encoding: "utf8" });
  assert.equal(good.status, 0, good.stderr);
  assert.equal(JSON.parse(good.stdout).id, "cli1");

  const draft = spawnSync(process.execPath, [
    path.join(REPO, "agents", "submit.mjs"),
    "--root", root, "--agent", "imperium-patrol", "--orders", "patrol", "--id", "cli2",
  ], { encoding: "utf8" });
  assert.equal(draft.status, 1);
  assert.match(draft.stderr, /draft/);
  assert.equal(fs.existsSync(path.join(root, "jobs", "cli2.job.json")), false);
});

test("the CLI refuses missing arguments with a usage error", () => {
  const result = spawnSync(process.execPath, [path.join(REPO, "agents", "submit.mjs")], {
    encoding: "utf8",
  });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /usage/);
});
