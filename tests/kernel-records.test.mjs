// CB2-405 — the kernel record the face quotes is a file, and it says what the
// face says it says.
//
// The held kernel-records file failed at the file level, so this is written
// against the current tree: the face cites os-build/logs/K7-boot.txt, and every
// line it prints as a record must be in that log. A quote without a source is
// how a demo becomes a claim.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const faceJs = fs.readFileSync(path.join(ROOT, "face", "face.js"), "utf8");
const LOG_REL = "os-build/logs/K7-boot.txt";
const log = fs.readFileSync(path.join(ROOT, LOG_REL), "utf8");
const lines = log.split("\n");

test("CB2-405 the boot log the face cites exists and carries its banner", () => {
  assert.ok(fs.existsSync(path.join(ROOT, LOG_REL)), LOG_REL + " is in the tree");
  assert.ok(faceJs.includes(LOG_REL), "the face cites the log it quotes");

  assert.ok(lines.some((l) => l.includes("META OS 0.1 (K6)")), "the banner line is in the log");
  assert.ok(lines.some((l) => l.includes("META OS KERNEL - alive (K1)")), "the alive line is in the log");
});

test("CB2-405 every record line the terminal prints appears in the log", () => {
  // The two lines the Terminal window prints as recorded fact.
  const printed = ["META OS 0.1 (K6)", "META OS KERNEL - alive (K1)"];
  for (const line of printed) {
    assert.ok(faceJs.includes('"' + line + '"'), "the face prints: " + line);
    assert.ok(log.includes(line), "and the log holds it: " + line);
  }

  // The userspace program the dashboard and About quote is in the same log.
  assert.ok(/HELLO FROM USERSPACE/.test(log), "userspace program line");
  assert.ok(/crasher/.test(log), "the isolated fault is on the record");
});

test("CB2-405 the log is text, not a rendered claim, and has no panic", () => {
  assert.ok(Buffer.byteLength(log, "utf8") > 200, "the log has real content");
  assert.ok(log.includes("\n"), "it is line-oriented text a reader can check");
  assert.equal(/panicked at|PANIC|kernel panic/i.test(log), false, "no panic in the recorded boot");
});
