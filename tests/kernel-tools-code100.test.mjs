// CB-091..099 — kernel-adjacent tools. Read-only inputs; no kernel source edit.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";

import { parseSerial } from "../os-build/tools/serial_events.mjs";
import { diffGate } from "../os-build/tools/gate_diff.mjs";
import { checkClaims } from "../os-build/tools/claims_check.mjs";
import { parseAbi } from "../os-build/tools/abi_json.mjs";
import { validateFrames } from "../os-build/tools/frame_validate.mjs";
import { countSecrets } from "../os-build/tools/redact_check.mjs";
import { buildLogsManifest } from "../os-build/tools/logs_manifest.mjs";
import { checkManifest, demoLogRefs } from "../os-build/tools/demo_manifest_check.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "metaos-kernel-"));

test("CB-091/092 serial parser structures a log and makes panic first-class", () => {
  const text = fs.readFileSync(path.join(ROOT, "os-build/logs/K6-repro-main-2026-11-01.txt"), "utf8");
  const parsed = parseSerial(text);
  assert.equal(parsed.result, "OK");
  assert.equal(parsed.panic, false);
  assert.ok(parsed.events.some((e) => e.type === "alive"));
  assert.ok(parsed.events.some((e) => e.type === "exit" && e.code === 0));
  assert.ok(parsed.events.some((e) => e.type === "fault"));
  assert.ok(parsed.events.some((e) => e.type === "status" && e.tasks === 7));

  const panicked = parseSerial("META OS KERNEL - alive (K1)\nMETA OS KERNEL - panic\n");
  assert.equal(panicked.result, "PANIC");
  assert.equal(panicked.panic, true);
});

test("CB-093 gate differ lists stage and verdict changes", () => {
  const before = "== boot ==\nok K1\nFAIL K6\nGATE RED\n";
  const after = "== boot ==\nok K1\nok K6\nGATE GREEN\n";
  const diff = diffGate(before, after);
  assert.equal(diff.before, "RED");
  assert.equal(diff.after, "GREEN");
  assert.equal(diff.verdictChanged, true);
  assert.equal(diff.changes.length, 1);
  assert.deepEqual(diff.changes[0].after, { ok: 2, fail: 0, skip: 0 });
});

test("CB-094 claims checklist passes all six beats and names a missing one", () => {
  const all = [
    "META OS 0.1 (K6)", "META OS KERNEL - alive (K1)", "HELLO FROM USERSPACE",
    "user hello: entry 0x600000000000", "sleeper: before sleep", "crasher: about to read zero",
    "INT user page-fault", "sleeper: after sleep", "STATUS tasks=7",
    "user bad syscall 99 refused", "receipt_id=sim-6623d237a90b3d9d", "simulated=true",
  ].join("\n");
  assert.equal(checkClaims(all).allPass, true);
  const cut = checkClaims(all.replace("simulated=true", ""));
  assert.equal(cut.allPass, false);
  assert.deepEqual(cut.beats.find((b) => !b.pass).missing, ["simulated=true"]);
});

test("CB-095 ABI doc yields calls 0-5 and reserved 6-15", () => {
  const abi = parseAbi(fs.readFileSync(path.join(ROOT, "os-build/USERSPACE_ABI.md"), "utf8"));
  assert.equal(abi.calls.length, 6);
  assert.deepEqual(abi.calls.map((c) => c.name), ["exit", "write", "sleep", "pid", "yield", "read_key"]);
  assert.equal(abi.reserved.length, 10);
  assert.equal(abi.reserved[0].number, 6);
  assert.equal(abi.reserved[9].number, 15);
});

test("CB-096 every committed frame has the same dimensions", () => {
  const result = validateFrames(path.join(ROOT, "os-build/demo/frames"));
  assert.equal(result.ok, true);
  assert.equal(result.frames.length, 9);
  assert.deepEqual(result.dimensions, ["1280x720"]);
});

test("CB-097 redaction checker counts secrets and prints no value", () => {
  const secret = "sk-" + "a".repeat(32);
  const github = "ghp_" + "b".repeat(36);
  const result = countSecrets("first " + secret + " and " + github);
  assert.equal(result.total, 2);
  assert.equal(JSON.stringify(result).includes(secret), false);
});

test("CB-098 logs manifest carries file, size, sha256 and claim", () => {
  const dir = tmp();
  try {
    fs.writeFileSync(path.join(dir, "one.txt"), "one\n");
    fs.mkdirSync(path.join(dir, "sub"));
    fs.writeFileSync(path.join(dir, "sub", "two.txt"), "two\n");
    const index = path.join(dir, "INDEX.md");
    fs.writeFileSync(index, "| File | Lines | Marker | Note |\n|---|---:|---|---|\n| `one.txt` | 1 | x | the first log |\n");
    const manifest = buildLogsManifest(dir, index);
    const one = manifest.files.find((f) => f.file === "one.txt");
    assert.equal(one.size, 4);
    assert.match(one.sha256, /^[0-9a-f]{64}$/);
    assert.equal(one.claim, "the first log");
    assert.ok(manifest.files.some((f) => f.file === "sub/two.txt"));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("CB-099 every demo log reference exists in the real manifest", () => {
  const refs = demoLogRefs(fs.readFileSync(path.join(ROOT, "os-build/DEMO_SCRIPT.md"), "utf8"));
  assert.ok(refs.includes("K6-boot.txt"));
  assert.ok(refs.includes("R5-soak-final.txt"));
  assert.ok(refs.includes("R5-imperium/receipt.txt"));
  const manifest = buildLogsManifest(path.join(ROOT, "os-build/logs"), path.join(ROOT, "os-build/BOOT_LOG_INDEX.md"));
  const result = checkManifest(refs, manifest);
  assert.deepEqual(result.missing, []);
});
