// CB2-418..419 — the dock, read as data, against the repo it points into.
//
// Every dock entry must name an app that exists, and every system window must
// cite real files: a window that sends you to a path nobody wrote is a broken
// desktop, not a design choice. The six systems are the ones the rebuild keeps;
// Custos is retired and must not appear.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const faceJs = fs.readFileSync(path.join(ROOT, "face", "face.js"), "utf8");

const appsBlock = faceJs.slice(faceJs.indexOf("var APPS = {"), faceJs.indexOf("/* ---------- dock ---------- */"));
const appIds = [...appsBlock.matchAll(/^  ([a-z]+): \{/gm)].map((m) => m[1]);

const dockBlock = faceJs.slice(faceJs.indexOf("var DOCK = ["), faceJs.indexOf("DOCK.forEach"));
const dockIds = [...dockBlock.matchAll(/\["([a-z]+)",/g)].map((m) => m[1]);

const SYSTEMS = ["imperium", "musica", "science", "officina", "aegis", "nervus"];

// The window body for one app, from its key to the next key at the same depth.
function appBlock(id, nextId) {
  const start = appsBlock.indexOf("  " + id + ": {");
  assert.ok(start > 0, "app exists: " + id);
  const end = appsBlock.indexOf("  " + nextId + ": {", start);
  return end > start ? appsBlock.slice(start, end) : appsBlock.slice(start);
}

test("CB2-418 every dock entry names an app that exists", () => {
  assert.ok(appIds.length >= 16, "the app table grew with the systems");
  assert.ok(dockIds.length >= 16, "the dock grew with the systems");
  for (const id of dockIds) assert.ok(appIds.includes(id), "dock id has an app: " + id);
  // No duplicates: a doubled entry would open the same window twice from two slots.
  assert.equal(new Set(dockIds).size, dockIds.length, "no repeated dock id");
});

test("CB2-419 all six systems are dockable, Custos is not", () => {
  for (const id of SYSTEMS) {
    assert.ok(appIds.includes(id), "system app exists: " + id);
    assert.ok(dockIds.includes(id), "system is on the dock: " + id);
  }
  assert.equal(dockIds.includes("custos"), false, "Custos is retired, not a current system");
  assert.equal(appIds.includes("custos"), false);
  assert.doesNotMatch(appsBlock, /Custos is a current system/i);
});

test("CB2-418 the three new system windows cite files that exist", () => {
  // Only the windows written for this section are path-checked here; the older
  // three are pinned by their own waves and are not rewritten to satisfy a test.
  const order = ["officina", "aegis", "nervus"];
  for (const id of order) {
    const block = appBlock(id, order[order.indexOf(id) + 1] || "calculator");
    const cited = [...new Set([...block.matchAll(/[\w./-]+\.(?:json|mjs|py|md)/g)].map((m) => m[0]))];
    assert.ok(cited.length >= 2, id + " cites its real files");
    for (const rel of cited) {
      assert.ok(fs.existsSync(path.join(ROOT, rel)), id + " cites a real path: " + rel);
    }
  }
});
