// CB2-401..404 — the app surface of the reference desktop.
//
// The five held node files this section expected are not in the tree, so these
// are written against what the face does now rather than repaired against what
// it did then. Each case checks a fact a browser user would hit: an app opens,
// a window has the parts it needs, the login gate behaves, the dock lights up.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const faceJs = fs.readFileSync(path.join(ROOT, "face", "face.js"), "utf8");
const indexHtml = fs.readFileSync(path.join(ROOT, "face", "index.html"), "utf8");

const appsBlock = faceJs.slice(faceJs.indexOf("var APPS = {"), faceJs.indexOf("/* ---------- dock ---------- */"));
// The last entry closes the object (`  }` with no comma), so the terminator is optional.
const appEntries = [...appsBlock.matchAll(/^  ([a-z]+): \{([\s\S]*?)\n  \}[,]?/gm)].map((m) => [m[1], m[2]]);

test("CB2-401 every app declares a title and a build function", () => {
  assert.ok(appEntries.length >= 16, "read the whole APPS table: " + appEntries.length);
  for (const [id, body] of appEntries) {
    assert.match(body, /title: "[^"]+"/, id + " has a window title");
    assert.match(body, /build: function \(body\)/, id + " builds into the window body");
    // Files and Trash share one builder instead of writing their own markup.
    assert.match(body, /body\.innerHTML|buildFiles\(body/, id + " writes its own content");
  }
});

test("CB2-402 the window template carries the four parts openApp wires", () => {
  const templates = indexHtml.match(/<template id="win-template">/g) || [];
  assert.equal(templates.length, 1, "exactly one window template");

  const template = indexHtml.slice(indexHtml.indexOf('<template id="win-template">'));
  for (const part of ["win-bar", "win-title", "win-min", "win-close", "win-body"]) {
    assert.ok(template.includes('class="' + part), "template has ." + part);
  }

  // openApp clones that template, never builds a window from a string.
  assert.match(faceJs, /#win-template"\)\.content\.firstElementChild\.cloneNode\(true\)/);
  assert.match(faceJs, /win-title"\)\.textContent = def\.title/);
});

test("CB2-403 the login gate refuses an empty password and opens the desktop on any other", () => {
  assert.equal((indexHtml.match(/type="password"/g) || []).length, 1, "one password field");
  assert.match(faceJs, /if \(!pw\.value\) \{[\s\S]*?return; \}/, "empty input is refused before the desktop opens");
  assert.match(faceJs, /\$\("#login"\)\.hidden = true;/, "a non-empty password hides the gate");
  assert.match(faceJs, /\$\("#desktop"\)\.hidden = false;/);
  // The demo gate says it is a demo gate, in the page itself.
  assert.match(indexHtml, /Demo gate — any password enters/);
});

test("CB2-404 the dock lights only the apps that are open, and close clears it", () => {
  assert.match(faceJs, /d\.classList\.toggle\("running", !!openWins\[d\.dataset\.app\]\)/);
  assert.match(faceJs, /node\.remove\(\); delete openWins\[id\];/);
  assert.match(faceJs, /openWins\[id\] = node;/);
  // Closing and reopening is possible because the id is deleted, not just hidden.
  assert.equal((faceJs.match(/delete openWins\[/g) || []).length, 1, "one delete path");
});
