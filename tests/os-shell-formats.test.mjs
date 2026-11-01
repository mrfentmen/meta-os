// Node built-in test runner, no dependencies:  node --test tests/os-shell-formats.test.mjs
// Covers the OS shell formats (H2): the machine-readable formats
// file parses, the banner is exactly four templated lines, the
// agent record fields are exactly the specified set, and the
// formats doc agrees with the data file on the exact strings
// (banner line 1, help empty line, prompt). Spec-only checks:
// nothing here claims any of these strings are emitted by a
// running kernel — emission is NOT BUILT until a QEMU boot log
// shows it.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const formats = JSON.parse(
  readFileSync(new URL("../os-build/shell-formats.json", import.meta.url), "utf8"),
);
const doc = readFileSync(
  new URL("../os-build/shell-formats.md", import.meta.url),
  "utf8",
);

test("banner is exactly four templated lines in order", () => {
  assert.equal(formats.banner_lines.length, 4);
  assert.equal(formats.banner_lines[0], "META OS");
  assert.equal(formats.banner_lines[1], "milestone K<n>");
  assert.equal(formats.banner_lines[2], "memory <total_kib> KiB");
  assert.equal(formats.banner_lines[3], "tasks <count>");
});

test("agent record fields are exactly the specified set", () => {
  const names = formats.agent_record_fields.map((f) => f.name);
  assert.deepEqual(names, [
    "record",
    "os",
    "milestone",
    "kernel_version",
    "memory_kib",
    "tasks",
    "ticks",
    "heap_used_kib",
    "heap_total_kib",
    "status",
  ]);
  const byName = Object.fromEntries(
    formats.agent_record_fields.map((f) => [f.name, f]),
  );
  assert.equal(byName.os.values[0], "Meta OS");
  assert.deepEqual(byName.status.values, ["alive", "panic"]);
  assert.equal(byName.memory_kib.measurable_from, "K2");
  assert.equal(byName.tasks.measurable_from, "K5");
  assert.equal(byName.ticks.measurable_from, "K3");
  assert.equal(byName.heap_used_kib.measurable_from, "K4");
});

test("doc agrees with data on the exact strings", () => {
  assert.ok(doc.includes("META OS"));
  assert.ok(doc.includes(formats.help_empty));
  assert.ok(doc.includes("commands: (none yet)"));
  assert.equal(formats.help_empty, "commands: (none yet)");
  assert.equal(formats.prompt, "metaos> ");
  assert.ok(doc.includes("metaos> "));
});

test("limits and bad-input strings are exact", () => {
  assert.equal(formats.limits.max_line_chars, 256);
  assert.equal(formats.limits.max_echo_token_chars, 64);
  assert.equal(formats.bad_input.long_line, "line too long, ignored");
  assert.equal(formats.bad_input.unknown_command, "unknown command: <first-token>");
  assert.deepEqual(formats.status_lines, [
    "tasks <count>",
    "ticks <count>",
    "heap <used_kib>/<total_kib> KiB",
  ]);
});
