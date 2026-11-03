// Tests for agents/jobs.mjs — real files, real ledger lines, no mocks.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import url from "node:url";

import { board } from "../agents/jobs.mjs";

const REPO = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));

function root() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "meta-board-"));
  fs.mkdirSync(path.join(dir, "jobs"));
  return dir;
}

function put(dir, name, value) {
  const file = path.join(dir, "jobs", name);
  fs.writeFileSync(file, typeof value === "string" ? value : JSON.stringify(value));
}

function ledger(dir, lines) {
  fs.writeFileSync(
    path.join(dir, "watchman.jsonl"),
    lines.map((line) => JSON.stringify(line)).join("\n") + "\n"
  );
}

test("an untouched job is queued", () => {
  const dir = root();
  put(dir, "q.job.json", { id: "q", agent: "aegis" });
  const view = board({ root: dir });
  assert.equal(view.rows[0].state, "queued");
  assert.equal(view.counts.queued, 1);
});

test("a bell with no result is running", () => {
  const dir = root();
  put(dir, "r.job.json", { id: "r", agent: "aegis" });
  ledger(dir, [{ event: "bell", id: "r", run: "run-1" }]);
  assert.equal(board({ root: dir }).rows[0].state, "running");
});

test("a clean result is done and a nonzero one is failed", () => {
  const dir = root();
  put(dir, "d.job.json", { id: "d", agent: "aegis" });
  put(dir, "d.result.json", { id: "d", code: 0, signal: null });
  put(dir, "f.job.json", { id: "f", agent: "aegis" });
  put(dir, "f.result.json", { id: "f", code: 3, signal: null });
  put(dir, "s.job.json", { id: "s", agent: "aegis" });
  put(dir, "s.result.json", { id: "s", code: null, signal: "SIGTERM" });
  const states = Object.fromEntries(board({ root: dir }).rows.map((r) => [r.id, r.state]));
  assert.deepEqual(states, { d: "done", f: "failed", s: "failed" });
});

test("a refused spawn is refused, with the reason from the result", () => {
  const dir = root();
  put(dir, "x.job.json", { id: "x", agent: "imperium-patrol" });
  put(dir, "x.result.json", { id: "x", refused: "draft-agent" });
  const row = board({ root: dir }).rows[0];
  assert.equal(row.state, "refused");
  assert.equal(row.reason, "draft-agent");
});

test("a bell with no result but a refusal line is refused, not running", () => {
  const dir = root();
  put(dir, "y.job.json", { id: "y", agent: "aegis" });
  ledger(dir, [{ event: "job-refused", id: "y", reason: "memory-cap" }]);
  const row = board({ root: dir }).rows[0];
  assert.equal(row.state, "refused");
  assert.equal(row.reason, "memory-cap");
});

test("a broken job file is shown as unreadable, not skipped", () => {
  const dir = root();
  put(dir, "bad.job.json", "{not json");
  const view = board({ root: dir });
  assert.equal(view.rows.length, 1);
  assert.equal(view.rows[0].state, "unreadable");
  assert.equal(view.counts.unreadable, 1);
});

test("a torn ledger line does not hide the rest of the board", () => {
  const dir = root();
  put(dir, "t.job.json", { id: "t", agent: "aegis" });
  fs.writeFileSync(path.join(dir, "watchman.jsonl"), '{"event":"bell","id":"t"}\n{"event":"bo');
  assert.equal(board({ root: dir }).rows[0].state, "running");
});

test("an empty board is a report, not a crash", () => {
  const view = board({ root: root() });
  assert.deepEqual(view.rows, []);
  assert.equal(view.counts.queued, 0);
});

test("the CLI prints the board and exits 0", () => {
  const dir = root();
  put(dir, "c.job.json", { id: "c", agent: "aegis" });
  const run = spawnSync(process.execPath, [path.join(REPO, "agents", "jobs.mjs"), "--root", dir], {
    encoding: "utf8",
  });
  assert.equal(run.status, 0, run.stderr);
  assert.match(run.stdout, /c\s+queued/);
  assert.match(run.stdout, /1 job\(s\)/);

  const json = spawnSync(
    process.execPath,
    [path.join(REPO, "agents", "jobs.mjs"), "--root", dir, "--json"],
    { encoding: "utf8" }
  );
  assert.equal(JSON.parse(json.stdout).rows[0].state, "queued");
});

test("the CLI refuses a directory with no board", () => {
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), "meta-noboard-"));
  const run = spawnSync(process.execPath, [path.join(REPO, "agents", "jobs.mjs"), "--root", empty], {
    encoding: "utf8",
  });
  assert.equal(run.status, 2);
  assert.match(run.stderr, /no board/);
});
