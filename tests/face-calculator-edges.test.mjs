// CB2-406..408 — calculator rules, tested against face/logic.mjs.
//
// These are the rules the Calculator window follows, not a copy of them: the
// window imports the same functions. The calculator is sequential, so 2 + 3 * 4
// is 20 — the pending operator applies when the next one is pressed.
import test from "node:test";
import assert from "node:assert/strict";
import { calcKey, initialCalc } from "../face/logic.mjs";

function type(keys, state = initialCalc()) {
  return keys.reduce((s, k) => calcKey(s, k), state);
}
const display = (keys) => type(keys).cur;

test("CB2-406 division by zero shows Error; chained operations apply as they are pressed", () => {
  assert.equal(display(["8", "/", "0", "="]), "Error", "8 / 0 is refused, not Infinity");
  // Before = the fresh entry is shown, which is the 0 just typed: the operator
  // does not apply until the next operator or =, and the display says so.
  assert.equal(display(["8", "/", "0"]), "0");

  // Sequential, not algebraic: 2 + 3 * 4 = 20.
  assert.equal(display(["2", "+", "3", "*", "4", "="]), "20");
  // 2 + 3 = 5, then minus 8 = -3.
  assert.equal(display(["2", "+", "3", "-", "8", "="]), "-3");

  // Clear returns the window to its opening state, whatever came before.
  assert.deepEqual(type(["9", "*", "9", "C"]), initialCalc());
  assert.equal(display(["9", "*", "9", "Escape"]), "0");

  // Backspace on a single digit is 0, never an empty display.
  assert.equal(display(["7", "Backspace"]), "0");
  assert.equal(display(["1", "2", "3", "Backspace"]), "12");

  // Pressing = with no pending operator changes nothing.
  assert.equal(display(["4", "2", "="]), "42");
});

test("CB2-407 a second decimal point in one number is ignored", () => {
  assert.equal(display(["1", ".", "2", ".", "3"]), "1.23", "the second dot is dropped, the digits are not");
  assert.equal(display(["1", ".", ".", "5"]), "1.5");
  assert.equal(display([".", "5"]), "0.5", "a leading dot starts 0.");
  assert.equal(display([".", ".", "5"]), "0.5");
  // After an operator the entry is fresh, so a new number may use a dot again.
  assert.equal(display(["1", ".", "5", "+", ".", "5", "="]), "2");
});

test("CB2-408 the 15-digit display is the raw number, pinned", () => {
  // Entering fifteen digits keeps every one of them.
  const fifteen = "123456789012345";
  assert.equal(fifteen.length, 15);
  assert.equal(display([...fifteen]), fifteen);

  // A sum that stays 15 digits is exact and shows in full.
  assert.equal(display([...fifteen, "+", "0", "="]), fifteen);

  // Past 15 exact digits the browser's own String() is the format: no rounding
  // for display, no thousands separators, no exponent until JavaScript picks one.
  assert.equal(display([...fifteen, "*", "1", "0", "="]), "1234567890123450");
  assert.equal(display(["9", "9", "9", "9", "9", "9", "9", "9", "9", "9", "9", "9", "9", "9", "9", "9", "*", "1", "0", "="]), "100000000000000000");

  // A result that JavaScript renders in exponent form is shown as Is, not padded.
  assert.equal(display(["1", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "*", "1", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "="]), "1e+29");

  // Small decimals keep full precision too: 0.1 + 0.2 is not silently tidied.
  assert.equal(display(["0", ".", "1", "+", "0", ".", "2", "="]), "0.30000000000000004");
});
