// CB-396..397: the two safe-write promises that are not about disk-full.
//   * writing the same bytes again is a no-change path, not a write;
//   * a path outside the allowed root is refused before the file is opened.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { writeIfChanged, writeWithinRoot } from "../agents/safe-write.mjs";

function tempRoot() {
  return mkdtempSync(join(tmpdir(), "agents-safewrite-"));
}

test("same content twice takes the no-change path and leaves mtime alone", () => {
  const dir = tempRoot();
  try {
    const file = join(dir, "record.json");
    const first = writeIfChanged(file, '{"a":1}\n');
    assert.deepEqual(first, { changed: true, bytes: 8 });
    const before = statSync(file).mtimeMs;

    const second = writeIfChanged(file, '{"a":1}\n');
    assert.deepEqual(second, { changed: false, bytes: 8 });
    assert.equal(statSync(file).mtimeMs, before, "mtime must not move");
    assert.equal(readFileSync(file, "utf8"), '{"a":1}\n');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("changed content writes and reports changed", () => {
  const dir = tempRoot();
  try {
    const file = join(dir, "record.json");
    writeIfChanged(file, "one\n");
    assert.deepEqual(writeIfChanged(file, "two\n"), { changed: true, bytes: 4 });
    assert.equal(readFileSync(file, "utf8"), "two\n");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a missing file is written on the first call", () => {
  const dir = tempRoot();
  try {
    const file = join(dir, "nested", "first.txt");
    assert.deepEqual(writeIfChanged(file, "hello"), { changed: true, bytes: 5 });
    assert.equal(readFileSync(file, "utf8"), "hello");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a path inside the allowed root is written", () => {
  const dir = tempRoot();
  try {
    const target = join(dir, "sub", "ok.txt");
    writeWithinRoot(dir, target, "inside");
    assert.equal(readFileSync(target, "utf8"), "inside");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a ../ escape is refused and nothing is created", () => {
  const dir = tempRoot();
  const outside = join(dir, "..", "escape-" + process.pid + ".txt");
  try {
    assert.throws(
      () => writeWithinRoot(dir, outside, "nope"),
      /write refused: .* is outside /
    );
    assert.throws(() => readFileSync(outside, "utf8"), /ENOENT/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
    try { rmSync(outside, { force: true }); } catch { /* never created */ }
  }
});

test("a sibling directory sharing the root's name is not inside it", () => {
  const dir = tempRoot();
  const sibling = dir + "-evil";
  try {
    assert.throws(
      () => writeWithinRoot(dir, join(sibling, "x.txt"), "nope"),
      /write refused:/
    );
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the root itself is not a file target", () => {
  const dir = tempRoot();
  try {
    assert.throws(() => writeWithinRoot(dir, dir, "nope"), /write refused:/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("an absolute path outside the root is refused", () => {
  const dir = tempRoot();
  try {
    assert.throws(
      () => writeWithinRoot(dir, "/etc/definitely-not-ours.txt", "nope"),
      /write refused:/
    );
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a symlink-style relative alias that resolves inside is allowed", () => {
  const dir = tempRoot();
  try {
    const target = join(dir, "a", "..", "b.txt");
    writeWithinRoot(dir, target, "still inside");
    assert.equal(readFileSync(join(dir, "b.txt"), "utf8"), "still inside");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("an existing file outside the root is not overwritten", () => {
  const dir = tempRoot();
  const outside = join(dir, "..", "keep-" + process.pid + ".txt");
  try {
    writeFileSync(outside, "original");
    assert.throws(() => writeWithinRoot(dir, outside, "clobbered"), /write refused:/);
    assert.equal(readFileSync(outside, "utf8"), "original");
  } finally {
    rmSync(dir, { recursive: true, force: true });
    try { rmSync(outside, { force: true }); } catch { /* nothing left */ }
  }
});
