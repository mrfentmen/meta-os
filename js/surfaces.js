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

// HN-058 Gate status page: the Delaney gate shown as its true state,
// driven by the gate directory's files. The directory is read via its
// manifest (gates/delaney/manifest.json, listing the files present).
// State criteria, in precedence order:
//   earned   — a file whose name marks the gate earned (earned.json)
//   running  — a run marker is present (running.json)
//   prepared — the Delaney set file is present (delaney-set.json)
//   not prepared — none of the above (today's true state on main:
//   no gate files exist in this repo, so the page says so plainly).
export function gateState(files) {
  const names = (Array.isArray(files) ? files : []).map((f) => String(f ?? ""));
  if (names.some((n) => /(^|\/)earned\.json$/.test(n))) return "earned";
  if (names.some((n) => /(^|\/)running\.json$/.test(n))) return "running";
  if (names.some((n) => /(^|\/)delaney-set\.json$/.test(n))) return "prepared";
  return "not prepared";
}

export function gateStatusPage(manifest) {
  const files = Array.isArray(manifest?.files) ? manifest.files : [];
  const state = gateState(files);
  const fileList = files.length > 0
    ? `<ul>${files.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}</ul>`
    : `<p class="empty-state">No gate files in this repo yet.</p>`;
  return `<div class="gate-status" data-gate-state="${escapeHtml(state)}">`
    + `<span class="gate-state-chip">${escapeHtml(state)}</span>`
    + `<p>Delaney gate state is read from the gate directory's files: earned.json → earned, running.json → running, delaney-set.json → prepared, otherwise not prepared.</p>`
    + fileList + `</div>`;
}

// HN-059 Evidence viewer: flagged-incident evidence crops in the app,
// with the ID: UNIDENTIFIED card exactly as specced (README identity
// rule: the system describes what a person looks like and never puts
// a name to a face). Rules, all enforced here:
//   - crops are shown only for flagged incidents;
//   - a purged incident shows the purge, never stale counts;
//   - the card carries ID: UNIDENTIFIED and no name field, ever.
// Input is the crew-status projection shape: {status, evidence:
// {files, frames, face_crops} | null, evidence_purged}. Flagged means
// status === "flagged" (crew_records.py).
export function evidenceViewer(incident) {
  const card = `<div class="evidence-id-card">ID: UNIDENTIFIED</div>`;
  if (incident?.evidence_purged) {
    return card + `<p class="evidence-purged">Evidence purged — no person evidence is kept.</p>`;
  }
  if (incident?.status !== "flagged") {
    return card + `<p class="empty-state">Evidence crops are taken only on flagged events.</p>`;
  }
  const ev = incident?.evidence;
  if (!ev || !Number.isFinite(ev.files) || ev.files <= 0) {
    return card + `<p class="empty-state">No evidence recorded for this incident.</p>`;
  }
  return card + `<ul class="evidence-crops">`
    + `<li>${ev.files} evidence file${ev.files === 1 ? "" : "s"}</li>`
    + `<li>${ev.frames ?? 0} flagged/investigation frames</li>`
    + `<li>${ev.face_crops ?? 0} face crops</li></ul>`;
}

// HN-061 BOLO card: the recorded-description card rendered from a real
// staged incident record. The key set is exactly BOLO_KEYS
// (server/queue/evidence.py): division, category, camera_name, area,
// flagged_at, frame_files, face_crops, person_descriptions,
// visible_marks, direction_of_travel, direction_note — observation
// and evidence only. Any key outside that set is DROPPED, never
// rendered, so no identity-shaped field (a name, an id, a match) can
// leak through. Visible marks only: person_descriptions render as
// descriptions, never as a name. The card header always reads
// ID: UNIDENTIFIED.
export const BOLO_KEYS = ["division", "category", "camera_name", "area",
  "flagged_at", "frame_files", "face_crops", "person_descriptions",
  "visible_marks", "direction_of_travel", "direction_note"];

export function boloCard(bolo) {
  if (!bolo || typeof bolo !== "object") {
    return `<p class="empty-state">No BOLO filed.</p>`;
  }
  const rows = BOLO_KEYS.filter((k) => bolo[k] !== undefined && bolo[k] !== null)
    .map((k) => {
      const v = Array.isArray(bolo[k]) ? bolo[k].join("; ") : bolo[k];
      return `<li><span class="bolo-key">${escapeHtml(k)}</span>: `
        + `<span class="bolo-value">${escapeHtml(v)}</span></li>`;
    }).join("");
  return `<div class="bolo-card"><div class="evidence-id-card">ID: UNIDENTIFIED</div>`
    + `<ul class="bolo-fields">${rows}</ul></div>`;
}

