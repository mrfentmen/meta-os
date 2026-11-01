// Surfaces boards (HN-056…HN-070): pure renderers for the boards page.
// Every renderer takes data and returns an HTML string; nothing here
// fetches, guesses, or invents records. A board with no records renders
// an honest empty state, never a placeholder row. All text is escaped.

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// HN-056 Lab board: experiments list reading the lab's records.
// Rule (V3): no level is EVER shown higher than the record's cap. When
// a record claims a level above its cap, the board shows the cap value
// with a "(capped)" marker and never prints the higher number anywhere.
export function labBoard(records) {
  const rows = Array.isArray(records) ? records : [];
  if (rows.length === 0) {
    return `<p class="empty-state">No lab experiments recorded yet.</p>`;
  }
  const items = rows.map((r) => {
    const level = Number(r?.ladder_level);
    const cap = Number(r?.cap);
    const shown = Number.isFinite(level) && Number.isFinite(cap)
      ? Math.min(level, cap)
      : (Number.isFinite(level) ? level : null);
    const capped = Number.isFinite(level) && Number.isFinite(cap) && level > cap;
    const levelText = shown === null ? "—" : `Level ${shown}${capped ? " (capped)" : ""}`;
    return `<li class="lab-row" data-lab-id="${escapeHtml(r?.id ?? "")}">`
      + `<span class="lab-hypothesis">${escapeHtml(r?.hypothesis ?? "—")}</span> `
      + `<span class="lab-level">${escapeHtml(levelText)}</span> `
      + `<span class="lab-status">${escapeHtml(r?.status ?? "—")}</span></li>`;
  }).join("");
  return `<ul class="lab-list">${items}</ul>`;
}

// HN-057 Hortus run viewer: generations charted from real run JSONLs.
// Format (one JSON object per line): {"generation": N, "best": X, "mean": Y}.
// The parser groups by generation (best = max, mean = average of the
// lines for that generation), sorts ascending, and SKIPS malformed
// lines — it never invents a generation. With no series the chart is
// an honest empty state, not a drawn line. No Hortus run JSONLs exist
// in this repo today, so the live board shows that state; the parser
// and chart below are proven on format fixtures in the test file.
// The champion card renders only what a run record actually carries
// (organism id, rung label, params) — nothing is filled in.
export function parseHortusJsonl(text) {
  const byGen = new Map();
  let skipped = 0;
  for (const line of String(text ?? "").split("\n")) {
    const trimmed = line.trim();
    if (trimmed === "") continue;
    let obj;
    try { obj = JSON.parse(trimmed); } catch { skipped += 1; continue; }
    const gen = Number(obj?.generation);
    const best = Number(obj?.best);
    const mean = Number(obj?.mean);
    if (!Number.isFinite(gen) || !Number.isFinite(best) || !Number.isFinite(mean)) {
      skipped += 1;
      continue;
    }
    const slot = byGen.get(gen) ?? { generation: gen, best: -Infinity, meanSum: 0, meanCount: 0 };
    slot.best = Math.max(slot.best, best);
    slot.meanSum += mean;
    slot.meanCount += 1;
    byGen.set(gen, slot);
  }
  const series = [...byGen.values()]
    .sort((a, b) => a.generation - b.generation)
    .map((s) => ({ generation: s.generation, best: s.best, mean: s.meanSum / s.meanCount }));
  return { series, skipped };
}

export function hortusChart(series) {
  const points = Array.isArray(series) ? series : [];
  if (points.length === 0) {
    return `<p class="empty-state">No Hortus runs in this repo yet.</p>`;
  }
  const W = 600, H = 200, PAD = 30;
  const maxGen = Math.max(...points.map((p) => p.generation), 1);
  const maxVal = Math.max(...points.map((p) => Math.max(p.best, p.mean)), 1);
  const x = (g) => PAD + (g / maxGen) * (W - 2 * PAD);
  const y = (v) => H - PAD - (v / maxVal) * (H - 2 * PAD);
  const poly = (key) => points.map((p) => `${x(p.generation).toFixed(1)},${y(p[key]).toFixed(1)}`).join(" ");
  const labels = points.map((p) => `<text x="${x(p.generation).toFixed(1)}" y="${H - 8}" font-size="10">G${p.generation}</text>`).join("");
  return `<svg class="hortus-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Hortus best and mean per generation">`
    + `<polyline class="hortus-best" fill="none" stroke="currentColor" points="${poly("best")}"/>`
    + `<polyline class="hortus-mean" fill="none" stroke="currentColor" stroke-dasharray="4 3" points="${poly("mean")}"/>`
    + labels + `</svg>`
    + `<p>Best (solid) and mean (dashed) per generation; ${points.length} generations.</p>`;
}

export function hortusChampion(run) {
  const champ = run?.champion;
  if (!champ || typeof champ !== "object") {
    return `<p class="empty-state">No champion recorded yet.</p>`;
  }
  return `<div class="hortus-champion">`
    + `<span class="hortus-champion-id">${escapeHtml(champ.organism ?? champ.id ?? "—")}</span> `
    + `<span class="hortus-champion-rung">${escapeHtml(champ.rung ?? "—")}</span> `
    + `<span class="hortus-champion-params">${escapeHtml(JSON.stringify(champ.params ?? {}))}</span></div>`;
}
