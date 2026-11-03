import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { checkBeat, writeBeat } from "../agents/watchdog.mjs";

function fixture() {
  const dir = mkdtempSync(join(tmpdir(), "agents-watchdog-"));
  return { dir, file: join(dir, "beat.json") };
}

test("one missed heartbeat is not flagged", () => {
  const { dir, file } = fixture();
  try {
    writeBeat(file, { now: 1_000 });
    const result = checkBeat(file, { now: 14_000, maxAgeMs: 15_000 });
    assert.equal(result.state, "fine");
    assert.equal(result.alarm, null);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("two missed heartbeats raise one alarm, then stay quiet", () => {
  const { dir, file } = fixture();
  try {
    writeBeat(file, { now: 1_000 });
    const dead = checkBeat(file, { now: 31_000, maxAgeMs: 15_000 });
    assert.equal(dead.state, "dead");
    assert.match(dead.alarm, /heartbeat lost/);
    const still = checkBeat(file, { now: 45_000, maxAgeMs: 15_000 });
    assert.equal(still.state, "still-dead");
    assert.equal(still.alarm, null, "an alarm is raised once, not every run");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a fresh beat clears the raised marker", () => {
  const { dir, file } = fixture();
  try {
    writeBeat(file, { now: 1_000 });
    checkBeat(file, { now: 31_000, maxAgeMs: 15_000 });
    writeBeat(file, { now: 32_000 });
    const recovered = checkBeat(file, { now: 33_000, maxAgeMs: 15_000 });
    assert.equal(recovered.state, "fine");
    assert.equal(recovered.cleared, true);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
