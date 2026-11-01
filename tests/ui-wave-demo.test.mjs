// Node built-in test runner, no dependencies:  node --test tests/ui-wave-demo.test.mjs
// Covers HN-022 (demo-mode banner): ?demo=1 shows a persistent
// "demo data" marker; anything else stays live. Demo mode was
// inert before this task — no ?demo handling existed anywhere —
// so the banner is the whole feature, and the exact-flag rule is
// the guard against demo data silently mixing with live data.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { isDemoMode } from "../js/demo.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");

test("only the exact flag ?demo=1 counts as demo mode", () => {
  assert.equal(isDemoMode("?demo=1"), true);
  assert.equal(isDemoMode("?demo=1&foo=bar"), true);
  assert.equal(isDemoMode("?demo=0"), false);
  assert.equal(isDemoMode("?demo"), false);
  assert.equal(isDemoMode(""), false);
  assert.equal(isDemoMode("?foo=1"), false);
  assert.equal(isDemoMode("not a query"), false);
});

test("banner markup is present, hidden, and announced", () => {
  assert.match(html, /<p id="demo-banner" class="demo-banner" role="status" hidden>/);
  assert.match(html, /Demo data — nothing here is live/);
});

test("banner is wired into init and styled sticky", () => {
  assert.ok(mapJs.includes('import { isDemoMode } from "./demo.js";'));
  assert.ok(mapJs.includes('demoBanner: $("demo-banner"),'));
  assert.ok(mapJs.includes("if (isDemoMode(window.location.search)) els.demoBanner.hidden = false;"));
  assert.match(css, /\.demo-banner \{\n\s+position: sticky;\n\s+top: 0;/);
  assert.match(css, /background: #c9a227;\n\s+color: #14161a;/);
});
