// Node built-in test runner, no dependencies:
//   node --test tests/native-health-check-reset.test.mjs
//
// Web <-> native health-check Reset parity. Reset Session clears the
// backend-health line ("Backend health not checked yet.") so a
// pre-reset check does not linger as if it were current — but a check
// outstanding across Reset used to repaint that cleared line when it
// settled, success or failure, with a result from before the reset.
// The assessment paths already guard their display updates against
// exactly this with the view generation; the health check did not.
// This test reads the sources (it cannot run Swift in this sandbox,
// and app.js needs a DOM) to assert both frontends capture the view
// generation when the check starts and apply its result text only
// when the generation is unchanged, while still re-enabling the
// check button in every case.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);
const web = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const webHealth = web.slice(
  web.indexOf('els.btnBackendCheck.addEventListener'),
  web.indexOf("// Initial state."),
);
const nativeHealth = model.slice(
  model.indexOf("func checkBackendHealth()"),
  model.indexOf("// MARK: - Still-image input"),
);
const nativeReset = model.slice(
  model.indexOf("func resetSession()"),
  model.indexOf("// MARK: - Backend health check"),
);
const webReset = web.slice(
  web.indexOf('els.btnReset.addEventListener'),
  web.indexOf('els.intervalSeconds.addEventListener'),
);

test("anchor: Reset clears the health line on both frontends, so a stale repaint would be visible", () => {
  assert.match(
    webReset,
    /els\.backendHealth\.textContent = "Backend health not checked yet\./,
  );
  assert.match(
    nativeReset,
    /backendHealth = "Backend health not checked yet\./,
  );
});

test("web: the health check captures the view generation and guards both result texts", () => {
  assert.match(webHealth, /const generation = viewGeneration;/);
  assert.match(
    webHealth,
    /if \(generation === viewGeneration\) \{\s*els\.backendHealth\.textContent =\s*`Backend reachable:/,
  );
  assert.match(
    webHealth,
    /if \(generation === viewGeneration\) \{\s*els\.backendHealth\.textContent = `Backend health check failed:/,
  );
});

test("web: a health check across Reset still re-enables its button", () => {
  assert.match(
    webHealth,
    /finally \{\s*backendChecking = false;\s*els\.btnBackendCheck\.disabled = false;/,
  );
});

test("native: the health check captures the view generation and applies its result only when unchanged", () => {
  assert.match(nativeHealth, /let requestGeneration = viewGeneration/);
  assert.match(
    nativeHealth,
    /if requestGeneration == viewGeneration \{\s*backendHealth = resultText\s*\}/,
  );
  assert.doesNotMatch(nativeHealth, /backendHealth =\s*"Backend reachable:/);
  assert.doesNotMatch(nativeHealth, /backendHealth = "Backend health check failed:/);
});

test("native: a health check across Reset still clears its checking flag", () => {
  assert.match(
    nativeHealth,
    /if requestGeneration == viewGeneration \{[\s\S]*?\}\s*healthChecking = false/,
  );
});
