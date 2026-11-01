// Tests for the Command view's loop feed formatting (js/command-loop.js)
// and its wiring: the panel exists in index.html, the glue polls the
// crew status endpoint, and the CSS sits in the additive command
// layer. The formatters render only what the agent crew recorded
// (server/queue/crew_records.py via GET /api/crew/status) — including
// the loud states: feed errors, budget pauses, endpoint silence.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { flagTier, loopEventText, loopFeedItems, loopIncidentItems, loopIncidentText, loopStatusText } from "../js/command-loop.js";

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

test("flag tiers follow the ruling lists, baselines and unknowns get none", () => {
  assert.equal(flagTier("vigiles", "energetic movement"), "yellow");
  assert.equal(flagTier("vigiles", "staged verbal dispute"), "yellow");
  assert.equal(flagTier("vigiles", "person down"), "red");
  assert.equal(flagTier("ignis", "visible smoke"), "yellow");
  assert.equal(flagTier("ignis", "cooking oil fire indicators"), "yellow");
  assert.equal(flagTier("ignis", "structure fire"), "red");
  assert.equal(flagTier("ignis", "dark smoke"), "red");
  assert.equal(flagTier("medicus", "bystander aid in progress"), "yellow");
  assert.equal(flagTier("medicus", "blood visible at scene"), "red");
  assert.equal(flagTier("vigiles", "normal activity"), null);
  assert.equal(flagTier("ignis", "no hazard visible"), null);
  assert.equal(flagTier("medicus", "indeterminate"), null);
  assert.equal(flagTier("vigiles", "something unlisted"), null);
  assert.equal(flagTier("unknown-division", "person down"), null);
});

test("incident lines surface BOLO marks, evidence counts, and the tier", () => {
  const line = loopIncidentText({
    camera_name: "1 Ave @ 84 St", division: "vigiles", category: "person down",
    status: "dispatched-simulated",
    bolo: { visible_marks: ["tattoo on left forearm"], person_descriptions: ["a person on the ground"], direction_note: "Not determined from still frames." },
    evidence: { files: 3, frames: 2, face_crops: 1 }, evidence_purged: false,
  });
  assert.match(line, /Incident — 1 Ave @ 84 St · Vigiles: person down \(dispatched-simulated\)/);
  assert.match(line, /RED — full flag chain/);
  assert.match(line, /BOLO: tattoo on left forearm/);
  assert.match(line, /1 person description/);
  assert.match(line, /evidence: 3 files \(2 frames, 1 face crops\)/);
  // Face crops are a count only — no image, no identity language.
  assert.doesNotMatch(line, /<img|data:image|identified as|matched to/);
  const yellow = loopIncidentText({
    camera_name: "2 Ave @ 10 St", division: "vigiles", category: "energetic movement",
    status: "reported", bolo: null, evidence: null, evidence_purged: false,
  });
  assert.match(yellow, /YELLOW — recorded for human review, no investigation, no dispatch/);
  assert.doesNotMatch(yellow, /BOLO|evidence:/);
  const purged = loopIncidentText({
    camera_name: "3 Ave @ 20 St", division: "medicus", category: "crowd gathered around a person",
    status: "cleared-by-review", bolo: null, evidence: null, evidence_purged: true,
  });
  assert.match(purged, /YELLOW/);
  assert.match(purged, /evidence files purged on false-positive close/);
  const items = loopIncidentItems({ incidents: [
    { camera_name: "X", division: "ignis", category: "visible smoke", status: "reported" },
    null,
  ] });
  assert.equal(items.length, 1);
  assert.equal(items[0].type, "incident");
  assert.equal(items[0].tier, "yellow");
});

test("loop feed panel is wired: markup, honest copy, polling glue, CSS", () => {
  assert.ok(html.includes('id="cmd-loop-status"'), "status line element exists");
  assert.ok(html.includes('id="cmd-loop-feed"'), "feed list element exists");
  assert.ok(html.includes("Dispatch from this system is SIMULATED"), "panel copy labels dispatch simulated");
  assert.ok(html.includes("no real emergency service is ever contacted"), "panel copy states the boundary");
  assert.ok(commandJs.includes("loopFeedItems("), "glue renders via the pure formatters");
  assert.ok(commandJs.includes("loopIncidentItems("), "glue renders incidents via the pure formatters");
  assert.ok(css.includes(".cmd-loop-item--incident-yellow"), "yellow-tier incident rows are styled distinctly");
  assert.ok(commandJs.includes("loopStatusText("), "glue renders the status line via the pure formatter");
  assert.ok(commandJs.includes('fetch("/api/crew/status"'), "glue polls the crew status endpoint");
  assert.ok(commandJs.includes("setInterval(refreshLoopFeed, 5000)"), "poll interval is wired");
  assert.ok(commandJs.includes('$("cmd-loop-status")') || commandJs.includes('"cmd-loop-status"'), "glue queries the status element");
  assert.ok(commandJs.includes('$("cmd-loop-feed")') || commandJs.includes('"cmd-loop-feed"'), "glue queries the feed element");
  const layer = css.slice(css.indexOf("/* COMMAND VIEW v2"), css.indexOf("/* OPS-CONSOLE-1"));
  assert.ok(layer.includes(".cmd-loop-feed"), "loop feed styles live in the additive command layer");
  assert.ok(layer.includes(".cmd-loop-item--dispatch"), "dispatch rows are styled distinctly");
});
