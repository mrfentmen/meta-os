// CB2-463/464 — Musica catalogue data, read as data only.
//
// The catalogue files are written by os/worlds/musica/runtime/catalogue.py
// from the take log. Key and tempo live on the take record (take_log.jsonl,
// params.key / params.tempo); the catalogue carries the published track. So
// the test joins the two by take_id rather than inventing fields on the
// catalogue that the studio never writes.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { validateCatalogue } from "../os/worlds/musica/catalogue_validate.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const STUDIO = path.join(ROOT, "os/worlds/musica");
const CATALOGUES = path.join(STUDIO, "gate-packet/catalogues");
const SESSIONS = path.join(STUDIO, "sessions");

const catalogueFiles = fs.readdirSync(CATALOGUES).filter((f) => f.endsWith(".json"));
const catalogues = catalogueFiles.map((f) => ({
  file: f,
  data: JSON.parse(fs.readFileSync(path.join(CATALOGUES, f), "utf8")),
}));

function takeLogFor(sessionId) {
  const file = path.join(SESSIONS, sessionId, "take_log.jsonl");
  if (!fs.existsSync(file)) return [];
  return fs.readFileSync(file, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l));
}

test("CB2-463 every published track carries a title, a duration, and a key and tempo from its take", () => {
  assert.ok(catalogues.length >= 2, "read the real catalogues");
  let checked = 0;
  for (const { file, data } of catalogues) {
    const takes = new Map(takeLogFor(data.session_id).map((t) => [t.take_id, t]));
    assert.ok(data.tracks.length > 0, file + " has tracks");
    for (const track of data.tracks) {
      assert.equal(typeof track.title, "string", file + " " + track.take_id + " title");
      assert.notEqual(track.title.trim(), "", file + " " + track.take_id + " title is not blank");
      assert.equal(typeof track.duration_s, "number", file + " " + track.take_id + " duration");
      assert.ok(track.duration_s > 0, file + " " + track.take_id + " duration is positive");

      const take = takes.get(track.take_id);
      assert.ok(take, file + " track " + track.take_id + " has a take record");
      assert.equal(typeof take.params.key, "string", track.take_id + " key is a string");
      assert.equal(typeof take.params.tempo, "number", track.take_id + " tempo is a number");
      assert.ok(take.params.tempo > 0, track.take_id + " tempo is positive");
      checked += 1;
    }
  }
  assert.ok(checked >= 10, "checked every published track: " + checked);
});

test("CB2-463b the real catalogues pass the validator with zero errors", () => {
  for (const { file, data } of catalogues) {
    assert.deepEqual(validateCatalogue(data), [], file + " is clean");
  }
});

test("CB2-464 duplicate take ids are detected, naming both indexes", () => {
  const dup = {
    session_id: "fixture-dup",
    tracks: [
      { take_id: "take-001", title: "One", duration_s: 4.0, licence: "own" },
      { take_id: "take-001", title: "One again", duration_s: 4.0, licence: "own" },
    ],
  };
  const errors = validateCatalogue(dup);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /tracks\[1\]\.take_id: duplicate id "take-001" \(first seen at tracks\[0\]\)/);
});

test("CB2-464b distinct take ids and a missing licence are reported separately", () => {
  const missing = {
    session_id: "fixture-licence",
    tracks: [{ take_id: "take-002", title: "Two", duration_s: 2.5 }],
  };
  const errors = validateCatalogue(missing);
  assert.deepEqual(errors, ["catalogue.tracks[0].licence: must be a non-empty string"]);
});
