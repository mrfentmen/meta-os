// Node built-in test runner, no dependencies:  node --test tests/face-apps.test.mjs
// Covers the light-lane face apps: Notes, Calendar, Files, Calculator and
// Settings are one self-contained HTML file each (no build step, no external
// resource), they persist under their own browser keys, and the shell dock
// opens all five as face windows instead of host binaries.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (name) => readFileSync(new URL(`../os-build/face/${name}`, import.meta.url), "utf8");

const apps = {
  "notes.html": read("notes.html"),
  "calendar.html": read("calendar.html"),
  "files.html": read("files.html"),
  "calculator.html": read("calculator.html"),
  "settings.html": read("settings.html"),
};
const shell = read("shell.html");

test("all five face apps exist and carry real markup", () => {
  for (const [name, html] of Object.entries(apps)) {
    assert.ok(html.length > 500, `${name} must be a real app, not a stub`);
    assert.match(html, /<html lang="en"/, `${name} must declare its language`);
    assert.match(html, /<title>/, `${name} must have a title`);
  }
});

test("every app is self-contained: no external resource and no import", () => {
  for (const [name, html] of Object.entries(apps)) {
    assert.doesNotMatch(html, /https?:\/\//, `${name} must not reference an external URL`);
    assert.doesNotMatch(html, /<script[^>]+\bsrc=/i, `${name} must not load an external script`);
    assert.doesNotMatch(html, /<link[^>]+rel=["']?stylesheet/i, `${name} must not load an external stylesheet`);
    assert.doesNotMatch(html, /(^|\n)\s*import\s/, `${name} must not use module imports`);
  }
});

test("no app uses eval", () => {
  for (const [name, html] of Object.entries(apps)) {
    assert.equal(html.includes("eval("), false, `${name} must not use eval()`);
  }
});

test("every app has an ARIA live region or a labelled control", () => {
  for (const [name, html] of Object.entries(apps)) {
    assert.match(html, /aria-live="polite"|aria-label="/, `${name} needs an accessible surface`);
  }
});

test("apps persist under their own browser keys", () => {
  assert.ok(apps["notes.html"].includes("metaos-notes"), "Notes key");
  assert.ok(apps["calendar.html"].includes("metaos-calendar"), "Calendar key");
  assert.ok(apps["settings.html"].includes("metaos-settings"), "Settings key");
  assert.ok(apps["files.html"].includes("metaos-"), "Files lists the metaos- records");
});

test("Files is honest: real records, honest empty state, no sample data", () => {
  const html = apps["files.html"];
  assert.match(html, /No browser-local records yet/);
  assert.match(html, /not on disk/);
  assert.match(html, /localStorage\.key\(i\)/);
  assert.doesNotMatch(html, /lorem ipsum|sample file|example\.txt/i);
});

test("Calculator keeps its keypad, keyboard support and live display", () => {
  const html = apps["calculator.html"];
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /addEventListener\('keydown'/);
  assert.match(html, /data-k="="/);
  assert.equal(html.includes("eval("), false);
});

test("shell dock opens all five apps as face windows on their own files", () => {
  const expected = {
    Notes: "notes.html",
    Calendar: "calendar.html",
    Files: "files.html",
    Calculator: "calculator.html",
    Settings: "settings.html",
  };
  for (const [name, target] of Object.entries(expected)) {
    const line = new RegExp(
      `\\{ id: "[^"]+",\\s*icon: "[^"]*",\\s*name: "${name}",\\s*kind: "([^"]+)",\\s*target: "([^"]+)"`,
    );
    const match = shell.match(line);
    assert.ok(match, `shell must have a dock entry for ${name}`);
    assert.equal(match[1], "url", `${name} must render in a face window`);
    assert.equal(match[2], target, `${name} must point at ${target}`);
  }
});
