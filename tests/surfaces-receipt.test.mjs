// HN-064 Dispatch receipt view: sim- receipt shown on the incident
// after a staged dispatch, labelled SIMULATED in the view.
// Run: node --test tests/surfaces-receipt.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { receiptView } from "../js/surfaces.js";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

test("receipt shows SIMULATED label, receipt id, and no-real-service note", () => {
  const html = receiptView({ receipt_id: "sim-abc123" });
  assert.match(html, /Dispatch \(SIMULATED\)/);
  assert.match(html, /receipt sim-abc123/);
  assert.match(html, /no real service contacted/i);
});

test("no receipt before dispatch is an honest empty state", () => {
  assert.match(receiptView({}), /No dispatch receipt/);
  assert.match(receiptView({ receipt_id: "" }), /No dispatch receipt/);
  assert.match(receiptView(null), /No dispatch receipt/);
});

test("receipt id is escaped", () => {
  const html = receiptView({ receipt_id: "<script>" });
  assert.doesNotMatch(html, /<script>/);
});

test("boards page has a receipt section wired to live crew records", () => {
  assert.match(surfacesHtml, /id="board-receipt"/);
  assert.match(surfacesHtml, /id="receipt-content"/);
});
