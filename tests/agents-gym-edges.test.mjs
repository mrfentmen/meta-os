// CB2-387..388: drill files.
//
// A drill declares its steps; an unknown type is refused at load with the type
// named. A real drill runs through agents/runtime.mjs (spawnAgent is the real
// import, no mock of it) and records one result per step.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  loadDrillFile,
  recordGymResult,
  runDrillFile,
} from "../agents/gym.mjs";
import { Ledger } from "../agents/runtime.mjs";
import { existsSync } from "node:fs";

const NOOP_OK = [process.execPath, "-e", "process.exit(0)"];
const NOOP_FAIL = [process.execPath, "-e", "process.exit(3)"];

function workspace({ command = NOOP_OK } = {}) {
  const dir = mkdtempSync(join(tmpdir(), "gym-drill-file-"));
  const registryFile = join(dir, "registry.json");
  writeFileSync(
    registryFile,
    JSON.stringify({
      agents: [{ name: "trainee", lane: "test", command, budget: {} }],
    })
  );
  return { dir, registryFile };
}

function writeDrill(dir, drill) {
  const file = join(dir, "drill.json");
  writeFileSync(file, JSON.stringify(drill));
  return file;
}

test("an unknown step type is refused with the type named", () => {
  const { dir } = workspace();
  try {
    const file = writeDrill(dir, {
      id: "bad-drill",
      steps: [{ type: "registry-entry" }, { type: "teleport" }],
    });
    assert.throws(
      () => loadDrillFile(file),
      /gym drill: unknown step type "teleport" at step 1/
    );
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a drill with no steps or no id is refused", () => {
  const { dir } = workspace();
  try {
    assert.throws(
      () => loadDrillFile(writeDrill(dir, { id: "empty", steps: [] })),
      /steps must be a non-empty array/
    );
    assert.throws(
      () => loadDrillFile(writeDrill(dir, { steps: [{ type: "spawn" }] })),
      /missing id/
    );
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a real drill runs through the runtime and scores every step", async () => {
  const { dir, registryFile } = workspace();
  try {
    const file = writeDrill(dir, {
      id: "drill-file-1",
      agent: "trainee",
      steps: [
        { id: "entry", type: "registry-entry" },
        { id: "spawn", type: "spawn" },
        { id: "ledger", type: "ledger-readable" },
      ],
    });
    const result = await runDrillFile({
      file,
      registryFile,
      runRoot: join(dir, "runs-root"),
    });

    assert.equal(result.drill, "drill-file-1");
    assert.equal(result.agent, "trainee");
    assert.equal(result.total, 3);
    assert.equal(result.max, 3);
    assert.deepEqual(
      result.tasks.map((t) => [t.id, t.type, t.score]),
      [
        ["entry", "registry-entry", 1],
        ["spawn", "spawn", 1],
        ["ledger", "ledger-readable", 1],
      ]
    );

    // The run was real: the brief is on disk and the ledger has both events.
    assert.ok(existsSync(join(result.runDir, "brief.json")));
    const events = new Ledger(join(result.runDir, "ledger.jsonl")).read();
    assert.deepEqual(
      events.map((e) => e.event),
      ["spawn", "exit"]
    );
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a failing agent scores the spawn step 0 and the others stay honest", async () => {
  const { dir, registryFile } = workspace({ command: NOOP_FAIL });
  try {
    const file = writeDrill(dir, {
      id: "drill-file-2",
      agent: "trainee",
      steps: [{ type: "registry-entry" }, { type: "spawn" }],
    });
    const result = await runDrillFile({
      file,
      registryFile,
      runRoot: join(dir, "runs-root"),
    });
    assert.deepEqual(
      result.tasks.map((t) => t.score),
      [1, 0]
    );
    assert.equal(result.total, 1);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("per-step results land in the gym ledger and on the registry entry", async () => {
  const { dir, registryFile } = workspace();
  try {
    const file = writeDrill(dir, {
      id: "drill-file-3",
      agent: "trainee",
      steps: [{ id: "entry", type: "registry-entry" }, { id: "run", type: "spawn" }],
    });
    const result = await runDrillFile({
      file,
      registryFile,
      runRoot: join(dir, "runs-root"),
    });
    const gymLedgerFile = join(dir, "gym-ledger.jsonl");
    recordGymResult({ registryFile, gymLedgerFile, result });

    const events = new Ledger(gymLedgerFile).read();
    assert.deepEqual(
      events.filter((e) => e.event === "gym-task-score").map((e) => e.task),
      ["entry", "run"]
    );
    assert.equal(events.filter((e) => e.event === "gym-total").length, 1);

    const registry = JSON.parse(readFileSync(registryFile, "utf8"));
    assert.equal(registry.agents[0].gym.total, 2);
    assert.equal(registry.agents[0].gym.tasks.length, 2);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a drill file that is not an object is refused", () => {
  const { dir } = workspace();
  try {
    const file = join(dir, "array.json");
    writeFileSync(file, "[]");
    assert.throws(() => loadDrillFile(file), /file must hold an object/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
