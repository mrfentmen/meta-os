// Meta OS agent layer — supervisor → runtime bridge (Round 8, B1/B2).
//
// The supervisor decides whether a service may run; the runtime runs one agent when told. This
// is the verb between them and nothing else: no policy of its own, no state the supervisor does
// not have. Design: os-build/layer1/SUPERVISOR_BRIDGE.md.
//
//   node agents/bridge.mjs boot [bootFile]
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { loadRegistry, spawnAgent, killAgent, Ledger } from "./runtime.mjs";

export const BST_STOPPED = "stopped";
export const BST_RUNNING = "running";
export const BST_FAILED = "failed";

// CB2-392: the bridge has one message, and it is the reply to a start or a stop.
// It is addressed to the agent, carries a kind and a body, and is versioned so a
// reader can tell a shaped reply from a ledger note. A message with no
// destination is refused: a reply to nobody is not a message.
export const WIRE_FIELDS = ["v", "to", "kind", "body", "ts"];

export function toWire(message) {
  if (!message || typeof message !== "object") throw new Error("bridge: message has no destination");
  if (typeof message.to !== "string" || !message.to.trim()) {
    throw new Error("bridge: message has no destination");
  }
  if (typeof message.kind !== "string" || !message.kind.trim()) {
    throw new Error("bridge: message has no kind");
  }
  return {
    v: 1,
    to: message.to.trim(),
    kind: message.kind.trim(),
    body: message.body && typeof message.body === "object" ? { ...message.body } : {},
    ts: Number.isFinite(message.ts) ? message.ts : Date.now(),
  };
}

export function loadBoot(file) {
  const raw = JSON.parse(fs.readFileSync(file, "utf8"));
  if (!Array.isArray(raw.boot)) throw new Error("boot: 'boot' must be an array");
  const seen = new Set();
  for (const e of raw.boot) {
    if (!e.agent || typeof e.agent !== "string") throw new Error("boot: entry missing agent");
    if (seen.has(e.agent)) throw new Error("boot: duplicate agent " + e.agent);
    seen.add(e.agent);
  }
  // The same invariant bo_order_ok checks for services: every dependency appears earlier.
  raw.boot.forEach((e, i) => {
    for (const n of e.needs || []) {
      const at = raw.boot.findIndex((x) => x.agent === n);
      if (at < 0) throw new Error("boot: " + e.agent + " needs unknown agent " + n);
      if (at >= i) throw new Error("boot: " + e.agent + " needs " + n + " which does not come earlier");
    }
  });
  return raw.boot;
}

export function createBridge({ root, registryFile, bootFile }) {
  const agents = loadRegistry(registryFile);
  const boot = loadBoot(bootFile);
  const ledger = new Ledger(path.join(root, "bridge.jsonl"));
  const stopDir = path.join(root, "stop");
  fs.mkdirSync(stopDir, { recursive: true });

  const slots = new Map();
  for (const e of boot) {
    slots.set(e.agent, { state: BST_STOPPED, needs: e.needs || [], runId: null, handle: null, exit: null });
  }

  const stopMarker = (name) => path.join(stopDir, name + ".STOP");
  const refuse = (name, reason, extra = {}) => {
    // The refusal is answered to the agent that asked, in the wire shape, so the
    // ledger note and the reply cannot say different things.
    const wire = toWire({ to: name, kind: "refused", body: { reason, ...extra } });
    ledger.add("bridge", "refused", { agent: name, reason, ...extra });
    return { ok: false, reason, wire };
  };

  // Start one agent. Refusals are: unknown, already running, a dependency not running, a STOP
  // filed before the claim. All four are recorded; none invents a state.
  function start(name, job = {}) {
    const s = slots.get(name);
    if (!s) return refuse(name, "unknown-agent");
    if (s.state === BST_RUNNING) return { ok: false, reason: "already-running" };
    const missing = s.needs.filter((n) => (slots.get(n) || {}).state !== BST_RUNNING);
    if (missing.length) return refuse(name, "needs-not-running", { missing });
    if (fs.existsSync(stopMarker(name))) {
      ledger.add("bridge", "stop-pre-spawn", { agent: name });
      return { ok: false, reason: "stop-filed" };
    }
    const agent = agents.find((a) => a.name === name);
    if (!agent) return refuse(name, "not-in-registry");

    ledger.add("bridge", "start-request", { agent: name });
    const handle = spawnAgent(agent, { root, job: { orders: job.orders || "boot: " + name } });
    s.state = BST_RUNNING;
    s.handle = handle;
    s.runId = handle.runId;
    s.exit = null;
    ledger.add("bridge", "started", { agent: name, run: handle.runId });

    handle.done.then(({ code, signal }) => {
      s.exit = { code, signal };
      // A run that was stopped is stopped, whatever its exit code; only an unrequested exit can
      // be a failure. The runtime records the reason; this maps it to a supervisor state.
      s.state = handle.stopped || code === 0 ? BST_STOPPED : BST_FAILED;
      ledger.add("bridge", "exited", {
        agent: name, run: handle.runId, code, signal,
        state: s.state, stopped: handle.stopped || null,
      });
    });
    return { ok: true, run: handle.runId, handle };
  }

  // Stop one agent: the STOP file first (window 2), then the runtime's graceful-then-hard kill.
  async function stop(name, reason = "operator", graceMs = 400) {
    const s = slots.get(name);
    if (!s) return { ok: false, reason: "unknown-agent" };
    fs.mkdirSync(stopDir, { recursive: true });
    fs.writeFileSync(stopMarker(name), reason + "\n");
    ledger.add("bridge", "stop-request", { agent: name, reason });
    if (s.handle && !s.exit) await killAgent(s.handle, "bridge:" + reason, graceMs);
    return { ok: true };
  }

  const order = () => [...slots.keys()];
  const bootAll = (jobs = {}) => order().map((name) => ({ agent: name, ...start(name, jobs[name] || {}) }));
  const clearStop = (name) => { try { fs.unlinkSync(stopMarker(name)); } catch {} };

  return { slots, order, start, stop, bootAll, ledger, clearStop };
}

/* ---- CLI ---- */
const HERE = path.dirname(url.fileURLToPath(import.meta.url));
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const [, , cmd, bootArg] = process.argv;
  if (cmd !== "boot") {
    console.error("usage: bridge.mjs boot [bootFile]");
    process.exit(1);
  }
  const b = createBridge({
    root: HERE,
    registryFile: path.join(HERE, "registry.json"),
    bootFile: bootArg || path.join(HERE, "boot.json"),
  });
  for (const r of b.bootAll()) console.log(r.ok ? "started " + r.agent + " " + r.run : "refused " + r.agent + " (" + r.reason + ")");
}
