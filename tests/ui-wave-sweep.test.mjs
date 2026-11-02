// Node built-in test runner, no dependencies:  node --test tests/ui-wave-sweep.test.mjs
// Covers HN-020 (79-control sweep re-run): the sweep doc covers
// every static control in the live UI, names the audit-only items
// as REMOVED, and says plainly that Pax's UI_AUDIT.md is NOT on
// this VM — so the doc is checked against the live UI, not
// against an audit file nobody here can read.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const sweep = readFileSync(new URL("../docs/UI_CONTROL_SWEEP.md", import.meta.url), "utf8");

test("sweep covers every static control in the live UI", () => {
  const buttons = (html.match(/<button/g) || []).length;
  const inputs = (html.match(/<input/g) || []).length;
  const selects = (html.match(/<select/g) || []).length;
  assert.equal(buttons + inputs + selects, 51, `expected 51 static controls, found ${buttons + inputs + selects}`);
  // Id-carrying controls must each be named in the sweep.
  const ids = new Set();
  for (const m of html.matchAll(/<(button|input|select)[^>]*\bid="([^"]+)"/g)) {
    ids.add(m[2]);
  }
  const missing = [...ids].filter((id) => !sweep.includes(id));
  assert.deepEqual(missing, [], `controls missing from the sweep: ${missing.join(", ")}`);
  // Id-less controls are covered as groups: product chips, mode
  // buttons, and the product radios. (The logo swatch group went
  // with the LOGO-1 color controls, removed 2026-11-01.)
  for (const group of ["cmd-product-chip", "cmd-mode-btn", "product radio"]) {
    assert.ok(sweep.includes(group), `sweep must cover ${group}`);
  }
});

test("sweep names the audit-only items as REMOVED with reasons", () => {
  for (const item of [
    "Brief me now", "Post N jobs", "Alert Acknowledge", "Alert Resolve",
    "#intel-plan", "Credential-form first screen", "muse-relay title",
  ]) {
    assert.ok(sweep.includes(item), `sweep must name ${item}`);
  }
  assert.match(sweep, /## REMOVED — audit items absent from this repo's UI \(8\)/);
  assert.match(sweep, /Dead count in this repo's live UI: 0\./);
});

test("sweep states its method limit honestly", () => {
  assert.match(sweep, /Pax's `UI_AUDIT\.md` is NOT on this VM/);
  assert.match(sweep, /cannot be re-verified 1:1/);
  assert.match(sweep, /51 static controls: 35 buttons \+ 14 inputs \+ 2 selects/);
  assert.match(sweep, /27 native disclosures/);
  assert.match(sweep, /6 dynamic control templates/);
});

test("dynamic templates and disclosures are in the sweep", () => {
  for (const item of [
    "cmd-cam-row", "cmd-alert-track", "cmd-kresult", "cmd-tile",
    "createMarkerElement", "About this panel", "Full session statistics",
  ]) {
    assert.ok(sweep.includes(item), `sweep must cover ${item}`);
  }
});
