// CB2-422 — settings rules, tested against face/logic.mjs.
//
// The Settings window writes through setSetting, so an unknown key the test
// refuses is a key the window cannot silently drop.
import test from "node:test";
import assert from "node:assert/strict";
import { SETTING_KEYS, setSetting } from "../face/logic.mjs";

const base = { mode: "dark", bar: "auto", speed: 25, paused: false, variant: "blue", bg: "default" };

test("CB2-422 a boolean toggle round-trips and an unknown key is refused", () => {
  const paused = setSetting(base, "paused", true);
  assert.equal(paused.paused, true);
  const running = setSetting(paused, "paused", false);
  assert.equal(running.paused, false);
  assert.deepEqual({ ...running, paused: true }, { ...base, paused: true }, "nothing else moved");

  // The caller's object is not mutated: settings is replaced, never edited.
  assert.equal(base.paused, false);

  // An unknown key is named, not ignored.
  assert.throws(() => setSetting(base, "theme", "dark"), /unknown key "theme"/);
  assert.throws(() => setSetting(base, "nope", 1), /unknown key "nope"/);

  // A known key with a value outside its set is refused the same way.
  assert.throws(() => setSetting(base, "mode", "purple"), /mode must be one of dark, light/);
  assert.throws(() => setSetting(base, "bar", "green"), /bar must be one of/);
  assert.throws(() => setSetting(base, "speed", 0), /speed must be a positive number/);
  assert.throws(() => setSetting(base, "speed", -5), /speed must be a positive number/);
  assert.throws(() => setSetting(base, "speed", NaN), /speed must be a positive number/);

  // Every documented key is writable, so the guard cannot block a real control.
  for (const key of SETTING_KEYS) {
    const value = { mode: "light", bar: "black", speed: 50, paused: true, variant: "ice", bg: "navy" }[key];
    assert.doesNotThrow(() => setSetting(base, key, value), key + " is a real setting");
  }
});
