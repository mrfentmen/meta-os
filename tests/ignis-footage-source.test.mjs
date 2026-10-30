// Node built-in test runner, no dependencies:
//   node --test tests/ignis-footage-source.test.mjs
//
// IGNIS-ONEOFONE-9 (Del's one-of-one bar, Oct 29): the Ignis
// footage-source breakdown counts recorded ok Ignis assessments by
// the input source the app itself stamped on each entry at submit
// time — live-camera, still-image, or recorded-video. Real state
// only: failures contribute nothing, other products move no bucket,
// entries with no usable source count in the total and in unknown,
// and an empty or held session reads all zeros rather than inventing
// a footage mix. The source stamp itself lives in js/log.js
// (record() stores it) and js/app.js (each submit path passes the
// source it genuinely knows). No contract, server, or Spark-gate
// change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisFootageSource } from "../js/ignis-footage-source.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const log = readFileSync(new URL("../js/log.js", import.meta.url), "utf8");

const entryWithSource = (source) => ({
  status: "ok",
  product: "ignis",
  source,
});

test("footage source: an empty session reads all zeros", () => {
  assert.deepEqual(ignisFootageSource([]), {
    total: 0,
    liveCamera: 0,
    stillImage: 0,
    recordedVideo: 0,
    unknown: 0,
  });
  assert.deepEqual(ignisFootageSource(null), {
    total: 0,
    liveCamera: 0,
    stillImage: 0,
    recordedVideo: 0,
    unknown: 0,
  });
  assert.deepEqual(ignisFootageSource(undefined), {
    total: 0,
    liveCamera: 0,
    stillImage: 0,
    recordedVideo: 0,
    unknown: 0,
  });
});

test("footage source: buckets follow the source stamped on each entry", () => {
  const counts = ignisFootageSource([
    entryWithSource("live-camera"),
    entryWithSource("live-camera"),
    entryWithSource("still-image"),
    entryWithSource("recorded-video"),
    entryWithSource("recorded-video"),
    entryWithSource("recorded-video"),
    entryWithSource(null),
    entryWithSource(undefined),
    entryWithSource(""),
    entryWithSource(42),
    { status: "ok", product: "ignis" },
    null,
  ]);
  assert.deepEqual(counts, {
    total: 11,
    liveCamera: 2,
    stillImage: 1,
    recordedVideo: 3,
    unknown: 5,
  });
});

test("footage source: failed and other-product entries move no bucket", () => {
  const counts = ignisFootageSource([
    { status: "network_error", product: "ignis", source: "recorded-video" },
    { status: "http_error", product: "ignis", source: "live-camera" },
    { status: "ok", product: "vigiles", source: "recorded-video" },
    { status: "ok", product: "medicus", source: "still-image" },
    null,
    entryWithSource("recorded-video"),
  ]);
  assert.deepEqual(counts, {
    total: 1,
    liveCamera: 0,
    stillImage: 0,
    recordedVideo: 1,
    unknown: 0,
  });
});

test("footage source: panel exists in HTML, hidden except under Ignis, wired in app.js, source stamped in log.js", () => {
  assert.ok(html.includes('id="ignis-footage-source"'));
  assert.ok(html.includes("ignis-footage-source-panel"));
  assert.ok(css.includes(".ignis-footage-source-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-footage-source-panel'));
  assert.ok(app.includes("ignisFootageSource"));
  assert.ok(app.includes("els.ignisFootageSource.textContent"));
  assert.ok(app.includes('"live-camera"'));
  assert.ok(app.includes('"still-image"'));
  assert.ok(app.includes('"recorded-video"'));
  assert.ok(log.includes("source"));
});
