// Tests for the Command view's loop feed formatting (js/command-loop.js)
// and its wiring: the panel exists in index.html, the glue polls the
// crew status endpoint, and the CSS sits in the additive command
// layer. The formatters render only what the agent crew recorded
// (server/queue/crew_records.py via GET /api/crew/status) — including
// the loud states: feed errors, budget pauses, endpoint silence.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { loopEventText, loopFeedItems, loopStatusText } from "../js/command-loop.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const commandJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");

test("patrol check lines carry the real outcome", () => {
  assert.equal(
    loopEventText({ type: "patrol-check", camera_name: "1 Ave @ 84 St", division: "vigiles", outcome: "baseline", category: "normal activity" }),
    "Patrol — 1 Ave @ 84 St · Vigiles: normal activity (no flag)",
  );
  assert.equal(
    loopEventText({ type: "patrol-check", camera_name: "Bay Pkwy @ 78 St", division: "ignis", outcome: "flagged", category: "visible smoke" }),
    "Patrol — Bay Pkwy @ 78 St · Ignis: FLAGGED visible smoke",
  );
  assert.match(
    loopEventText({ type: "patrol-check", camera_name: "X", division: "medicus", outcome: "feed-error", error: "HTTP 404" }),
    /feed error \(HTTP 404\)/,
  );
  assert.match(
    loopEventText({ type: "patrol-check", camera_name: "X", division: "medicus", outcome: "assessment-failed", error: "no result" }),
    /assessment failed/,
  );
});

test("review verdicts read as verdicts: confirmed, cleared, inconclusive", () => {
  assert.match(loopEventText({ type: "review", camera_name: "X", verdict: "confirmed", category: "person down" }), /CONFIRMED the flag/);
  assert.match(loopEventText({ type: "review", camera_name: "X", verdict: "cleared", category: "normal activity" }), /CLEARED as a look-alike/);
  assert.match(loopEventText({ type: "review", camera_name: "X", verdict: "inconclusive" }), /inconclusive — flag stays for human review/);
});

test("incident, investigation, and dispatch lines — dispatch says SIMULATED", () => {
  assert.match(
    loopEventText({ type: "incident", camera_name: "X", division: "vigiles", category: "person down", priority: "high" }),
    /Incident REPORTED — X · Vigiles: person down \(high priority\)/,
  );
  assert.equal(
    loopEventText({ type: "investigation", camera_name: "X", calls: 5, flags_found: 1 }),
    "Investigation — X: 5 extra checks, 1 further flags",
  );
  const ok = loopEventText({ type: "dispatch", camera_name: "X", simulated: true, receipt_id: "sim-abc" });
  assert.match(ok, /Dispatch \(SIMULATED\)/);
  assert.match(ok, /no real service contacted/);
  assert.match(
    loopEventText({ type: "dispatch", camera_name: "X", simulated: true, error: "connection refused" }),
    /Dispatch \(SIMULATED\) — X: endpoint error/,
  );
});

test("orchestrator decisions render as decisions with their reason", () => {
  const line = loopEventText({
    type: "orchestrator", agent: "orchestrator", camera_name: "X", division: "ignis",
    decision: "investigate", actions: 1,
    reason: "flagged category is outside the ignis baseline set and no independent review has been recorded yet",
  });
  assert.match(line, /Orchestrator — X · Ignis: investigate \(1 actions\)/);
  assert.match(line, /no independent review/);
});

test("unknown event types are skipped, never rendered as guesses", () => {
  assert.equal(loopEventText({ type: "something-else" }), null);
  assert.equal(loopEventText(null), null);
  const items = loopFeedItems(
    { events: [{ type: "something-else", at: "t0" }, { type: "flag", camera_name: "X", division: "ignis", category: "visible flame", priority: "high", at: "t1" }] },
    12,
  );
  assert.equal(items.length, 1);
  assert.match(items[0].text, /Flag raised/);
});

test("status line: waiting, unreachable, never-ran, paused, running", () => {
  assert.match(loopStatusText(null), /waiting for the crew status endpoint/);
  assert.match(loopStatusText({ unreachable: true }), /UNAVAILABLE/);
  assert.match(loopStatusText({ available: false }), /no crew records yet/);
  assert.match(
    loopStatusText({
      available: true,
      patrol: { state: "paused-budget", camera_source: "nyctmc-live", counts: { checks: 9, reported: 1 } },
    }),
    /Patrol PAUSED \(budget\) — 9 checks, 1 reported · live NYCTMC list/,
  );
  assert.match(
    loopStatusText({
      available: true,
      patrol: { state: "running", camera_source: "fallback-subset", counts: { checks: 3, baseline: 2, reported: 0, feed_errors: 1 } },
    }),
    /Patrol running — 3 checks · 2 baseline · 0 reported · 1 feed errors · offline camera list/,
  );
});

test("loop feed panel is wired: markup, honest copy, polling glue, CSS", () => {
  assert.ok(html.includes('id="cmd-loop-status"'), "status line element exists");
  assert.ok(html.includes('id="cmd-loop-feed"'), "feed list element exists");
  assert.ok(html.includes("Dispatch from this system is SIMULATED"), "panel copy labels dispatch simulated");
  assert.ok(html.includes("no real emergency service is ever contacted"), "panel copy states the boundary");
  assert.ok(commandJs.includes("loopFeedItems("), "glue renders via the pure formatters");
  assert.ok(commandJs.includes("loopStatusText("), "glue renders the status line via the pure formatter");
  assert.ok(commandJs.includes('fetch("/api/crew/status"'), "glue polls the crew status endpoint");
  assert.ok(commandJs.includes("setInterval(refreshLoopFeed, 5000)"), "poll interval is wired");
  assert.ok(commandJs.includes('$("cmd-loop-status")') || commandJs.includes('"cmd-loop-status"'), "glue queries the status element");
  assert.ok(commandJs.includes('$("cmd-loop-feed")') || commandJs.includes('"cmd-loop-feed"'), "glue queries the feed element");
  const layer = css.slice(css.indexOf("/* COMMAND VIEW v2"), css.indexOf("/* OPS-CONSOLE-1"));
  assert.ok(layer.includes(".cmd-loop-feed"), "loop feed styles live in the additive command layer");
  assert.ok(layer.includes(".cmd-loop-item--dispatch"), "dispatch rows are styled distinctly");
});
