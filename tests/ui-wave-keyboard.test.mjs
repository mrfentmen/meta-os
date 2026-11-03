// Node built-in test runner, no dependencies:  node --test tests/ui-wave-keyboard.test.mjs
// Covers HN-015 (keyboard map): the view's only keyboard features
// are the search three (Ctrl/Cmd+K, Esc, Enter — the only key
// handlers in js/command-map.js and js/app.js). Search gets a
// visible button so it is never keyboard-only, and a help overlay
// lists all three shortcuts with visible open/close controls.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../imperium/index.html", import.meta.url), "utf8");
const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

test("search and shortcuts are visible buttons, not keyboard-only", () => {
  assert.ok(html.includes('<button id="cmd-search-open" type="button">Search cameras</button>'));
  assert.ok(html.includes('<button id="cmd-help-open" type="button">Keyboard shortcuts</button>'));
  assert.ok(mapJs.includes('els.searchOpen.addEventListener("click", openSearch)'));
});

test("help overlay lists every keyboard shortcut in the view", () => {
  assert.ok(html.includes('<div id="cmd-help-overlay" class="cmd-search-overlay" hidden>'));
  assert.match(html, /<kbd>Ctrl<\/kbd> \+ <kbd>K<\/kbd> or <kbd>Cmd<\/kbd> \+ <kbd>K<\/kbd> — Open or close camera search/);
  assert.match(html, /<kbd>Esc<\/kbd> — Close search or this help/);
  assert.match(html, /<kbd>Enter<\/kbd> — In search, focus the top result/);
  assert.ok(html.includes('<button id="cmd-help-close" type="button">Close</button>'));
});

test("help overlay opens, focuses close, and closes by button, backdrop, and Esc", () => {
  assert.match(mapJs, /els\.helpOpen\.addEventListener\("click", \(\) => \{\n\s+state\.helpReturnFocus = rememberFocus\(\);\n\s+els\.helpOverlay\.hidden = false;\n\s+els\.helpClose\.focus\(\);/);
  assert.ok(mapJs.includes('if (els.helpClose) els.helpClose.addEventListener("click", closeHelp);'));
  assert.ok(mapJs.includes("if (event.target === els.helpOverlay) closeHelp();"));
  assert.match(mapJs, /event\.key === "Escape" && els\.helpOverlay && !els\.helpOverlay\.hidden/);
  assert.ok(css.includes(".cmd-help-list kbd {"));
});
