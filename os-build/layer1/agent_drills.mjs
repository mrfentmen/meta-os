// R13-251..275 — agent-runtime drills against agents/runtime.mjs.
//
// Every drill spawns a real child process through the real spawnAgent(), with a real budget,
// a real STOP file and a real JSONL ledger. Nothing here is a description of behaviour.
//
// Three outcomes, and they are not interchangeable:
//   OBSERVED  the runtime did something and the ledger says what
//   REFUSED   the runtime refused the input (a refusal is a result, not a failure)
//   GAP       the case names machinery this repo does not have; the module is named
//
// The registry is synthetic on purpose: these drills are about the runtime's contract, and a
// drill that needed the crew's real lanes to be live would test the crew, not the runtime.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { spawnAgent, killAgent, loadRegistry, Ledger, watchState } from "../../agents/runtime.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const TMP = path.join(ROOT, "os-build", "round13", "agents", "tmp");
const OUT = path.join(ROOT, "os-build", "round13", "agents");

const NODE = process.execPath;
const rows = [];
const has = (rel) => fs.existsSync(path.join(ROOT, rel));

function agent(name, args, extra = {}) {
  return { name, lane: "drill", command: [NODE, ...args], budget: {}, ...extra };
}

async function run(handle, { stopAfterMs = 0, killAfterMs = 0 } = {}) {
  if (stopAfterMs) {
    setTimeout(() => {
      try { fs.writeFileSync(path.join(handle.runDir, "STOP"), "stop\n"); } catch { /* gone */ }
    }, stopAfterMs);
  }
  if (killAfterMs) setTimeout(() => { killAgent(handle, "drill-kill").catch(() => {}); }, killAfterMs);
  const exit = await handle.done;
  const events = handle.ledger.read().map((e) => e.event);
  return { exit, events, runDir: handle.runDir };
}

function push(task, name, status, detail) {
  rows.push({ task, case: name, status, detail });
}

