// Node built-in test runner, no dependencies:
//   node --test tests/native-sampler-queued-tick.test.mjs
//
// Native sampler queued-tick parity. The native sampler's timer fires a
// Task onto the main actor, so a Stop or Reset Session can land after
// the timer fired but before the queued Task runs. stop() invalidates
// the timer, but it cannot recall a Task already created — and without
// a guard that Task would run a sample against a camera Reset just
// stopped, so runSample's capture-failure path would repaint the
// timeline and the status bar Reset had just cleared, with a failure
// for a sample that never should have run. tick() therefore stands
// down when the sampler is no longer running, before counting anything.
// The web sampler needs no equivalent: its interval callback calls
// tick() synchronously, so there is no queued Task a Stop or Reset can
// land behind. Swift cannot run in this sandbox, so the guard is
// asserted from source, in the same style as the other native tests.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const sampler = readFileSync(
  new URL("../native/Sources/MetaTrio/Services/FrameSampler.swift", import.meta.url),
  "utf8",
);
const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);
const webSampler = readFileSync(
  new URL("../js/sampler.js", import.meta.url),
  "utf8",
);

const tickBody = sampler.slice(
  sampler.indexOf("func tick() async {"),
  sampler.indexOf("func tick() async {") === -1
    ? undefined
    : sampler.length,
);
const stopBody = sampler.slice(
  sampler.indexOf("func stop() {"),
  sampler.indexOf("func setInterval("),
);

test("native: the timer fires each tick as a queued main-actor Task", () => {
  assert.match(
    sampler,
    /Task \{ @MainActor in\s*await self\.tick\(\)/,
  );
});

test("native: tick() stands down when the sampler is no longer running, before counting", () => {
  const guardAt = tickBody.indexOf("guard isRunning else { return }");
  assert.notEqual(guardAt, -1, "tick() is missing its isRunning guard");
  const countAt = tickBody.indexOf("tickCount += 1");
  assert.ok(
    guardAt < countAt,
    "the isRunning guard must come before the tick is counted, so a cancelled tick counts as nothing",
  );
});

test("native: stop() invalidates the timer, which is what makes the guard fire", () => {
  assert.match(stopBody, /timer\?\.invalidate\(\)/);
  assert.match(stopBody, /timer = nil/);
});

test("native: Reset Session stops analysis, and stopping analysis stops the sampler", () => {
  const resetBody = model.slice(
    model.indexOf("func resetSession() {"),
    model.indexOf("// MARK: - Backend health check"),
  );
  assert.match(resetBody, /stopAnalysis\(\)/);
  const stopAnalysisBody = model.slice(
    model.indexOf("func stopAnalysis() {"),
    model.indexOf("/// Stops capture and clears"),
  );
  assert.match(stopAnalysisBody, /sampler\.stop\(\)/);
});

test("web: the interval callback calls tick() synchronously, so no queued-Task guard is needed there", () => {
  assert.match(
    webSampler,
    /_setIntervalFn\(\(\) => \{\s*\/\/ tick\(\) never rejects.*\n\s*void this\.tick\(\);/,
  );
  assert.doesNotMatch(webSampler, /Task \{/);
});
