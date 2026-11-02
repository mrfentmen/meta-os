// H-FP4 / HN4-2 dispatch card: the receipt view shows the dispatch
// package fields when the incident carries them — picture attached,
// dispatch mode auto, receipt id, SIMULATED label — and never guesses
// a picture or mode the record does not carry.
// Fixture fields are the R5-imperium record on main:
// os-build/logs/R5-imperium/package-sent.json (dispatch_mode auto,
// picture.frame / picture.evidence_crop) and receipt.txt
// (receipt_id sim-6623d237a90b3d9d).
// Run: node --test tests/surfaces-dispatch-card.test.mjs

import test from "node:test";
import assert from "node:assert/strict";

import { receiptView } from "../js/surfaces.js";

const PACKAGE = {
  dispatch_mode: "auto",
  picture: {
    frame: "evidence/incident-27e9cfbd46e8078d/flag-frame-cam-a-d0966c.jpg",
    evidence_crop: "evidence/incident-27e9cfbd46e8078d/face-crop-cam-a-283674.jpg",
  },
};

test("dispatch card with the package shows picture, auto mode, receipt, SIMULATED", () => {
  const html = receiptView({ receipt_id: "sim-6623d237a90b3d9d", package: PACKAGE });
  assert.match(html, /Dispatch \(SIMULATED\)/);
  assert.match(html, /receipt sim-6623d237a90b3d9d/);
  assert.match(html, /Picture attached: flagged frame \+ evidence crop/);
  assert.match(html, /dispatch mode auto/);
  assert.match(html, /post-hoc audit/);
  assert.match(html, /no real service contacted/i);
});

test("picture references are named, never printed as paths", () => {
  const html = receiptView({ receipt_id: "sim-6623d237a90b3d9d", package: PACKAGE });
  assert.doesNotMatch(html, /flag-frame-cam-a-d0966c/);
  assert.doesNotMatch(html, /face-crop-cam-a-283674/);
});

test("frame without a crop names only the frame", () => {
  const html = receiptView({
    receipt_id: "sim-abc123",
    package: { dispatch_mode: "auto", picture: { frame: "evidence/x.jpg", evidence_crop: null } },
  });
  assert.match(html, /Picture attached: flagged frame/);
  assert.doesNotMatch(html, /evidence crop/);
});

test("no package data means no picture or mode line, receipt alone", () => {
  const html = receiptView({ receipt_id: "sim-abc123" });
  assert.match(html, /receipt sim-abc123/);
  assert.doesNotMatch(html, /Picture attached/);
  assert.doesNotMatch(html, /dispatch mode auto/);
  assert.doesNotMatch(html, /post-hoc audit/);
});

test("a non-auto mode claims no auto flow", () => {
  const html = receiptView({
    receipt_id: "sim-abc123",
    dispatch_mode: "held-for-verify",
    picture: { frame: "evidence/x.jpg" },
  });
  assert.match(html, /Picture attached: flagged frame/);
  assert.doesNotMatch(html, /dispatch mode auto/);
  assert.doesNotMatch(html, /no human verify step/);
  assert.doesNotMatch(html, /post-hoc audit/);
});

test("empty picture references claim no picture", () => {
  const html = receiptView({
    receipt_id: "sim-abc123",
    package: { dispatch_mode: "auto", picture: { frame: "", evidence_crop: "" } },
  });
  assert.doesNotMatch(html, /Picture attached/);
});
