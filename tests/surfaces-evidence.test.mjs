// HN-059 Evidence viewer: flagged-only crops + ID: UNIDENTIFIED card.
// Run: node --test tests/surfaces-evidence.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { evidenceViewer } from "../js/surfaces.js";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

test("flagged incident with evidence shows crops and the UNIDENTIFIED card, no name", () => {
  const html = evidenceViewer({
    status: "flagged",
    evidence: { files: 3, frames: 2, face_crops: 1 },
    evidence_purged: false,
  });
  assert.match(html, /ID: UNIDENTIFIED/);
  assert.match(html, /3 evidence files/);
  assert.match(html, /2 flagged\/investigation frames/);
  assert.match(html, /1 face crops/);
  assert.doesNotMatch(html, /person_name|full_name|>Name</);
});

test("purged incident shows the purge, never stale counts", () => {
  const html = evidenceViewer({
    status: "flagged",
    evidence: { files: 3, frames: 2, face_crops: 1 },
    evidence_purged: true,
  });
  assert.match(html, /Evidence purged/);
  assert.doesNotMatch(html, /3 evidence files/);
});

test("unflagged incident shows crops are flagged-only", () => {
  const html = evidenceViewer({ status: "open", evidence: null, evidence_purged: false });
  assert.match(html, /only on flagged events/);
  assert.doesNotMatch(html, /evidence files/);
});

test("flagged incident with no evidence says so plainly", () => {
  const html = evidenceViewer({ status: "flagged", evidence: null, evidence_purged: false });
  assert.match(html, /No evidence recorded for this incident/);
});

test("boards page has an evidence section wired to live crew records", () => {
  assert.match(surfacesHtml, /id="board-evidence"/);
  assert.match(surfacesHtml, /id="evidence-content"/);
  assert.match(surfacesHtml, /\/api\/crew\/status/);
});
