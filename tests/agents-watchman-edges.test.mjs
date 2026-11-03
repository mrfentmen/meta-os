import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { LARGE_CHANGE_BYTES, pollWatch } from "../agents/runtime.mjs";

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

test("CB2-382 a change at the documented threshold takes the full alarm form", () => {
  const { dir, target } = fixture();
  try {
    // The fixture file starts at 3 bytes, so the new size must be the
    // threshold plus those 3 to land exactly ON the boundary.
    const prev = pollWatch([target], {}).state;
    writeFileSync(target.path, "x".repeat(LARGE_CHANGE_BYTES + "one".length));
    const poll = pollWatch([target], prev);
    assert.equal(poll.changes.length, 1);
    assert.equal(poll.changes[0].kind, "alarm", "a large change is not a quiet note");
    assert.ok(poll.changes[0].deltaBytes >= LARGE_CHANGE_BYTES);
    assert.equal(poll.changes[0].reason, null, "a resized file is not a create or a delete");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("CB2-382b a small change stays a quiet note", () => {
  const { dir, target } = fixture();
  try {
    let prev = pollWatch([target], {}).state;
    writeFileSync(target.path, "one plus a few bytes");
    const poll = pollWatch([target], prev);
    assert.equal(poll.changes.length, 1);
    assert.equal(poll.changes[0].kind, "note");
    assert.ok(poll.changes[0].deltaBytes < LARGE_CHANGE_BYTES);
    prev = poll.state;
    writeFileSync(target.path, "two");
    assert.equal(pollWatch([target], prev).changes[0].kind, "note");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("CB2-382c a deleted file is an alarm whatever its size", () => {
  const { dir, target } = fixture();
  try {
    const prev = pollWatch([target], {}).state;
    rmSync(target.path);
    const poll = pollWatch([target], prev);
    assert.equal(poll.changes.length, 1);
    assert.equal(poll.changes[0].kind, "alarm");
    assert.equal(poll.changes[0].reason, "deleted");
    assert.equal(poll.changes[0].deltaBytes, null, "a delete has no byte delta to report");
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
