// CB2-500 — every program has its README data file, and no data file is orphaned.
//
// The program list is declared in agents/registry.json under `programs`; the
// data files are the ones in docs/readme-data. Kernel, live-cams and face are
// pages of their own rather than programs, so they are named here once instead
// of being smuggled into the program list.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const DATA_DIR = path.join(ROOT, "docs", "readme-data");
const EXTRAS = ["kernel", "live-cams", "face"];

const registry = JSON.parse(fs.readFileSync(path.join(ROOT, "agents", "registry.json"), "utf8"));
const files = fs.readdirSync(DATA_DIR).filter((f) => f.endsWith(".json")).map((f) => f.slice(0, -5));

test("CB2-500 the registry declares the program list", () => {
  assert.ok(Array.isArray(registry.programs), "agents/registry.json carries a programs list");
  assert.ok(registry.programs.length >= 10, "the list is the real set: " + registry.programs.length);
  assert.equal(new Set(registry.programs).size, registry.programs.length, "no program is listed twice");
  for (const id of registry.programs) assert.match(id, /^[a-z0-9-]+$/, "program id is a slug: " + id);
});

test("CB2-500 every program has a data file and every data file is accounted for", () => {
  const expected = [...registry.programs, ...EXTRAS].sort();
  assert.deepEqual(files.sort(), expected, "the data directory is exactly the program list plus its three pages");
});

test("CB2-500 no page is missing its own record", () => {
  for (const id of [...registry.programs, ...EXTRAS]) {
    const record = JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + ".json"), "utf8"));
    assert.ok(record.name && record.status, id + " names itself and its status");
  }
});
