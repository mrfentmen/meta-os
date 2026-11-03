// Aegis secret-pattern counts (CB2-371..372).
//
// Counts and categories only. A fixture string exists so the scanner
// has something to find; the assertion is always HOW MANY hits of which
// pattern id, and -- CB2-372 -- that the fixture value survives nowhere
// in the serialised report. Never assert a match's text.
import assert from "node:assert/strict";
import test from "node:test";

import { PATTERNS, scanText } from "../aegis/secrets.mjs";

// Shaped like real credentials but built at runtime from harmless
// pieces, so this file itself is not a hit for the scanner it tests.
const FIXTURES = {
  "aws-access-key-id": "AKIA" + "Q".repeat(16),
  "github-token": "ghp" + "_" + "a".repeat(36),
  "slack-token": "xox" + "b-1234567890abcdef",
  "stripe-live-key": "sk" + `_live_${"a".repeat(20)}`,
  "private-key-block": "-----BEGIN " + "RSA PRIVATE KEY-----",
  "jwt":
    "eyJ" + "a".repeat(12) + "." + "b".repeat(12) + "." + "c".repeat(12),
  "assigned-secret": 'api_key = "' + "z".repeat(24) + '"',
};

const countsOf = (hits) => {
  const counts = {};
  for (const hit of hits) counts[hit.id] = (counts[hit.id] || 0) + 1;
  return counts;
};

test("every documented pattern id has a fixture with a known count", () => {
  for (const pattern of PATTERNS) {
    assert.ok(
      Object.hasOwn(FIXTURES, pattern.id),
      `no fixture for pattern ${pattern.id}`
    );
  }
});

test("one fixture line yields exactly one hit of its own pattern", () => {
  for (const [id, fixture] of Object.entries(FIXTURES)) {
    const hits = scanText(fixture);
    assert.equal(hits.length, 1, `${id} fixture count`);
    assert.equal(hits[0].id, id);
    assert.equal(hits[0].line, 1);
  }
});

test("a three-line file counts one hit per offending line only", () => {
  const text = [
    "const greeting = 'hello';",
    FIXTURES["github-token"],
    FIXTURES["github-token"],
  ].join("\n");
  const hits = scanText(text);
  assert.equal(hits.length, 2);
  assert.deepEqual(
    hits.map((h) => h.line),
    [2, 3]
  );
});

test("confidence labels stay separate: confirmed vs review", () => {
  const text = [FIXTURES["aws-access-key-id"], FIXTURES["assigned-secret"]].join(
    "\n"
  );
  const counts = countsOf(scanText(text));
  assert.deepEqual(counts, {
    "aws-access-key-id": 1,
    "assigned-secret": 1,
  });
  const labels = new Map(PATTERNS.map((p) => [p.id, p.confidence]));
  assert.equal(labels.get("aws-access-key-id"), "confirmed");
  assert.equal(labels.get("assigned-secret"), "review");
});

test("clean text has zero hits", () => {
  assert.deepEqual(scanText("nothing to see here\njust prose"), []);
});

test("allowlisted hits are counted and marked, not dropped", () => {
  const hits = scanText(`example: ${FIXTURES["slack-token"]}`, {
    allow: () => true,
  });
  assert.equal(hits.length, 1);
  assert.equal(hits[0].allowlisted, true);
});

// CB2-372: the report is counts and categories only. Serialise it and
// prove no fixture value appears anywhere in the output.
test("serialised report contains no fixture secret string", () => {
  const text = Object.values(FIXTURES).join("\n");
  const report = {
    scanned: 1,
    hits: scanText(text).map((hit) => ({
      id: hit.id,
      confidence: hit.confidence,
      path: hit.path,
      line: hit.line,
      allowlisted: hit.allowlisted || false,
    })),
    counts: countsOf(scanText(text)),
  };
  const serialised = JSON.stringify(report);
  for (const [id, fixture] of Object.entries(FIXTURES)) {
    assert.equal(
      serialised.includes(fixture),
      false,
      `${id} value leaked into the report`
    );
  }
  // And the report still says what was found.
  assert.equal(report.hits.length, Object.keys(FIXTURES).length);
  for (const id of Object.keys(FIXTURES)) {
    assert.equal(report.counts[id], 1, id);
  }
});
