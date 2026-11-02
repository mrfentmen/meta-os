// Holds the lane-3 records to the code they describe.
//
// Three checks, each read-only:
//   1. every syscall number the kernel actually dispatches is specced;
//   2. every file in os-build/logs/ is indexed, and every log the index
//      names exists;
//   3. the known disagreements (K7 "no log" vs the file, K5 no banner,
//      the empty MERGED-boot.txt) are stated, not quietly dropped.
//
// No child processes, no network: the sources are read as text.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), "utf8");

const ABI = read("os-build/USERSPACE_ABI.md");
const BEHAVIOUR = read("os-build/KERNEL_BEHAVIOUR.md");
const INDEX = read("os-build/BOOT_LOG_INDEX.md");
const USER_RS = read("kernel/src/user.rs");

// The syscall dispatch is a `match num { ... }` between the handler
// signature and `user_write`. Slice exactly that region so unrelated
// matches (ELF relocations, decode tables) cannot leak in.
function dispatchedNumbers(source) {
  const start = source.indexOf("pub fn syscall_handler");
  const end = source.indexOf("unsafe fn user_write");
  assert.ok(start !== -1 && end > start, "user.rs: syscall_handler/user_write markers missing");
  const body = source.slice(start, end);
  const numbers = new Set();
  for (const m of body.matchAll(/^\s*(\d+)\s*=>/gm)) numbers.add(Number(m[1]));
  return [...numbers].sort((a, b) => a - b);
}

test("every dispatched syscall number is specced in USERSPACE_ABI.md", () => {
  const numbers = dispatchedNumbers(USER_RS);
  assert.deepEqual(numbers, [0, 1, 2, 3, 4, 5], "user.rs dispatch changed shape");
  for (const n of numbers) {
    assert.ok(
      ABI.includes(`### ${n} `),
      `syscall ${n} is dispatched but has no "### ${n} " section in USERSPACE_ABI.md`,
    );
  }
});

test("the bad-syscall refusal and its sentinel are documented", () => {
  assert.match(USER_RS, /user bad syscall \{\} refused/, "refusal string vanished from user.rs");
  assert.ok(ABI.includes("user bad syscall {n} refused"), "refusal string not in the spec");
  assert.ok(ABI.includes("u64::MAX"), "the u64::MAX sentinel is not in the spec");
  assert.ok(ABI.includes("4096"), "the 4096-byte write cap is not in the spec");
  assert.ok(ABI.includes("Vector 128") || ABI.includes("vector 128"), "entry vector not named");
  assert.ok(ABI.includes("syscalls.rs"), "frozen syscalls.rs not called out");
  assert.match(ABI, /FROZEN/, "syscalls.rs is not marked FROZEN");
});

test("USERSPACE_ABI.md cites the code by file and line", () => {
  const refs = [...ABI.matchAll(/kernel\/src\/[a-z]+\.rs:\d+/g)];
  assert.ok(refs.length >= 8, `expected real file:line references, found ${refs.length}`);
  assert.ok(ABI.includes("kernel/src/user.rs:90"), "the match at user.rs:90 is not named");
});

test("KERNEL_BEHAVIOUR.md records all three areas with file:line refs", () => {
  for (const section of ["Allocator", "Task lifecycle", "Fault path"]) {
    assert.match(
      BEHAVIOUR,
      new RegExp(`^## \\d+\\. ${section}$`, "m"),
      `missing behaviour section: ${section}`,
    );
  }
  assert.ok(BEHAVIOUR.includes("kernel/src/mem.rs:"), "allocator record has no mem.rs ref");
  assert.ok(BEHAVIOUR.includes("kernel/src/tasks.rs:"), "task record has no tasks.rs ref");
  assert.ok(BEHAVIOUR.includes("kernel/src/interrupts.rs:"), "fault record has no interrupts.rs ref");
  // The cooperative-scheduler limitation must be stated, not implied.
  assert.match(BEHAVIOUR, /No preemption runs today/, "preemption limitation is not stated");
});

test("every file in os-build/logs is in the index", () => {
  const dir = path.join(ROOT, "os-build", "logs");
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  assert.ok(entries.length > 30, "logs directory unexpectedly small");
  for (const entry of entries) {
    assert.ok(
      INDEX.includes(entry.name),
      `os-build/logs/${entry.name} is not listed in BOOT_LOG_INDEX.md`,
    );
  }
});

test("every log path the index names exists, and no stale names", () => {
  // The index is a table whose first column is the bare file name;
  // parse that column so a renamed entry cannot hide in prose.
  const named = new Set(
    [...INDEX.matchAll(/^\|\s*`([^`]+)`/gm)].map((m) => m[1]),
  );
  assert.ok(named.size >= 30, `index names only ${named.size} log paths`);
  for (const name of named) {
    assert.ok(
      fs.existsSync(path.join(ROOT, "os-build", "logs", name)),
      `BOOT_LOG_INDEX.md names os-build/logs/${name}, which does not exist`,
    );
  }
});

test("the index keeps the known disagreements visible", () => {
  // K7: a file exists, but no K7 banner does. gates.md says "NO LOG".
  assert.ok(INDEX.includes("K7-boot.txt"), "the existing K7 session log is not indexed");
  assert.match(INDEX, /no K7 milestone banner/i, "the missing K7 banner is not stated");
  assert.match(INDEX, /gates\.md:20/, "the gates.md conflict is not cited");
  // K5: tick output, no banner.
  assert.match(INDEX, /No K5 banner exists/i, "the K5 banner limitation is not stated");
  // The empty file must be called empty, not counted as evidence.
  assert.match(INDEX, /MERGED-boot\.txt/);
  assert.match(INDEX, /EMPTY FILE/, "MERGED-boot.txt is not flagged as empty");
  // Screenshots must not be presented as log lines.
  assert.match(INDEX, /Screenshots \(not logs\)/, "screenshot/log split missing");
});
