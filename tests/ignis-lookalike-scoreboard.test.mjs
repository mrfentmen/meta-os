// Node built-in test runner, no dependencies:
//   node --test tests/ignis-lookalike-scoreboard.test.mjs
//
// IGNIS-ONEOFONE-1 (Del's one-of-one bar, Oct 29): the Ignis
// look-alike scoreboard counts recorded Ignis assessments by their
// returned category — look-alike classes against hazard classes.
// Real state only: failures contribute nothing, other products move
// no bucket, and an empty or held session reads all zeros rather
// than inventing a reading. No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisLookAlikeScoreboard } from "../js/ignis-scoreboard.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const ok = (product, category) => ({
  status: "ok",
  product,
  response: { assessment: { category } },
});

const zero = {
  total: 0,
  visibleSmoke: 0,
  visibleFlame: 0,
  steamOrFog: 0,
  flameLikeLighting: 0,
  obscuredOrDistant: 0,
  noHazard: 0,
  indeterminate: 0,
};

test("scoreboard: an empty session reads all zeros", () => {
  assert.deepEqual(ignisLookAlikeScoreboard([]), zero);
  assert.deepEqual(ignisLookAlikeScoreboard(null), zero);
  assert.deepEqual(ignisLookAlikeScoreboard(undefined), zero);
});

test("scoreboard: every contract category lands in its own bucket", () => {
  const counts = ignisLookAlikeScoreboard([
    ok("ignis", "visible smoke"),
    ok("ignis", "visible smoke"),
    ok("ignis", "visible flame"),
    ok("ignis", "steam or fog"),
    ok("ignis", "steam or fog"),
    ok("ignis", "steam or fog"),
    ok("ignis", "flame-like lighting"),
    ok("ignis", "obscured or distant hazard"),
    ok("ignis", "no hazard visible"),
    ok("ignis", "indeterminate"),
  ]);
  assert.equal(counts.total, 10);
  assert.equal(counts.visibleSmoke, 2);
  assert.equal(counts.visibleFlame, 1);
  assert.equal(counts.steamOrFog, 3);
  assert.equal(counts.flameLikeLighting, 1);
  assert.equal(counts.obscuredOrDistant, 1);
  assert.equal(counts.noHazard, 1);
  assert.equal(counts.indeterminate, 1);
});

test("scoreboard: failures and other products move no bucket", () => {
  const counts = ignisLookAlikeScoreboard([
    ok("ignis", "visible smoke"),
    { status: "network_error", product: "ignis", error: "down" },
    { status: "http_error", product: "ignis", error: "500" },
    ok("vigiles", "visible smoke"),
    ok("sanitas", "steam or fog"),
    { status: "ok", product: "vigiles", response: { assessment: { category: "visible flame" } } },
  ]);
  assert.deepEqual(counts, { ...zero, total: 1, visibleSmoke: 1 });
});

test("scoreboard: an unrecognized or missing category counts in the total only", () => {
  const counts = ignisLookAlikeScoreboard([
    ok("ignis", "visible flame"),
    ok("ignis", "dust cloud"),
    { status: "ok", product: "ignis", response: null },
    { status: "ok", product: "ignis" },
    { status: "ok", product: null, response: { assessment: { category: "visible smoke" } } },
    null,
    "not an entry",
  ]);
  assert.equal(counts.total, 4);
  assert.equal(counts.visibleFlame, 1);
  assert.equal(counts.visibleSmoke, 0);
  assert.equal(counts.steamOrFog, 0);
});

test("web: the scoreboard panel exists with its static zeros line", () => {
  assert.match(
    html,
    /<section class="panel ignis-scoreboard-panel" aria-label="Ignis look-alike scoreboard">/,
  );
  assert.match(html, /<p id="ignis-scoreboard" class="note mono">/);
  assert.match(
    html,
    /Look-alikes — Steam or fog 0 · Flame-like lighting 0 \| Hazards — Visible smoke 0 · Visible flame 0 \| Other — Obscured or distant hazard 0 · No hazard visible 0 · Indeterminate 0/,
  );
  assert.match(html, /Supplementary awareness only — never a primary-detection or code status/);
});

test("web: the scoreboard panel shows only under Ignis", () => {
  assert.match(css, /\.ignis-scoreboard-panel \{\s+display: none;\s+\}/);
  assert.match(
    css,
    /body\[data-product="ignis"\] \.ignis-scoreboard-panel \{\s+display: block;\s+\}/,
  );
  assert.doesNotMatch(css, /body\[data-product="vigiles"\] \.ignis-scoreboard-panel/);
  assert.doesNotMatch(css, /body\[data-product="sanitas"\] \.ignis-scoreboard-panel/);
  // Scoped to the scoreboard block: OPS-CONSOLE-6 follows it with
  // Vigiles' own console pass (same direction, Vigiles lane), which
  // legitimately carries Vigiles blue and is not a scoreboard color.
  const block = css.slice(
    css.indexOf("/* IGNIS-ONEOFONE-1"),
    css.indexOf("/* OPS-CONSOLE-6"),
  );
  assert.doesNotMatch(block, /#5da864/, "no Sanitas green in the scoreboard block");
  assert.doesNotMatch(block, /#4f7ec2/, "no Vigiles blue in the scoreboard block");
});

test("web: app.js renders the scoreboard from log entries inside updateLogStats", () => {
  assert.match(app, /import \{ ignisLookAlikeScoreboard \} from "\.\/ignis-scoreboard\.js";/);
  assert.match(app, /ignisScoreboard: \$\("ignis-scoreboard"\),/);
  const body = app.slice(
    app.indexOf("function updateLogStats()"),
    app.indexOf("function updateHistoryEmpty()"),
  );
  assert.match(body, /ignisLookAlikeScoreboard\(log\.entries\(\)\)/);
  assert.match(
    body,
    /Look-alikes — Steam or fog \$\{scoreboard\.steamOrFog\} · Flame-like lighting \$\{scoreboard\.flameLikeLighting\} \| Hazards — Visible smoke \$\{scoreboard\.visibleSmoke\} · Visible flame \$\{scoreboard\.visibleFlame\} \| Other — Obscured or distant hazard \$\{scoreboard\.obscuredOrDistant\} · No hazard visible \$\{scoreboard\.noHazard\} · Indeterminate \$\{scoreboard\.indeterminate\}/,
  );
});
