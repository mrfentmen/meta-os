#!/usr/bin/env node
// CB-075 — totals model receipts by model. Costs are estimates; every line
// says so and unpriced receipts are counted, never guessed.
import fs from "node:fs";
import path from "node:path";

export function summarize(records) {
  const by = new Map();
  for (const rec of records) {
    const model = rec.model || "(missing model)";
    const row = by.get(model) || { model, receipts: 0, tokens: 0, latencyMs: 0, costEstimateUsd: 0, priced: 0, unpriced: 0 };
    row.receipts++;
    row.tokens += Number(rec.usage?.total_tokens) || 0;
    row.latencyMs += Number(rec.latency_ms) || 0;
    if (typeof rec.est_cost_usd === "number") {
      row.costEstimateUsd += rec.est_cost_usd;
      row.priced++;
    } else {
      row.unpriced++;
    }
    by.set(model, row);
  }
  const models = [...by.values()].map((r) => ({ ...r, avgLatencyMs: r.receipts ? Math.round(r.latencyMs / r.receipts) : 0 }));
  return {
    models,
    totalReceipts: models.reduce((n, r) => n + r.receipts, 0),
    totalTokens: models.reduce((n, r) => n + r.tokens, 0),
    unpriced: models.reduce((n, r) => n + r.unpriced, 0),
  };
}

export function readJsonl(file) {
  const out = [];
  if (!fs.existsSync(file)) return out;
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line.trim()) continue;
    try { out.push(JSON.parse(line)); } catch { /* torn line: skip */ }
  }
  return out;
}

export function readReceipts(targets) {
  const out = [];
  for (const target of targets) {
    if (fs.existsSync(target) && fs.statSync(target).isDirectory()) {
      for (const name of fs.readdirSync(target).filter((n) => n.endsWith(".jsonl")).sort()) {
        out.push(...readJsonl(path.join(target, name)));
      }
    } else {
      out.push(...readJsonl(target));
    }
  }
  return out;
}

export function main(argv) {
  const targets = argv.length ? argv : ["os-build/logs/wave3-model-proofs"];
  const summary = summarize(readReceipts(targets));
  console.log("receipts: " + summary.totalReceipts + ", tokens: " + summary.totalTokens);
  for (const row of summary.models) {
    console.log(
      "  " + row.model + ": " + row.receipts + " receipts, " + row.tokens + " tokens, avg " + row.avgLatencyMs +
      "ms, cost estimate $" + row.costEstimateUsd.toFixed(6) + " (" + row.priced + " priced, " + row.unpriced + " unpriced)",
    );
  }
  console.log("unpriced receipts: " + summary.unpriced);
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
