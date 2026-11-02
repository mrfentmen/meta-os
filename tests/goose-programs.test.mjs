// The four shallowest services, given a regression test each (E2).
//
// "Shallow" was measured, not guessed: services/*/*.goose by line count puts hello (3),
// heartbeat (19), echo (22) and mcp-host (61) at the bottom. Each is a real program, so
// the useful depth is a test that runs it and asserts the behaviour its header promises:
// hello prints, echo answers a line, heartbeat stops on the STOP sentinel, mcp-host answers
// JSON and logs the request. No new features were added to make the tests pass.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const GOOSE = process.env.GOOSE || "goose";

function goose(src, input, cwd) {
  const r = spawnSync(GOOSE, ["run", path.join(ROOT, src)], {
    input, cwd: cwd || ROOT, encoding: "utf8", timeout: 60000,
  });
  if (r.error && r.error.code === "ENOENT") return null;   // no toolchain on this machine
  return r;
}

function assertRan(r, label) {
  assert.ok(r, "goose toolchain missing");
  assert.equal(r.status, 0, label + " exited " + r.status + ": " + (r.stderr || "").slice(0, 400));
}

test("hello prints its one line", { timeout: 90000 }, (t) => {
  const r = goose("services/hello/hello.goose", "");
  if (!r) return t.skip("goose not on PATH");
  assertRan(r, "hello");
  assert.match(r.stdout, /HELLO FROM GOOSE/);
});

test("echo answers the line it was given", { timeout: 90000 }, (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "goose-echo-"));
  const r = goose("services/echo/echo.goose", "hello from node\n", dir);
  if (!r) return t.skip("goose not on PATH");
  assertRan(r, "echo");
  assert.match(r.stdout, /echo: hello from node/);
});

test("heartbeat stops cleanly on the STOP sentinel and beats zero times", { timeout: 90000 }, (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "goose-heartbeat-"));
  fs.writeFileSync(path.join(dir, "STOP"), "");
  const r = goose("services/heartbeat/heartbeat.goose", "", dir);
  if (!r) return t.skip("goose not on PATH");
  assertRan(r, "heartbeat");
  assert.match(r.stdout, /daemon stopping cleanly/);
  // The sentinel is checked before the first beat: a STOP already filed must win the race.
  assert.equal(fs.existsSync(path.join(dir, "heartbeat.log")), false);
});

test("mcp-host answers list and echo, and logs both requests", { timeout: 90000 }, (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "goose-host-"));
  const input = '{"tool":"list"}\n{"tool":"echo","args":{"text":"hi"}}\n';
  const r = goose("services/mcp-host/host.goose", input, dir);
  if (!r) return t.skip("goose not on PATH");
  assertRan(r, "mcp-host");
  assert.match(r.stdout, /\{"ok":true,"tools":\["echo"\]\}/);
  assert.match(r.stdout, /\{"ok":true,"result":"hi"\}/);
  const log = fs.readFileSync(path.join(dir, "host.log"), "utf8");
  assert.match(log, /"tool":"list"/);
  assert.match(log, /"tool":"echo"/);
});