// HN-062 Records timeline: an incident's life as one timeline from
// its record file. Steps render in FILE order — the record is the
// order (patrol → review → investigation → dispatch in the normal
// life, but a record with different steps renders exactly what it
// carries). Nothing is reordered, rebuilt, or filled in: a dispatch
// step shows its receipt, a purge step shows its reason, a step
// without a time shows no time.
export function timelineView(incident) {
  const steps = Array.isArray(incident?.timeline) ? incident.timeline : [];
  if (steps.length === 0) {
    return `<p class="empty-state">No timeline recorded for this incident.</p>`;
  }
  const items = steps.map((s) => {
    const parts = [`<span class="timeline-step">${escapeHtml(s?.step ?? "—")}</span>`];
    if (s?.at) parts.push(`<span class="timeline-at">${escapeHtml(s.at)}</span>`);
    if (s?.status) parts.push(`<span class="timeline-status">${escapeHtml(s.status)}</span>`);
    if (s?.receipt_id) parts.push(`<span class="timeline-receipt">receipt ${escapeHtml(s.receipt_id)}</span>`);
    if (s?.reason) parts.push(`<span class="timeline-reason">${escapeHtml(s.reason)}</span>`);
    if (s?.step === "bolo") parts.push(`<span class="timeline-note">BOLO filed</span>`);
    return `<li>${parts.join(" ")}</li>`;
  }).join("");
  return `<ol class="records-timeline">${items}</ol>`;
}

// HN-064 Dispatch receipt view: the sim- receipt shown on the
// incident after a staged dispatch, labelled SIMULATED in the view.
// Format follows the loop feed's dispatch line (js/command-loop.js):
// package logged, receipt id, and the plain statement that no real
// service was contacted. No receipt exists before a dispatch, so none
// is shown then.
export function receiptView(incident) {
  const receipt = incident?.receipt_id;
  if (typeof receipt !== "string" || receipt.length === 0) {
    return `<p class="empty-state">No dispatch receipt for this incident.</p>`;
  }
  return `<div class="dispatch-receipt">`
    + `<span class="dispatch-receipt-label">Dispatch (SIMULATED)</span> `
    + `<span class="dispatch-receipt-id">receipt ${escapeHtml(receipt)}</span> `
    + `<span class="dispatch-receipt-note">Package logged — no real service contacted.</span></div>`;
}

// HN-065 Cost ticker: the incident view shows calls spent and
// dollars spent from the ledger. Input is the budget ledger state
// (server/budget.mjs shape: {calls, est_cost_usd, log}). A missing
// ledger is a fresh ledger (calls 0, $0.00) — the budget module's
// own rule, not an invention. The page re-fetches on an interval so
// the ticker updates as the chain runs.
export function costTicker(state) {
  const calls = Number.isFinite(Number(state?.calls)) ? Number(state.calls) : 0;
  const dollars = Number.isFinite(Number(state?.est_cost_usd)) ? Number(state.est_cost_usd) : 0;
  return `<div class="cost-ticker">`
    + `<span class="cost-calls">${calls} calls spent</span> `
    + `<span class="cost-dollars">$${dollars.toFixed(2)} spent</span></div>`;
}

// HN-066 Officina board: workshop runs rendered from Milo's records
// format (os/worlds/officina/runs/*.json). Three shapes exist:
//   run-001 files: rough_input, brief, rounds_used, final_params,
//     final_grade, verification, proven, status;
//   overnight run: artefact_class, n_variants, jobs, failures (each
//     with a failure_reason), best, proven_best, score curve;
//   best-design files: artefact_class, best, verification, proven.
// A run-001 file is marked FAILED only on recorded failure evidence:
// feasible === false, a non-empty violations list, or
// fresh_agrees === false. An overnight run lists its variant failures
// with their reasons (failures are per-variant, not a failed run).
// A record with null grade/status renders "unknown" — never failed,
// never proven, never filled in.
export function officinaBoard(files) {
  const runs = (Array.isArray(files) ? files : []).filter((f) => f && typeof f === "object");
  const sections = [];
  const singleRuns = runs.filter((f) => f.final_params !== undefined || f.rough_input !== undefined);
  if (singleRuns.length > 0) {
    const rows = singleRuns.map((r) => {
      const grade = r.final_grade ?? {};
      const violations = Array.isArray(grade.violations) ? grade.violations : [];
      const failed = grade.feasible === false || violations.length > 0 || r.verification?.fresh_agrees === false;
      const state = failed ? "failed" : (r.status ?? "unknown");
      const rth = Number.isFinite(Number(grade.r_th_c_per_w)) ? Number(grade.r_th_c_per_w).toFixed(3) : "—";
      return `<li class="officina-run officina-run--${escapeHtml(state)}">`
        + `<span class="officina-input">${escapeHtml(r.rough_input ?? r.brief?.artefact_class ?? "—")}</span> `
        + `<span class="officina-rounds">${r.rounds_used ?? "—"} rounds</span> `
        + `<span class="officina-grade">R_th ${rth}</span> `
        + `<span class="officina-state">${escapeHtml(state)}</span></li>`;
    }).join("");
    sections.push(`<h3>Runs</h3><ul class="officina-runs">${rows}</ul>`);
  }
  const overnight = runs.filter((f) => Number.isFinite(Number(f.n_variants)));
  for (const o of overnight) {
    const failures = Array.isArray(o.failures) ? o.failures : [];
    const failRows = failures.slice(0, 5).map((fl) =>
      `<li>job ${escapeHtml(fl.job_id ?? "—")}: ${escapeHtml(fl.failure_reason ?? "failed")}</li>`).join("");
    const bestScore = Number.isFinite(Number(o.best?.score_r_th_c_per_w))
      ? Number(o.best.score_r_th_c_per_w).toFixed(3) : "—";
    const provenScore = Number.isFinite(Number(o.proven_best?.score_r_th_c_per_w))
      ? Number(o.proven_best.score_r_th_c_per_w).toFixed(3) : "—";
    sections.push(`<h3>Overnight run: ${escapeHtml(o.artefact_class ?? "—")}</h3>`
      + `<p>${o.n_variants} variants, ${failures.length} failures, best R_th ${bestScore}, proven best R_th ${provenScore}.</p>`
      + `<ul class="officina-failures">${failRows || "<li>No failures recorded.</li>"}</ul>`);
  }
  const designs = runs.filter((f) => f.best !== undefined && f.n_variants === undefined);
  if (designs.length > 0) {
    const rows = designs.map((d) => {
      const params = d.best?.params ?? d.best ?? {};
      return `<li class="officina-design">`
        + `<span class="officina-class">${escapeHtml(d.artefact_class ?? "—")}</span> `
        + `<span class="officina-params">${escapeHtml(JSON.stringify(params))}</span> `
        + `<span class="officina-proven">${d.proven ? "proven" : "unproven"}</span></li>`;
    }).join("");
    sections.push(`<h3>Proven designs</h3><ul class="officina-designs">${rows}</ul>`);
  }
  if (sections.length === 0) return `<p class="empty-state">No Officina runs recorded.</p>`;
  return `<div class="officina-board">${sections.join("")}</div>`;
}

