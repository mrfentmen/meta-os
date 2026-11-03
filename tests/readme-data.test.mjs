import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const DIR = join(HERE, "..", "docs", "readme-data");
const REQUIRED = ["name", "purpose", "status", "proof", "limits", "notes"];
const STATUSES = new Set(["VERIFIED", "CODE-INSPECTED", "UNIMPLEMENTED", "BLOCKED"]);

const files = readdirSync(DIR).filter((name) => name.endsWith(".json")).sort();
const records = files.map((file) => ({
  file,
  data: JSON.parse(readFileSync(join(DIR, file), "utf8")),
}));

test("every readme-data file parses and carries exactly the six keys", () => {
  assert.ok(files.length >= 16, `expected at least 16 files, got ${files.length}`);
  for (const { file, data } of records) {
    assert.equal(typeof data, "object", file);
    assert.deepEqual(Object.keys(data).sort(), [...REQUIRED].sort(), file);
    for (const key of REQUIRED) {
      assert.equal(typeof data[key], "string", `${file}: ${key}`);
      assert.ok(data[key].trim().length > 0, `${file}: ${key} is empty`);
    }
  }
});

test("every status is one of the four documented values", () => {
  for (const { file, data } of records) {
    assert.ok(STATUSES.has(data.status), `${file}: ${data.status}`);
  }
});

test("no data file presents Custos as a current system", () => {
  for (const { file, data } of records) {
    assert.ok(!JSON.stringify(data).includes("Custos"), file);
  }
});

test("the kernel and live-cams entries exist", () => {
  assert.ok(files.includes("kernel.json"));
  assert.ok(files.includes("live-cams.json"));
});

test("program names are unique across the directory", () => {
  const names = records.map(({ data }) => data.name);
  assert.equal(new Set(names).size, names.length, names.join(", "));
});
