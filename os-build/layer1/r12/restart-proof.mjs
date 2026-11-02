// Round 12, Section D restart proof — the services that are real host processes.
//
// Only three of the 38 service directories contain a `main` a host can run: echo, heartbeat,
// mcp-host. The other 35 are libraries or svc_entry code and cannot be started by
// services/supervisor.sh at all; that gap is filed in RESTART_GAP.md.
//
// Each run copies the .goose source to a temp directory so no repository state file is touched.
// Heartbeat: killed and restarted, log appends rather than truncates, STOP exits cleanly.
// Echo: killed and restarted, answers again; no persistent state is claimed.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import url from "node:url";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.dirname(path.dirname(path.dirname(HERE)));
const SUP = path.join(ROOT, "services", "supervisor.sh");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitFor(pred, ms, label) {
  const t = Date.now();
  while (Date.now() - t < ms) {
    if (pred()) return Date.now() - t;
    await sleep(50);
  }
  throw new Error("timed out waiting for " + label);
}
const lines = (file) => (fs.existsSync(file) ? fs.readFileSync(file, "utf8").trim().split("\n").filter(Boolean) : []);
// heartbeat.goose appends the four letters "beat" with no newline, so counting lines counts 1
// forever. Count the beats themselves; that is the growth the restart has to preserve.
const beats = (file) => {
  try { return (fs.readFileSync(file, "utf8").match(/beat/g) || []).length; }
  catch { return 0; }
};

async function heartbeatDrill() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "restart-heartbeat-"));
  fs.copyFileSync(path.join(ROOT, "services", "heartbeat", "heartbeat.goose"), path.join(dir, "heartbeat.goose"));
  const log = path.join(dir, "heartbeat.log");
  const started = Date.now();
  const run = () => spawn("sh", [SUP, "heartbeat", dir], { cwd: ROOT, detached: true, stdio: ["ignore", "pipe", "pipe"] });
  const first = run();
  await waitFor(() => beats(log) >= 2, 12000, "first heartbeat beats");
  const beforeKill = beats(log);
  process.kill(-first.pid, "SIGKILL");
  await sleep(250);
  const afterKill = beats(log);

  const second = run();
  const grewMs = await waitFor(() => beats(log) > afterKill, 12000, "beats after restart");
  const afterRestart = beats(log);
  fs.writeFileSync(path.join(dir, "STOP"), "restart drill done\n");
  const exit = await new Promise((resolve) => {
    const timer = setTimeout(() => resolve({ timeout: true }), 8000);
    second.on("close", (code, signal) => { clearTimeout(timer); resolve({ code, signal }); });
  });
  const records = lines(path.join(dir, "records.log"));
  return {
    service: "heartbeat",
    dir,
    ok: beforeKill >= 2 && afterRestart > afterKill && exit.code === 0 &&
      records.filter((l) => /service-start/.test(l)).length === 2,
    beforeKill, afterKill, afterRestart, grewMs,
    stoppedCleanly: exit.code === 0,
    recordedStarts: records.filter((l) => /service-start/.test(l)).length,
    recordedStops: records.filter((l) => /service-stop/.test(l)).length,
    note: "append-only heartbeat.log survived the kill and grew after restart; STOP was the clean stop",
    wallMs: Date.now() - started,
  };
}

async function echoDrill() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "restart-echo-"));
  fs.copyFileSync(path.join(ROOT, "services", "echo", "echo.goose"), path.join(dir, "echo.goose"));
  const out = path.join(dir, "service.out");
  const start = () => spawn("sh", [SUP, "echo", dir, "--once"], { cwd: ROOT, detached: true, stdio: ["pipe", "pipe", "pipe"] });
  const first = start();
  first.stdin.write("one\n");
  await waitFor(() => fs.existsSync(out) && fs.readFileSync(out, "utf8").includes("echo: one"), 8000, "first echo");
  process.kill(-first.pid, "SIGKILL");
  await sleep(200);
  const second = start();
  second.stdin.write("two\n");
  await waitFor(() => fs.readFileSync(out, "utf8").includes("echo: two"), 8000, "echo after restart");
  const body = fs.readFileSync(out, "utf8");
  process.kill(-second.pid, "SIGKILL");
  await sleep(150);
  const records = lines(path.join(dir, "records.log"));
  return {
    service: "echo",
    dir,
    ok: body.includes("echo: one") && body.includes("echo: two") &&
      records.filter((l) => /service-start/.test(l)).length === 2,
    answeredBeforeKill: body.includes("echo: one"),
    answeredAfterRestart: body.includes("echo: two"),
    recordedStarts: records.filter((l) => /service-start/.test(l)).length,
    note: "no persistent state; the restart proves the process and its stdio contract, not state survival",
  };
}

const results = [];
for (const drill of [heartbeatDrill, echoDrill]) {
  try { results.push(await drill()); }
  catch (err) {
    results.push({ service: drill.name, ok: false, error: String(err && err.message || err) });
  }
}
const ok = results.every((r) => r.ok);
const receipt = {
  task: "R12-027..R12-034 (restart half, services that run on a host)",
  at: new Date().toISOString(),
  ok,
  services: results,
  scope: "3 of 38 services have a main a host can run; only echo and heartbeat were drilled here. " +
    "mcp-host is the third and is named in RESTART_GAP.md; the other 35 cannot be started by supervisor.sh.",
};
fs.writeFileSync(path.join(HERE, "RESTART_PROOF.json"), JSON.stringify(receipt, null, 2) + "\n");
console.log("restart proof: " + (ok ? "PASS" : "FAIL") + " — " + results.map((r) => r.service + "=" + r.ok).join(" "));
process.exit(ok ? 0 : 1);
