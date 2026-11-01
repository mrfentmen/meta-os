// HN-065 Cost ticker: calls spent + dollars spent from the ledger.
// Run: node --test tests/surfaces-cost.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { costTicker } from "../js/surfaces.js";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

test("ticker shows calls and dollars from the ledger state", () => {
  const html = costTicker({ calls: 4, est_cost_usd: 0.5, log: [] });
  assert.match(html, /4 calls spent/);
  assert.match(html, /\$0\.50 spent/);
});

test("missing ledger is a fresh ledger: 0 calls, $0.00", () => {
  assert.match(costTicker(null), /0 calls spent/);
  assert.match(costTicker(null), /\$0\.00 spent/);
  assert.match(costTicker({}), /0 calls spent/);
});

test("live ledger file in repo parses to the ticker shape", () => {
  const ledger = JSON.parse(readFileSync(new URL("../server/queue/spark_guardrail_state.json", import.meta.url), "utf8"));
  assert.equal(typeof ledger.calls, "number");
  assert.equal(typeof ledger.est_cost_usd, "number");
  assert.match(costTicker(ledger), new RegExp(`${ledger.calls} calls spent`));
});

test("boards page has a cost section refreshed on an interval", () => {
  assert.match(surfacesHtml, /id="board-costs"/);
  assert.match(surfacesHtml, /id="cost-content"/);
  assert.match(surfacesHtml, /spark_guardrail_state\.json/);
  assert.match(surfacesHtml, /setInterval\(refreshCosts, 15000\)/);
});
