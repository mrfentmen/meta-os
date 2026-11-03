// CB2-473/474 — Musica normalisation as a pure data transform.
//
// runtime/normalize.py normalises rendered audio. The one pure piece that
// can be checked without rendering is the text transform the catalogue
// applies to a title before publishing. The real catalogue titles are the
// fixture: a title the studio already published must pass through
// unchanged, which is the idempotence the transform promises.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { normalizeTitle } from "../os/worlds/musica/catalogue_validate.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const CATALOGUES = path.join(ROOT, "os/worlds/musica/gate-packet/catalogues");

const titles = fs.readdirSync(CATALOGUES)
  .filter((f) => f.endsWith(".json"))
  .flatMap((f) => JSON.parse(fs.readFileSync(path.join(CATALOGUES, f), "utf8")).tracks)
  .map((t) => t.title);

test("CB2-473 messy metadata is normalised: trimmed, single-spaced, title-cased", () => {
  assert.equal(normalizeTitle("  dark   ride "), "Dark Ride");
  assert.equal(normalizeTitle("night\tbus"), "Night Bus");
  assert.equal(normalizeTitle("already Normal"), "Already Normal");
});

test("CB2-473b normalisation is idempotent on every published title", () => {
  assert.ok(titles.length >= 10, "read the real catalogue titles: " + titles.length);
  for (const title of titles) {
    const once = normalizeTitle(title);
    assert.equal(normalizeTitle(once), once, title + " is unchanged on a second pass");
    assert.equal(once, once.trim(), title + " has no edge whitespace");
    assert.doesNotMatch(once, /\s{2,}/, title + " has no double spaces");
  }
});

test("CB2-474 an already-normal entry is unchanged", () => {
  const normal = { title: "Dark Ride", brief_id: "chipsynth", duration_s: 7.273 };
  const copy = { ...normal, title: normalizeTitle(normal.title) };
  assert.deepEqual(copy, normal, "a normal entry survives the transform untouched");
});

test("CB2-474b a non-string title is refused by name, never coerced", () => {
  assert.throws(() => normalizeTitle(42), /title: must be a string/);
  assert.throws(() => normalizeTitle(null), /title: must be a string/);
});
