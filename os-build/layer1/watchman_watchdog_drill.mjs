// Round 8, A3 — stop a real watchman process and let the checker speak.
//
// Unlike the restart drill (which reconstructs a crash state), this one kills an actual process
// with SIGKILL: the heartbeat stops because the writer stopped, not because a test said so.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const NODE = process.execPath;
const CLI = path.join(ROOT, "agents", "watchdog.mjs");
const WATCHMAN = path.join(ROOT, "agents", "watchman.mjs");

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "watchdog-drill-"));
const jobs = path.join(dir, "jobs");
fs.mkdirSync(jobs, { recursive: true });
const registry = path.join(dir, "registry.json");
fs.writeFileSync(registry, JSON.stringify({ agents: [] }));
const beat = path.join(dir, "watchman.heartbeat.json");

// A watchman run as its own process, polling fast so the heartbeat is visibly alive.
const helper = path.join(dir, "relay-daemon.mjs");
fs.writeFileSync(helper, [
  'import { pathToFileURL } from "node:url";',
  'const { createWatchman } = await import(pathToFileURL(process.env.WATCHMAN_MOD).href);',
  'const w = createWatchman({ registryFile: process.env.REG, root: process.env.ROOT, jobsDir: process.env.JOBS, heartbeatFile: process.env.BEAT });',
  'await w.pollOnce();',
  'setInterval(() => { w.pollOnce(); }, 100);',
].join("\n"));

const check = (limit) => spawnSync(NODE, [CLI, "check", beat, String(limit)], { encoding: "utf8" });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const out = [];
const say = (s) => out.push(s);
say("# A3 watchdog drill — the heartbeat of a real relay, stopped\n");
say("Temp root: `" + dir + "`\n");

const child = spawn(NODE, [helper], {
  env: { ...process.env, WATCHMAN_MOD: WATCHMAN, REG: registry, ROOT: dir, JOBS: jobs, BEAT: beat },
  stdio: "ignore",
});
await wait(700);

say("## While the relay runs\n");
say("- heartbeat file: `" + (fs.existsSync(beat) ? fs.readFileSync(beat, "utf8") : "missing") + "`");
const alive = check(400);
say("- `check` with a 400 ms limit → exit " + alive.status + ", output " + JSON.stringify(alive.stdout.trim()) + "\n");

child.kill("SIGKILL");
await wait(900);

say("## After SIGKILL on the relay process (pid " + child.pid + ")\n");
const dead = check(400);
say("- `check` → exit " + dead.status);
say("- output:\n");
say("```\n" + dead.stdout.trim() + "\n```\n");
const again = check(400);
say("- `check` again → exit " + again.status + ", output " + JSON.stringify(again.stdout.trim()) + " (the same death is not re-announced)\n");

fs.writeFileSync(path.join(dir, "READ_ME.txt"), "drill artifacts\n");
console.log(out.join("\n"));
