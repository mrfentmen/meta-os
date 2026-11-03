// Round 8, A1 — failure injection against the agent runtime and the relay-watchman.
//
// The runtime is the part of this OS that runs OTHER programs, so its failure modes are not
// "does it work" but "what does the record say when it doesn't". Each test below breaks one
// thing on purpose and asserts what survives:
//
//   1. a torn LAST ledger line (crash mid-append) is skipped and the run stays
//      readable; a torn MIDDLE line is corruption, not a crash, and read refuses
//      with its line number instead of silently dropping the middle of the record
//   2. a kill mid-write must leave one stop-request and one exit, and a readable ledger
//   3. a second kill must not append a second stop-request
//   4. a STOP file that arrives after the run ended must not manufacture a stop
//   5. budget and exit racing must not duplicate the exit record
//   6. a registry entry with a nonsense budget must be refused, not clamped
//   7. a half-written job file must be ignored and retried, not claimed forever
//
// Run: node --test tests/agents-hardening.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnAgent, killAgent, loadRegistry, Ledger } from "../agents/runtime.mjs";
import { createWatchman } from "../agents/watchman.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "agents-hardening-"));
const NODE = process.execPath;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

test("A1.1 a torn tail line is skipped, a torn middle line refuses with its line number", () => {
  // Strict ledger policy (landed with the agent-runtime-harden hand-combine):
  // a crash tears only the last append, so a torn tail is skipped; a torn line
  // with good records after it is a spliced file, and read must refuse loudly
  // rather than silently drop the middle of the run's evidence.
  const dir = tmp();
  const file = path.join(dir, "ledger.jsonl");
  const ledger = new Ledger(file);
  ledger.add("run-1", "spawn", { lane: "test" });
  // A process killed mid-append leaves exactly this: a line with no closing brace.
  fs.appendFileSync(file, '{"ts":"2026-11-02T00:00:00.000Z","run":"run-1","event":"exit"');
  ledger.add("run-1", "done", { code: 0 });
  // The torn line is in the middle now (a good record follows it): refuse, named.
  assert.throws(() => ledger.read(), /ledger: torn line 2/);
  // Same tear as the last line (a true crash tail): skipped, history readable.
  const dir2 = tmp();
  const file2 = path.join(dir2, "ledger.jsonl");
  const ledger2 = new Ledger(file2);
  ledger2.add("run-1", "spawn", { lane: "test" });
  fs.appendFileSync(file2, '{"ts":"2026-11-02T00:00:00.000Z","run":"run-1","event":"exit"');
  const lines = ledger2.read();
  assert.equal(lines.length, 1, "the complete record is still readable");
  assert.equal(lines[0].event, "spawn");
});

test("A1.2 kill mid-write leaves one stop, one exit, and a readable ledger", async () => {
  const root = tmp();
  // Write slowly enough that the kill lands while the file is being written.
  const writer = "const fs=require('fs');const fd=fs.openSync('big.bin','w');const b=Buffer.alloc(65536,120);for(let i=0;i<200;i++){fs.writeSync(fd,b);}fs.closeSync(fd);setTimeout(()=>{},30000)";
  const agent = { name: "halfwriter", command: [NODE, "-e", writer], budget: {} };
  const h = spawnAgent(agent, { root });
  await sleep(30);
  await killAgent(h, "mid-write", 300);
  const events = h.ledger.read().map((l) => l.event);
  assert.equal(events.filter((e) => e === "stop-request").length, 1);
  assert.equal(events.filter((e) => e === "exit").length, 1);
  assert.ok(events.indexOf("spawn") < events.indexOf("exit"));
  // The run is marked, which is what a restart reads to know this run did not finish by itself.
  const exit = h.ledger.read().find((l) => l.event === "exit");
  assert.equal(exit.stopped, "mid-write");
});

