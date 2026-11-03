// Meta OS agent layer — ephemeral sandboxes for untrusted work.
//
// An agent that wants to download a package, run a script, or open a
// hostile file does it here, not on the host. Each run gets a fresh
// container that is destroyed afterwards (--rm always): no network by
// default, capped memory/CPU/PIDs, and exactly one host touchpoint — a
// fresh temp dir mounted at /work. Nothing else on the host is visible.
//
// Requires Docker (or a compatible runtime on PATH as `docker`). Every
// entry point probes first and fails with NO_DOCKER instead of hanging.
//
//   node agents/sandbox.mjs probe
//   node agents/sandbox.mjs run --image ubuntu:24.04 --timeout 10000 --net none -- sh -c 'echo hi > /work/out.txt; cat /etc/os-release | head -1'
//
// Network: "none" (default) or "bridge" for runs that must fetch.
// Timeout kills the run (SIGTERM via spawnSync timeout) and reports
// timedOut:true. Output is capped (default 64 KiB per stream).

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

function fail(code, message, detail = {}) {
  const err = new Error(message);
  err.name = "SandboxError";
  err.code = code;
  Object.assign(err, detail);
  throw err;
}

export function probeDocker(dockerBin = "docker") {
  const r = spawnSync(dockerBin, ["info", "--format", "{{.ServerVersion}}"], { encoding: "utf8", timeout: 15000 });
  if (r.error || r.status !== 0) return { ok: false };
  return { ok: true, server: (r.stdout || "").trim() };
}

export function imagePresent(image, dockerBin = "docker") {
  const r = spawnSync(dockerBin, ["image", "inspect", image], { encoding: "utf8", timeout: 15000, stdio: ["ignore", "ignore", "ignore"] });
  return !r.error && r.status === 0;
}

const MAX_STREAM = 64 * 1024;

function cap(s) {
  if (s.length <= MAX_STREAM) return { text: s, truncated: false };
  return { text: s.slice(0, MAX_STREAM), truncated: true };
}

export function runSandbox(cmd, options = {}) {
  const dockerBin = options.dockerBin || "docker";
  const probe = probeDocker(dockerBin);
  if (!probe.ok) fail("NO_DOCKER", "no working docker runtime on PATH");
  const image = options.image || "ubuntu:24.04";
  if (!imagePresent(image, dockerBin)) fail("NO_IMAGE", `image not present locally (no implicit pulls): ${image}`);
  if (!Array.isArray(cmd) || !cmd.length) fail("NO_CMD", "run needs a command array");

  const work = options.work || fs.mkdtempSync(path.join(os.tmpdir(), "sandbox-work-"));
  const args = [
    "run", "--rm",
    "--network", options.network || "none",
    "--memory", options.memory || "512m",
    "--cpus", options.cpus || "1.0",
    "--pids-limit", String(options.pids || 128),
    "-v", `${work}:/work`,
    "-w", "/work",
  ];
  for (const [k, v] of Object.entries(options.env || {})) args.push("-e", `${k}=${v}`);
  args.push(image, ...cmd);

  const timeoutMs = options.timeoutMs ?? 60000;
  const r = spawnSync(dockerBin, args, { encoding: "utf8", timeout: timeoutMs });
  const out = cap(r.stdout || "");
  const err = cap(r.stderr || "");
  return {
    image,
    work,
    exit: r.status,
    signal: r.signal || null,
    timedOut: r.error && r.error.code === "ETIMEDOUT",
    stdout: out.text,
    stdoutTruncated: out.truncated,
    stderr: err.text,
    stderrTruncated: err.truncated,
  };
}

function parseArgs(argv) {
  const out = { cmd: argv[2] || "", pos: [], flags: {} };
  for (let i = 3; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--image") out.flags.image = argv[++i];
    else if (a === "--timeout") out.flags.timeoutMs = Number(argv[++i]);
    else if (a === "--net") out.flags.network = argv[++i];
    else if (a === "--memory") out.flags.memory = argv[++i];
    else if (a === "--cpus") out.flags.cpus = argv[++i];
    else if (a === "--") out.pos.push(...argv.slice(i + 1)), (i = argv.length);
    else if (!a.startsWith("--")) out.pos.push(a);
  }
  return out;
}

if (process.argv[1] && path.resolve(process.argv[1]) === new URL(import.meta.url).pathname) {
  const { cmd, pos, flags } = parseArgs(process.argv);
  try {
    if (cmd === "probe") {
      const p = probeDocker();
      console.log(p.ok ? `docker ok (server ${p.server})` : "NO_DOCKER");
      process.exit(p.ok ? 0 : 1);
    } else if (cmd === "run") {
      if (!pos.length) throw new Error("run needs -- <cmd>");
      const r = runSandbox(pos, flags);
      if (r.stdout) process.stdout.write(r.stdout);
      if (r.stderr) process.stderr.write(r.stderr);
      console.error(`[exit=${r.exit} signal=${r.signal} timedOut=${r.timedOut} work=${r.work}]`);
      process.exit(r.timedOut ? 124 : (r.exit ?? 1));
    } else {
      console.error("usage: sandbox.mjs <probe|run> ...");
      process.exit(2);
    }
  } catch (e) {
    console.error(`${e.name || "Error"}[${e.code || "?"}]: ${e.message}`);
    process.exit(1);
  }
}
