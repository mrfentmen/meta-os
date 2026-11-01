// HN-067 Custos board: patrol records by tier/source from Rowan's
// real records format. The real-data assertions read the repo's
// actual patrol JSONLs.
// Run: node --test tests/surfaces-custos.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { parseCustosJsonl, custosBoard } from "../js/surfaces.js";
import { createAssessServer } from "../server/server.mjs";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");
const patrol1 = readFileSync(new URL("../os/worlds/custos/runs/patrol-001.jsonl", import.meta.url), "utf8");
const patrol2 = readFileSync(new URL("../os/worlds/custos/runs/patrol-002.jsonl", import.meta.url), "utf8");

test("parser reads the real patrol files, skipping malformed lines only", () => {
  const a = parseCustosJsonl(patrol1);
  const b = parseCustosJsonl(patrol2);
  assert.ok(a.records.length > 0);
  assert.ok(b.records.length > 0);
  const observations = [...a.records, ...b.records].filter((r) => r.record_type === "observation");
  assert.ok(observations.length > 0);
  for (const r of observations) {
    assert.equal(typeof r.tier, "string");
    assert.equal(typeof r.source, "string");
    assert.equal(typeof r.category, "string");
  }
  // Escalations and summaries ride the same files, untiered.
  const others = [...a.records, ...b.records].filter((r) => r.record_type !== "observation");
  assert.ok(others.some((r) => r.record_type === "escalation"));
  assert.ok(others.some((r) => r.record_type === "patrol-summary"));
});

test("board groups real records by tier and source", () => {
  const { records } = parseCustosJsonl(patrol1 + "\n" + patrol2);
  const html = custosBoard(records);
  assert.match(html, /By tier/);
  assert.match(html, /By source/);
  assert.match(html, /kev/);
  assert.match(html, /known-exploited vulnerability present/);
});

test("board with no records is an honest empty state", () => {
  assert.match(custosBoard([]), /No patrol records yet/);
});

test("server serves .jsonl as ndjson", async () => {
  const server = createAssessServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const base = `http://127.0.0.1:${server.address().port}`;
    const res = await fetch(`${base}/os/worlds/custos/runs/patrol-001.jsonl`);
    assert.equal(res.status, 200);
    assert.match(res.headers.get("content-type"), /ndjson/);
    const text = await res.text();
    assert.ok(text.includes("known-exploited vulnerability present"));
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("boards page has a custos section fetching the real patrol files", () => {
  assert.match(surfacesHtml, /id="board-custos"/);
  assert.match(surfacesHtml, /id="custos-content"/);
  assert.match(surfacesHtml, /os\/worlds\/custos\/runs\//);
});