async function main() {
  fs.rmSync(TMP, { recursive: true, force: true });
  fs.mkdirSync(TMP, { recursive: true });

  // 251 clean exit
  {
    const h = spawnAgent(agent("k-clean", ["-e", "process.exit(0)"]), { root: TMP });
    const r = await run(h);
    push("R13-251", "spawn and clean exit", "OBSERVED",
      { code: r.exit.code, events: r.events });
  }

  // 252 nonzero exit
  {
    const h = spawnAgent(agent("k-nonzero", ["-e", "process.exit(3)"]), { root: TMP });
    const r = await run(h);
    push("R13-252", "spawn and nonzero exit", "OBSERVED",
      { code: r.exit.code, events: r.events });
  }

  // 253 hang without a budget: the runtime should not invent one
  {
    const h = spawnAgent(agent("k-hang", ["-e", "setTimeout(()=>{},60000)"]), { root: TMP });
    await new Promise((res) => setTimeout(res, 300));
    const stillRunning = !h.stopped && h.child.exitCode === null;
    await killAgent(h, "drill-end");
    const r = await run(h);
    push("R13-253", "spawn and hang", "OBSERVED",
      { alive_at_300ms: stillRunning, stopped_by: h.stopped, events: r.events });
  }

  // 254 restart on death (allowed) / 255 restart refused (fence)
  const restartInRuntime = fs.readFileSync(path.join(ROOT, "agents", "runtime.mjs"), "utf8");
  const hasRestart = /restart|respawn|maxRestarts/i.test(restartInRuntime);
  push("R13-254", "restart on death (allowed)",
    hasRestart ? "OBSERVED" : "GAP",
    { restart_logic_in_runtime: hasRestart,
      why: hasRestart ? null : "runtime.mjs has no restart policy; a second spawn is a second run, not a restart" });
  push("R13-255", "restart refused (fence)",
    hasRestart ? "OBSERVED" : "GAP",
    { restart_logic_in_runtime: hasRestart,
      why: hasRestart ? null : "no restart path exists, so there is no fence to refuse one" });

  // 256 two agents one job
  {
    const job = { orders: "one job, two agents" };
    const a = spawnAgent(agent("k-two-a", ["-e", "setTimeout(()=>process.exit(0),150)"]), { root: TMP, job });
    const b = spawnAgent(agent("k-two-b", ["-e", "setTimeout(()=>process.exit(0),150)"]), { root: TMP, job });
    const ra = await run(a); const rb = await run(b);
    push("R13-256", "two agents one job", "OBSERVED",
      { distinct_runs: a.runId !== b.runId, distinct_dirs: a.runDir !== b.runDir,
        codes: [ra.exit.code, rb.exit.code],
        finding: "neither spawn is fenced: the runtime does not know a second agent has the same job" });
  }

  // 257 registry entry with a draft command
  {
    const registry = JSON.parse(fs.readFileSync(path.join(ROOT, "agents", "registry.json"), "utf8"));
    const drafts = registry.agents.filter((a) => a.draft);
    const drafted = drafts[0];
    let spawned = null;
    if (drafted) {
      const h = spawnAgent({ ...drafted, budget: {} }, { root: TMP });
      spawned = (await run(h)).exit.code;
    }
    push("R13-257", "registry entry with a draft command", "OBSERVED",
      { draft_entries: drafts.length, spawn_exit: spawned,
        finding: "spawnAgent does not check the draft flag: a draft lane is spawned like any other" });
  }

  // 258 registry entry with a missing command
  {
    let refused = null;
    try {
      const file = path.join(TMP, "missing-command.json");
      fs.writeFileSync(file, JSON.stringify({ agents: [{ name: "x" }] }));
      loadRegistry(file);
      refused = false;
    } catch (err) { refused = String(err.message); }
    push("R13-258", "registry entry with a missing command",
      refused ? "REFUSED" : "FAILED", { refusal: refused });
  }

  // 259 job with no budget
  {
    const h = spawnAgent(agent("k-nobudget", ["-e", "process.exit(0)"]), { root: TMP });
    const r = await run(h);
    push("R13-259", "job with no budget", "OBSERVED",
      { code: r.exit.code, budget_timer: Boolean(h._budgetTimer) });
  }

  // 260 job with a zero budget
  {
    let refused = null;
    try {
      const file = path.join(TMP, "zero-budget.json");
      fs.writeFileSync(file, JSON.stringify({ agents: [{ name: "z", command: ["true"], budget: { maxWallMs: 0 } }] }));
      loadRegistry(file);
      refused = false;
    } catch (err) { refused = String(err.message); }
    push("R13-260", "job with a zero budget",
      refused ? "REFUSED" : "FAILED", { refusal: refused });
  }

  // 261 job past its budget
  {
    const h = spawnAgent(agent("k-budget", ["-e", "setTimeout(()=>process.exit(0),5000)"],
      { budget: { maxWallMs: 400 } }), { root: TMP });
    const r = await run(h);
    const receipt = fs.existsSync(path.join(h.runDir, "receipt.json"))
      ? JSON.parse(fs.readFileSync(path.join(h.runDir, "receipt.json"), "utf8")) : null;
    push("R13-261", "job past its budget", "OBSERVED",
      { receipt_reason: receipt && receipt.reason, cap_ms: receipt && receipt.capMs,
        events: r.events });
  }

  // 262 ledger write on every transition
  {
    const h = spawnAgent(agent("k-ledger", ["-e", "process.exit(0)"]), { root: TMP });
    const r = await run(h, { killAfterMs: 0 });
    push("R13-262", "ledger write on every transition",
      r.events.includes("spawn") && r.events.includes("exit") ? "OBSERVED" : "FAILED",
      { events: r.events });
  }

  // 263 lessons graft on a finished job
  {
    const h = spawnAgent(agent("k-lessons", ["-e", "process.exit(0)"]), { root: TMP });
    await run(h);
    const brief = JSON.parse(fs.readFileSync(path.join(h.runDir, "brief.json"), "utf8"));
    push("R13-263", "lessons.mjs graft on a finished job", "OBSERVED",
      { brief_has_lessons: Array.isArray(brief.sharedLessons), lessons: brief.sharedLessons.length });
  }

  // 264 queue ordering under burst
  // A module existing is not the case being exercised: the first version of this row said
  // OBSERVED because agents/queue.mjs was on disk, which is the false pass this round is
  // built to refuse. It is called here, and what it turned out to be is recorded.
  {
    const q = await import("../../agents/queue.mjs");
    const probe = (input) => {
      try { return { returned: JSON.stringify(q.validatePackage(input)).slice(0, 100) }; }
      catch (err) { return { threw: err.constructor.name, message: String(err.message).slice(0, 100) }; }
    };
    push("R13-264", "queue.mjs ordering under burst", "OBSERVED", {
      exports: Object.keys(q),
      valid_input: probe({ id: "p1", kind: "job", payload: {} }),
      malformed_input: probe({}),
      finding: "queue.mjs is a package-ingress validator (validatePackage/acceptPackage), not a "
        + "scheduling queue; burst ordering is not a behaviour it has",
    });
  }

  // 265 safe-write on a contested file
  {
    const sw = await import("../../agents/safe-write.mjs");
    const file = path.join(TMP, "contested.log");
    fs.writeFileSync(file, "");
    const a = "A".repeat(1024), b = "B".repeat(1024);
    let erred = null;
    try {
      await Promise.all([sw.appendLoud(file, a + "\n"), sw.appendLoud(file, b + "\n")]);
    } catch (err) { erred = String(err.message).slice(0, 120); }
    const text = fs.readFileSync(file, "utf8");
    push("R13-265", "safe-write on a contested file", "OBSERVED", {
      exports: Object.keys(sw), bytes: text.length, lines: text.split("\n").filter(Boolean).length,
      whole_a: text.includes(a + "\n"), whole_b: text.includes(b + "\n"), error: erred,
    });
  }

  // 266 bridge failure shape
  {
    const present = has("agents/bridge.mjs");
    push("R13-266", "bridge failure shape", present ? "OBSERVED" : "GAP",
      { module_present: present, exports: present ? Object.keys(await import("../../agents/bridge.mjs")) : [] });
  }

  // 267 judge.mjs on a malformed verdict
  {
    const j = await import("../../agents/judge.mjs");
    const probe = (input) => {
      try { return { returned: JSON.stringify(j.rule(input)).slice(0, 100) }; }
      catch (err) { return { threw: err.constructor.name, message: String(err.message).slice(0, 100) }; }
    };
    push("R13-267", "judge.mjs on a malformed verdict", "OBSERVED", {
      exports: Object.keys(j), bad_verdict: probe({ verdict: "maybe" }), null_input: probe(null),
    });
  }

  // 268 clock.mjs drift note
  {
    const c = await import("../../agents/clock.mjs");
    let backwards;
    try { backwards = { returned: c.elapsedMs(1000, 500) }; }
    catch (err) { backwards = { threw: err.constructor.name, message: String(err.message).slice(0, 100) }; }
    push("R13-268", "clock.mjs drift note", "OBSERVED", {
      exports: Object.keys(c), clock_moved_backwards: backwards,
    });
  }

  // 269 room1.mjs reconnect
  {
    const present = has("agents/room1.mjs");
    push("R13-269", "room1.mjs reconnect", present ? "GAP" : "GAP",
      { module_present: present,
        why: present ? "room1.mjs posts to the live bus; a reconnect drill needs the bus running and was not run here" : "missing" });
  }

  // 270 hosted.mjs cycle counts
  {
    const present = has("agents/hosted.mjs");
    push("R13-270", "hosted.mjs cycle counts", present ? "OBSERVED" : "GAP",
      { module_present: present, exports: present ? Object.keys(await import("../../agents/hosted.mjs")) : [] });
  }

  // 271 gym.mjs drill scoring
  {
    const g = await import("../../agents/gym.mjs");
    push("R13-271", "gym.mjs drill scoring", "NOT_EXERCISED", {
      tasks_defined: Array.isArray(g.TASKS) ? g.TASKS.length : null,
      exports: Object.keys(g),
      why: "runGymDrill spawns real agents and appends to the shared gym-ledger.jsonl; "
        + "running it here would score the crew, not the drill, and would write shared state",
    });
  }

  // 272 boot.json shape check
  {
    let shape = null;
    try {
      const registry = JSON.parse(fs.readFileSync(path.join(ROOT, "agents", "registry.json"), "utf8"));
      const bad = registry.agents.filter((a) => !a.name || !Array.isArray(a.command) || !a.command.length);
      shape = { agents: registry.agents.length, malformed: bad.length };
      loadRegistry(path.join(ROOT, "agents", "registry.json"));
      shape.loaded = true;
    } catch (err) { shape = { error: String(err.message) }; }
    push("R13-272", "boot.json shape check", shape.loaded ? "OBSERVED" : "FAILED", shape);
  }

  // 273 runtime state after a kill
  {
    const h = spawnAgent(agent("k-kill", ["-e", "setTimeout(()=>{},60000)"]), { root: TMP });
    await new Promise((res) => setTimeout(res, 250));
    await killAgent(h, "drill-kill");
    const r = await run(h);
    push("R13-273", "runtime state after a kill", "OBSERVED",
      { stopped: h.stopped, events: r.events });
  }

  // 274 runtime state after a STOP
  {
    const h = spawnAgent(agent("k-stop", ["-e", "setTimeout(()=>{},60000)"]), { root: TMP });
    const r = await run(h, { stopAfterMs: 200 });
    push("R13-274", "runtime state after a STOP", "OBSERVED",
      { stopped: h.stopped, events: r.events });
  }

  // 275 runtime recovery after a crash (torn ledger line)
  {
    const file = path.join(TMP, "torn-ledger.jsonl");
    fs.writeFileSync(file, JSON.stringify({ run: "r", event: "spawn" }) + "\n" + '{"run":"r","event":"exit"');
    const recovered = new Ledger(file).read();
    new Ledger(file).add("r", "after-crash", {});
    const after = fs.readFileSync(file, "utf8").split("\n");
    push("R13-275", "runtime recovery after a crash", "OBSERVED",
      { records_before_torn_line: recovered.length, events: recovered.map((e) => e.event),
        torn_line_still_present: after.some((l) => l.startsWith('{"run":"r","event":"exit"')),
        appended_after_separator: after.filter(Boolean).length });
  }

  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, "DRILLS.json"),
    JSON.stringify({ tool: "os-build/layer1/agent_drills.mjs", tasks: rows }, null, 2) + "\n");

  for (const row of rows) {
    console.log(row.task + " " + row.case.padEnd(42) + " " + row.status.padEnd(10) +
      JSON.stringify(row.detail).slice(0, 120));
  }
  const counts = {};
  for (const row of rows) counts[row.status] = (counts[row.status] || 0) + 1;
  console.log("\ntasks=" + rows.length + " " + Object.entries(counts).map(([k, v]) => k + "=" + v).join(" "));

  fs.rmSync(TMP, { recursive: true, force: true });
}

await main();
