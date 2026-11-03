// CB2-415..417 — the face terminal's command table, tested against logic.mjs.
//
// The Terminal window prints what this table returns, so a command the test
// refuses is a command the shell cannot answer.
import test from "node:test";
import assert from "node:assert/strict";
import { TERMINAL_HELP, terminalAnswer } from "../face/logic.mjs";

test("CB2-415 the parser knows status, help, uptime, mem, ps and refuses anything else", () => {
  assert.deepEqual(terminalAnswer("help").lines, ["commands: status help uptime mem ps"]);
  assert.deepEqual(terminalAnswer("status").lines, ["STATUS tasks 7 heap_total 512K milestone K6"]);
  assert.deepEqual(terminalAnswer("uptime").lines, ["uptime 141s ticks 14100"]);
  assert.deepEqual(terminalAnswer("mem").lines, ["mem frames_free 118784 heap_total 512K"]);
  assert.deepEqual(terminalAnswer("ps").lines, [
    "ps id 1 state running (kernel)",
    "ps id 4 state sleeping (sleeper)",
    "ps id 7 state running (console)",
    "ps id 8 state held (readkey - spawn held until its boot proof)",
  ]);

  // An unknown word is answered, not ignored: it says so and reprints the list.
  for (const unknown of ["ls", "cat README.txt", "reboot"]) {
    const res = terminalAnswer(unknown);
    assert.deepEqual(res.lines, ["unknown command", TERMINAL_HELP], unknown + " is refused");
    assert.equal(res.clear, false);
  }

  // Commands are case- and space-insensitive, because a shell is.
  assert.deepEqual(terminalAnswer("  STATUS  ").lines, terminalAnswer("status").lines);
});

test("CB2-416 clear clears the window and is not listed in help", () => {
  const res = terminalAnswer("clear");
  assert.equal(res.clear, true, "the window wipes its output");
  assert.deepEqual(res.lines, [], "clear prints nothing of its own");

  // The help list is exactly five words, and clear is not one of them.
  const listed = TERMINAL_HELP.replace(/^commands:\s*/, "").split(/\s+/);
  assert.deepEqual(listed, ["status", "help", "uptime", "mem", "ps"]);
  assert.equal(listed.includes("clear"), false, "clear works but stays unlisted");
  assert.equal(TERMINAL_HELP.includes("clear"), false);
});

test("CB2-417 extra whitespace and empty input are a no-op, not an error", () => {
  for (const empty of ["", "   ", "\t", "\n", "  \n\t "]) {
    const res = terminalAnswer(empty);
    assert.deepEqual(res.lines, [], "nothing is printed for " + JSON.stringify(empty));
    assert.equal(res.clear, false, "and nothing is cleared");
  }

  // Extra inner whitespace is not a command either; only the ends are trimmed.
  assert.deepEqual(terminalAnswer("sta tus").lines[0], "unknown command");

  // A non-string is treated as an empty line rather than throwing at the window.
  assert.deepEqual(terminalAnswer(null).lines, []);
  assert.deepEqual(terminalAnswer(undefined).lines, []);
});
