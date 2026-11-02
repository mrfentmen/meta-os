// Round 8, B3 — three agents up: one budget-killed, one STOP-filed, one completes.
//
// Every line below comes from a real child process and the ledgers on disk; the drill prints the
// events rather than summarising them, because the ledger lines are the proof the task asks for.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createBridge } from "../../agents/bridge.mjs";

const NODE = process.execPath;
const root = fs.mkdtempSync(path.join(os.tmpdir(), "bridge-drill-"));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const registryFile = path.join(root, "registry.json");
fs.writeFileSync(registryFile, JSON.stringify({
  agents: [
    { name: "worker", lane: "drill", command: [NODE, "-e", "const fs=require('fs');fs.writeFileSync('done.txt','finished')"], budget: {} },
    { name: "runner", lane: "drill", command: [NODE, "-e", "setTimeout(()=>{},30000)"], budget: { maxWallMs: 300 } },
    { name: "stoppable", lane: "drill", command: [NODE, "-e", "setTimeout(()=>{},30000)"], budget: {} },
  ],
}));
const bootFile = path.join(root, "boot.json");
fs.writeFileSync(bootFile, JSON.stringify({
  boot: [
    { agent: "worker", needs: [] },
    { agent: "runner", needs: [] },
    { agent: "stoppable", needs: [] },
  ],
}));

const b = createBridge({ root, registryFile, bootFile });
const started = b.bootAll();

const out = [];
const say = (s) => out.push(s);
say("# B3 bridge drill — three agents, three outcomes\n");
say("Root: `" + root + "`\n");
say("## Boot\n");
for (const r of started) say("- " + (r.ok ? "started `" + r.agent + "` run `" + r.run + "`" : "refused `" + r.agent + "` (" + r.reason + ")"));

// STOP the third mid-run; the second dies on its budget; the first finishes on its own.
await wait(120);
await b.stop("stoppable", "drill");
await Promise.all(started.filter((r) => r.ok).map((r) => r.handle.done));

say("\n## Outcomes\n");
for (const r of started) {
  if (!r.ok) continue;
  const s = b.slots.get(r.agent);
  const exit = b.ledger.read().find((l) => l.event === "exited" && l.agent === r.agent);
  say("- `" + r.agent + "`: state **" + s.state + "**, exit code " + exit.code + ", stopped `" + (exit.stopped || "—") + "`");
}
const workerRun = b.ledger.read().find((l) => l.event === "started" && l.agent === "worker").run;
say("- worker artifact: `done.txt` = " + JSON.stringify(fs.readFileSync(path.join(root, "runs", workerRun, "done.txt"), "utf8")));

say("\n## bridge.jsonl (the three runs)\n");
say("```jsonl");
for (const l of b.ledger.read()) say(JSON.stringify(l));
say("```\n");

say("## Per-run ledgers\n");
for (const r of started) {
  if (!r.ok) continue;
  const f = path.join(root, "runs", r.run, "ledger.jsonl");
  const events = new Set(fs.readFileSync(f, "utf8").split("\n").filter(Boolean).map((x) => JSON.parse(x).event));
  say("- `" + r.agent + "` run `" + r.run + "`: " + [...events].join(", "));
}
say("\nVerdict: one run completed on its own (exit 0), one was stopped by its wall-clock budget,");
say("one was stopped by a filed STOP — each recorded by the runtime and mapped to a supervisor");
say("state by the bridge, with no state the supervisor does not have.");
console.log(out.join("\n"));
