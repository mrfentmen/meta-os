// Round 11 finish — the two documentation deliverables that can be checked mechanically:
// one worked example per ABI call (278) and an index that names every committed boot log (282).
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");

test("R11-278 the ABI has a worked example for each allocated call, and says they were not executed", () => {
  const abi = fs.readFileSync(path.join(ROOT, "os-build", "USERSPACE_ABI.md"), "utf8");
  assert.ok(abi.includes("## Worked examples"));
  assert.match(abi, /They were not executed in this round/);
  for (const call of ["exit", "write", "sleep", "pid", "yield", "read_key"]) {
    assert.match(abi, new RegExp("\\*\\*`" + call + "\\("), call + " has an example");
  }
  assert.ok(abi.includes("`u64::MAX`"), "the refusal value is in the examples");
});

test("R11-282 the boot-log index names every committed log and claims no verdict it did not check", () => {
  const index = fs.readFileSync(path.join(ROOT, "os-build", "layer1", "BOOTLOG_INDEX.md"), "utf8");
  const logs = fs.readdirSync(path.join(ROOT, "os-build", "logs")).filter((f) => f.endsWith(".txt"));
  assert.ok(logs.length > 10);
  for (const f of logs) assert.ok(index.includes("`" + f + "`"), f + " is in the index");
  assert.match(index, /The index does NOT decide that a/);
  assert.match(index, /A missing log is not a failed boot/);
});
