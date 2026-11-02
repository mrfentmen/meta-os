import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { lessons, teach } from "../agents/lessons.mjs";

function root() {
  return mkdtempSync(join(tmpdir(), "agents-lessons-"));
}

test("one teach writes one JSONL line with agent, text, and timestamp", () => {
  const dir = root();
  try {
    teach(dir, "milo", "check the gate log first");
    const lines = readFileSync(join(dir, "lessons.jsonl"), "utf8").trim().split("\n");
    assert.equal(lines.length, 1);
    const record = JSON.parse(lines[0]);
    assert.equal(record.agent, "milo");
    assert.equal(record.text, "check the gate log first");
    assert.equal(typeof record.ts, "string");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("lessons read back in append order and every agent sees them", () => {
  const dir = root();
  try {
    teach(dir, "milo", "first");
    teach(dir, "bond", "second");
    const all = lessons(dir).map((entry) => entry.text);
    assert.deepEqual(all, ["first", "second"]);
    // The second agent's read is the same shared file: the level-up property.
    assert.deepEqual(lessons(dir).map((entry) => entry.agent), ["milo", "bond"]);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the limit keeps the newest lessons", () => {
  const dir = root();
  try {
    for (const text of ["a", "b", "c"]) teach(dir, "milo", text);
    assert.deepEqual(lessons(dir, 2).map((entry) => entry.text), ["b", "c"]);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
