// HN-061 BOLO card: exactly the BOLO key set, visible marks only,
// ID: UNIDENTIFIED, no name field exists — and none can leak through.
// Run: node --test tests/surfaces-bolo.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { boloCard, BOLO_KEYS } from "../js/surfaces.js";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

const STAGED_BOLO = {
  division: "vigiles",
  category: "possible altercation",
  camera_name: "cam-7",
  area: "north",
  flagged_at: "2026-11-01T08:00:00Z",
  frame_files: 3,
  face_crops: 1,
  person_descriptions: ["tall, dark coat"],
  visible_marks: ["tattoo on left forearm"],
  direction_of_travel: "north",
  direction_note: "on foot",
};

test("BOLO card renders exactly the BOLO key set, verbatim", () => {
  const html = boloCard(STAGED_BOLO);
  assert.match(html, /ID: UNIDENTIFIED/);
  for (const key of BOLO_KEYS) {
    assert.match(html, new RegExp(key), `missing key ${key}`);
  }
  assert.match(html, /tattoo on left forearm/);
  assert.match(html, /tall, dark coat/);
});

test("a name field passed in is dropped, never rendered", () => {
  const html = boloCard({ ...STAGED_BOLO, name: "Jane Doe", person_name: "Jane" });
  assert.doesNotMatch(html, /Jane Doe/);
  assert.doesNotMatch(html, /person_name/);
  assert.doesNotMatch(html, />name</);
});

test("no BOLO filed is an honest empty state", () => {
  assert.match(boloCard(null), /No BOLO filed/);
});

test("boards page has a BOLO section wired to live crew records", () => {
  assert.match(surfacesHtml, /id="board-bolo"/);
  assert.match(surfacesHtml, /id="bolo-content"/);
});
