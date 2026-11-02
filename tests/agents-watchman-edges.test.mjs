import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pollWatch } from "../agents/runtime.mjs";

function fixture() {
  const dir = mkdtempSync(join(tmpdir(), "agents-watch-"));
  const file = join(dir, "watched.txt");
  writeFileSync(file, "one");
  return { dir, target: { type: "file", path: file } };
}

test("a content change produces exactly one change note", () => {
  const { dir, target } = fixture();
  try {
    const first = pollWatch([target], {});
    assert.equal(first.changes.length, 0, "first poll only records state");
    writeFileSync(target.path, "one plus more bytes");
    const second = pollWatch([target], first.state);
    assert.equal(second.changes.length, 1);
    assert.equal(second.changes[0].key, "file:" + target.path);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("three polls with no change stay silent", () => {
  const { dir, target } = fixture();
  try {
    let prev = pollWatch([target], {}).state;
    for (let i = 0; i < 3; i++) {
      const poll = pollWatch([target], prev);
      assert.deepEqual(poll.changes, [], `poll ${i + 1}`);
      prev = poll.state;
    }
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