test("A1.3 a second kill is a no-op, not a second stop record", async () => {
  const root = tmp();
  const agent = { name: "sleepy", command: [NODE, "-e", "setTimeout(()=>{},30000)"], budget: {} };
  const h = spawnAgent(agent, { root });
  await killAgent(h, "first", 200);
  await killAgent(h, "second", 200);
  const stops = h.ledger.read().filter((l) => l.event === "stop-request");
  assert.equal(stops.length, 1);
  assert.equal(stops[0].reason, "first");
});

test("A1.4 a STOP file after the run ended does not manufacture a stop", async () => {
  const root = tmp();
  const agent = { name: "quick", command: [NODE, "-e", ""], budget: {} };
  const h = spawnAgent(agent, { root });
  await h.done;
  fs.writeFileSync(path.join(h.runDir, "STOP"), "");
  await sleep(200);
  const events = h.ledger.read().map((l) => l.event);
  assert.equal(events.filter((e) => e === "stop-request").length, 0);
  assert.equal(events.filter((e) => e === "exit").length, 1);
});

test("A1.5 budget and exit racing do not duplicate the exit record", async () => {
  const root = tmp();
  // 1 ms budget against a process that exits in about 20 ms: the timer and the exit race.
  const agent = { name: "racer", command: [NODE, "-e", "setTimeout(()=>{},5)"], budget: { maxWallMs: 1 } };
  const h = spawnAgent(agent, { root });
  await h.done;
  await sleep(50);
  const events = h.ledger.read().map((l) => l.event);
  assert.equal(events.filter((e) => e === "exit").length, 1);
  assert.ok(events.filter((e) => e === "stop-request").length <= 1);
  // Whatever happened, the record is parseable end to end.
  assert.equal(h.ledger.read().length, events.length);
});

test("A1.6 a registry entry with an impossible budget is refused", () => {
  const dir = tmp();
  const write = (name, body) => {
    const f = path.join(dir, name);
    fs.writeFileSync(f, JSON.stringify(body));
    return f;
  };
  assert.throws(
    () => loadRegistry(write("neg.json", { agents: [{ name: "a", command: ["true"], budget: { maxWallMs: -5 } }] })),
    /bad maxWallMs/,
  );
  assert.throws(
    () => loadRegistry(write("zero.json", { agents: [{ name: "a", command: ["true"], budget: { maxWallMs: 0 } }] })),
    /bad maxWallMs/,
  );
  // A budget of null/absent means "no cap" and must load: the runtime's default.
  const ok = loadRegistry(write("ok.json", { agents: [{ name: "a", command: ["true"] }] }));
  assert.equal(ok.length, 1);
});

test("A1.7 a half-written job file is retried, not claimed forever", async () => {
  const dir = tmp();
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({
    agents: [{ name: "worker", command: [NODE, "-e", ""], budget: {} }],
  }));
  const jobsDir = path.join(dir, "jobs");
  const w = createWatchman({ registryFile: registry, root: dir, jobsDir });

  // Mid-write: valid JSON is impossible to parse, and the id is visible in the text.
  fs.writeFileSync(path.join(jobsDir, "h1.job.json"), '{"id":"h1","agent":"worker","orders":"half');
  assert.equal((await w.pollOnce()).length, 0);
  // No state file simply means nothing has been claimed yet; an empty claimed list is the same
  // fact recorded. Reading it unconditionally made the test fail on the correct behaviour.
  const statePath = path.join(dir, "watchman-state.json");
  const claimed = fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath, "utf8")).claimed : [];
  assert.deepEqual(claimed, [], "an unparseable job is not claimed");

  // The writer finishes. The next poll runs it exactly once.
  fs.writeFileSync(path.join(jobsDir, "h1.job.json"), JSON.stringify({ id: "h1", agent: "worker", orders: "whole" }));
  const first = await w.pollOnce();
  assert.equal(first.length, 1);
  const after = JSON.parse(fs.readFileSync(path.join(dir, "watchman-state.json"), "utf8")).claimed;
  assert.deepEqual(after, ["h1"], "the complete job is claimed by id");
  await first[0].handle.done;
  assert.equal((await w.pollOnce()).length, 0);
});
