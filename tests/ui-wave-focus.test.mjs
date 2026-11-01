// Node built-in test runner, no dependencies:  node --test tests/ui-wave-focus.test.mjs
// Covers HN-019 (focus order): the keyboard walk follows DOM
// order, which matches visual order in this view — topbar, left
// rail, right rail, wall, pin card, then the overlays (which take
// focus on open and return it on close). No positive tabindex
// exists anywhere, so nothing jumps the order. Traps found and
// fixed: search close stranded focus (now returns it), the pin
// card never took focus on open (now focuses Close and returns
// focus on close), and the help overlay now returns focus too.
// No browser runs here, so these are static checks on the
// shipped wiring; the walk itself is recorded in docs/UI_FIX_REPORT.md.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const appJs = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

test("no positive tabindex anywhere in the view", () => {
  for (const [name, src] of [["index.html", html], ["command-map.js", mapJs], ["app.js", appJs]]) {
    const hits = [...src.matchAll(/tabindex="([^"]*)"/g)].filter((m) => Number(m[1]) > 0);
    assert.deepEqual(hits, [], `${name} must not reorder tab flow`);
  }
});

test("search takes focus on open and returns it on close", () => {
  assert.match(mapJs, /function openSearch\(\) \{\n\s+state\.searchReturnFocus = rememberFocus\(\);/);
  assert.match(mapJs, /els\.ksearch\.focus\(\);/);
  assert.match(mapJs, /function closeSearch\(\) \{\n\s+els\.overlay\.hidden = true;\n\s+restoreFocus\(state\.searchReturnFocus\);/);
});

test("pin card takes focus on open and returns it on close", () => {
  assert.match(mapJs, /state\.pinReturnFocus = rememberFocus\(\);/);
  assert.match(mapJs, /els\.pinCardClose\.focus\(\);/);
  assert.match(mapJs, /els\.pinCardClose\.addEventListener\("click", \(\) => \{\n\s+els\.pinCard\.hidden = true;\n\s+restoreFocus\(state\.pinReturnFocus\);/);
});

test("help overlay returns focus on every close path", () => {
  assert.match(mapJs, /state\.helpReturnFocus = rememberFocus\(\);/);
  assert.match(mapJs, /function closeHelp\(\) \{\n\s+els\.helpOverlay\.hidden = true;\n\s+restoreFocus\(state\.helpReturnFocus\);/);
  assert.ok(mapJs.includes('if (els.helpClose) els.helpClose.addEventListener("click", closeHelp);'));
  assert.ok(mapJs.includes("if (event.target === els.helpOverlay) closeHelp();"));
  assert.ok(mapJs.includes("closeHelp();"));
});

test("focus helpers guard against detached elements", () => {
  assert.match(mapJs, /function rememberFocus\(\) \{\n\s+const el = document\.activeElement;\n\s+return el instanceof Element \? el : null;\n\}/);
  assert.match(mapJs, /function restoreFocus\(el\) \{\n\s+if \(el && el\.isConnected && typeof el\.focus === "function"\) el\.focus\(\);/);
});
