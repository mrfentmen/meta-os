// CB2-378..379: the cost governor.
//
// A job whose estimated cost is over the agent's cap is stopped before its first
// step: no command is resolved, no process exists, and the ledger carries the cap
// it broke. A job at the cap is allowed. A missing estimate is not zero -- it is
// passed to the wall-clock budget and marked unchecked on the gate result.
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { loadRegistry, preflightBudget, spawnAgent } from "../agents/runtime.mjs";

const NOOP = [process.execPath, "-e", "process.exit(0)"];

function root() {
  return mkdtempSync(join(tmpdir(), "agents-budget-"));
}

function agent(overrides = {}) {
  return {
    name: "spender",
    lane: "test",
    command: NOOP,
    budget: {},
    ...overrides,
  };
}

test("over-cap job is refused before any process exists", async () => {
  const dir = root();
  try {
    const handle = spawnAgent(agent({ budget: { maxCostUsd: 0.5 } }), {
      root: dir,
      job: { estimatedCostUsd: 0.75 },
    });
    const result = await handle.done;

    assert.equal(handle.child, null, "nothing was spawned");
    assert.equal(handle.stopped, "budget-cost-cap");
    assert.deepEqual(result, { code: null, signal: null, refused: true });
    assert.equal(existsSync(join(handle.runDir, "output.log")), false);
    assert.equal(handle._stopPoll, undefined, "no poll was armed");
    assert.equal(handle._budgetTimer, undefined, "no wall-clock timer was armed");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the stop reason is on the run ledger and in the receipt", async () => {
  const dir = root();
  try {
    const handle = spawnAgent(agent({ budget: { maxCostUsd: 0.5 } }), {
      root: dir,
      job: { estimatedCostUsd: 0.75 },
    });
    await handle.done;

    const events = handle.ledger.read();
    const receipt = events.find((e) => e.event === "budget-receipt");
    assert.ok(receipt, "a budget-receipt is written before the refusal");
    assert.equal(receipt.reason, "budget-cost-cap");
    assert.equal(receipt.estimateUsd, 0.75);
    assert.equal(receipt.capUsd, 0.5);
    assert.ok(
      events.some((e) => e.event === "refused" && e.reason === "budget-cost-cap"),
      "the ledger names why the run never started"
    );

    const onDisk = JSON.parse(readFileSync(join(handle.runDir, "receipt.json"), "utf8"));
    assert.equal(onDisk.reason, "budget-cost-cap");
    assert.equal(onDisk.run, handle.runId);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a job exactly at the cap runs", async () => {
  const dir = root();
  try {
    const handle = spawnAgent(agent({ budget: { maxCostUsd: 0.5 } }), {
      root: dir,
      job: { estimatedCostUsd: 0.5 },
    });
    assert.notEqual(handle.child, null);
    const result = await handle.done;
    assert.equal(result.code, 0);
    assert.equal(handle.stopped, null);
    assert.equal(
      handle.ledger.read().some((e) => e.event === "refused"),
      false
    );
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a missing estimate is unchecked, not zero, and still runs", async () => {
  const dir = root();
  try {
    assert.deepEqual(preflightBudget(agent({ budget: { maxCostUsd: 0 } }), {}), {
      ok: true,
      unchecked: "no-estimate",
    });
    const handle = spawnAgent(agent({ budget: { maxCostUsd: 0 } }), {
      root: dir,
      job: { orders: "no price on this one" },
    });
    const result = await handle.done;
    assert.equal(result.code, 0);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("no cap means no gate at all", () => {
  assert.deepEqual(preflightBudget(agent(), { estimatedCostUsd: 9999 }), {
    ok: true,
  });
});

test("a negative or non-numeric estimate is refused by name", () => {
  const a = agent({ budget: { maxCostUsd: 1 } });
  assert.throws(
    () => preflightBudget(a, { estimatedCostUsd: -1 }),
    /budget: estimatedCostUsd must be a non-negative number/
  );
  assert.throws(
    () => preflightBudget(a, { estimatedCostUsd: "0.5" }),
    /budget: estimatedCostUsd must be a non-negative number/
  );
});

test("a registry entry with a bad cap is refused at load", () => {
  const dir = root();
  try {
    const file = join(dir, "registry.json");
    writeFileSync(
      file,
      JSON.stringify({
        agents: [{ name: "bad", lane: "test", command: NOOP, budget: { maxCostUsd: -1 } }],
      })
    );
    assert.throws(() => loadRegistry(file), /registry: bad bad maxCostUsd/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a refusal writes a brief so the run is still reconstructible", async () => {
  const dir = root();
  try {
    const handle = spawnAgent(agent({ budget: { maxCostUsd: 0.1 } }), {
      root: dir,
      job: { estimatedCostUsd: 0.2, orders: "too dear" },
    });
    await handle.done;
    const brief = JSON.parse(readFileSync(join(handle.runDir, "brief.json"), "utf8"));
    assert.equal(brief.orders, "too dear");
    assert.equal(brief.budget.maxCostUsd, 0.1);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
