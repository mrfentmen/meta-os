import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync, appendFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Ledger, loadRegistry, validateEntry } from "../agents/runtime.mjs";

function tmp() {
  return mkdtempSync(join(tmpdir(), "agents-runtime-"));
}

test("an agent with an empty command array is refused at load", () => {
  const dir = tmp();
  try {
    const file = join(dir, "registry.json");
    writeFileSync(file, JSON.stringify({ agents: [{ name: "x", command: [], budget: {} }] }));
    assert.throws(() => loadRegistry(file), /missing command/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a placeholder command is accepted; only the registry's draft flag marks it", () => {
  const agents = loadRegistry(new URL("../agents/registry.json", import.meta.url).pathname);
  const rowan = agents.find((a) => a.name === "rowan");
  assert.ok(rowan, "rowan is in the real registry");
  assert.deepEqual(rowan.command, ["true"]);
  assert.equal(rowan.draft, true, "the registry itself reports the draft");
  assert.equal(validateEntry(rowan), true, "the runtime has no draft detector of its own");
});

test("duplicate agent names are refused", () => {
  const dir = tmp();
  try {
    const file = join(dir, "registry.json");
    writeFileSync(
      file,
      JSON.stringify({
        agents: [
          { name: "a", command: ["true"], budget: {} },
          { name: "a", command: ["true"], budget: {} },
        ],
      }),
    );
    assert.throws(() => loadRegistry(file), /duplicate agent a/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the ledger refuses a record with no run id", () => {
  const dir = tmp();
  try {
    const ledger = new Ledger(join(dir, "ledger.jsonl"));
    assert.throws(() => ledger.add("", "spawn"), /missing required field run/);
    assert.throws(() => ledger.add("r", ""), /missing required field event/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a torn final line is skipped and the next record stays whole", () => {
  const dir = tmp();
  try {
    const file = join(dir, "ledger.jsonl");
    const ledger = new Ledger(file);
    ledger.add("run-1", "spawn");
    appendFileSync(file, '{"ts":"torn"');
    ledger.add("run-1", "exit");
    const events = ledger.read().map((entry) => entry.event);
    assert.deepEqual(events, ["spawn", "exit"]);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