// HN-067 Custos board: patrol records by tier/source rendered from
// Rowan's records format (os/worlds/custos/runs/*.jsonl). Each line
// is one observation: {record_type, tier, source, category, ts,
// detail}. Malformed lines are skipped and counted, never rendered.
// The server serves .jsonl now (server.mjs CONTENT_TYPES), so the
// board fetches the real run files.
export function parseCustosJsonl(text) {
  const records = [];
  let skipped = 0;
  for (const line of String(text ?? "").split("\n")) {
    const trimmed = line.trim();
    if (trimmed === "") continue;
    try {
      const obj = JSON.parse(trimmed);
      if (obj && typeof obj === "object") records.push(obj);
      else skipped += 1;
    } catch { skipped += 1; }
  }
  return { records, skipped };
}

export function custosBoard(records) {
  const rows = (Array.isArray(records) ? records : []).filter((r) => r && typeof r === "object");
  if (rows.length === 0) {
    return `<p class="empty-state">No patrol records yet.</p>`;
  }
  // Observations carry tier/source/category. Escalations and
  // patrol-summaries are patrol records too, but untiered — they are
  // counted by type, never folded into the tier/source groups.
  const isObservation = (r) => r.record_type === "observation"
    || (r.record_type === undefined && typeof r.tier === "string");
  const observations = rows.filter(isObservation);
  const others = rows.filter((r) => !isObservation(r));
  const byTier = new Map();
  const bySource = new Map();
  for (const r of observations) {
    const tier = typeof r.tier === "string" ? r.tier : "unknown";
    const source = typeof r.source === "string" ? r.source : "unknown";
    byTier.set(tier, (byTier.get(tier) ?? 0) + 1);
    bySource.set(source, (bySource.get(source) ?? 0) + 1);
  }
  const tierRows = [...byTier.entries()].sort().map(([t, n]) =>
    `<li>${escapeHtml(t)}: ${n}</li>`).join("");
  const sourceRows = [...bySource.entries()].sort().map(([s, n]) =>
    `<li>${escapeHtml(s)}: ${n}</li>`).join("");
  const otherCounts = new Map();
  for (const r of others) {
    const t = typeof r.record_type === "string" ? r.record_type : "unknown";
    otherCounts.set(t, (otherCounts.get(t) ?? 0) + 1);
  }
  const otherRows = [...otherCounts.entries()].sort().map(([t, n]) =>
    `<li>${escapeHtml(t)}: ${n}</li>`).join("");
  const sorted = [...observations].sort((a, b) => String(b.ts ?? "").localeCompare(String(a.ts ?? "")));
  const recent = sorted.slice(0, 20).map((r) =>
    `<li><span class="custos-tier">${escapeHtml(r.tier ?? "—")}</span> `
    + `<span class="custos-category">${escapeHtml(r.category ?? "—")}</span> `
    + `<span class="custos-source">${escapeHtml(r.source ?? "—")}</span> `
    + `<span class="custos-at">${escapeHtml(r.ts ?? "—")}</span></li>`).join("");
  return `<div class="custos-board">`
    + `<h3>By tier</h3><ul>${tierRows}</ul>`
    + `<h3>By source</h3><ul>${sourceRows}</ul>`
    + (otherRows ? `<h3>Other patrol records</h3><ul>${otherRows}</ul>` : "")
    + `<h3>Latest observations</h3><ol>${recent}</ol></div>`;
}
