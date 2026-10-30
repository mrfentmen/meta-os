// Meta Trio frontend wiring. Connects camera -> sampler -> analysis
// client -> event display + session log, for whichever of the three
// products (Vigiles, Ignis, Sanitas) is selected. This module contains no
// detection logic and no sample data: if the backend is unreachable, the
// UI shows the error and nothing else.

import { Camera, cameraSupported, MAX_FRAME_DIMENSION } from "./camera.js";
import { FrameSampler } from "./sampler.js";
import { assessFrame, AssessError, checkHealth } from "./client.js";
import { SessionLog } from "./log.js";
import { PRODUCT_BY_ID, isProductId } from "./products.js";
import { ContactsStore } from "./contacts.js";
import { ignisLookAlikeScoreboard } from "./ignis-scoreboard.js";
import { ignisReportedConfidence } from "./ignis-confidence.js";
import { ignisReviewQueue } from "./ignis-review-queue.js";
import { ignisEvidenceTransparency } from "./ignis-evidence.js";
import { isSupportedImageFile, readFileAsDataURL, downscaleImageToDataURL } from "./image_input.js";
import { isSupportedVideoFile, captureVideoFrame } from "./video_input.js";

const $ = (id) => document.getElementById(id);

const els = {
  video: $("preview"),
  captureCanvas: $("capture-canvas"),
  cameraIndicator: $("camera-indicator"),
  cameraState: $("camera-state"),
  cameraFacing: $("camera-facing"),
  analysisActive: $("analysis-active"),
  btnCameraStart: $("btn-camera-start"),
  btnCameraStop: $("btn-camera-stop"),
  btnAnalysisStart: $("btn-analysis-start"),
  btnAnalysisStop: $("btn-analysis-stop"),
  btnReset: $("btn-reset"),
  productBadge: $("product-badge"),
  productRadios: [...document.querySelectorAll('input[name="product"]')],
  productDepartment: $("product-department"),
  productTagline: $("product-tagline"),
  productCategories: $("product-categories"),
  productGuidance: $("product-guidance"),
  productLimitations: $("product-limitations"),
  endpoint: $("endpoint"),
  btnBackendCheck: $("btn-backend-check"),
  backendHealth: $("backend-health"),
  intervalSeconds: $("interval-seconds"),
  scenarioSelect: $("scenario-select"),
  scenarioLabel: $("scenario-label"),
  samplingDisclosure: $("sampling-disclosure"),
  backendStatus: $("backend-status"),
  inFlight: $("in-flight"),
  samplerStats: $("sampler-stats"),
  lastRoundTrip: $("last-round-trip"),
  latest: $("latest-assessment"),
  history: $("history-list"),
  historyEmpty: $("history-empty"),
  btnExport: $("btn-export-log"),
  btnClearLog: $("btn-clear-log"),
  logStats: $("log-stats"),
  logStatsByProduct: $("log-stats-by-product"),
  logStatsFailedByProduct: $("log-stats-failed-by-product"),
  logStatsByFailure: $("log-stats-by-failure"),
  logStatsLastOk: $("log-stats-last-ok"),
  logStatsFirstOk: $("log-stats-first-ok"),
  logStatsAvgLatency: $("log-stats-avg-latency"),
  logStatsLatencyRange: $("log-stats-latency-range"),
  logStatsLastOkByProduct: $("log-stats-last-ok-by-product"),
  logStatsFirstOkByProduct: $("log-stats-first-ok-by-product"),
  logStatsLastFailedByProduct: $("log-stats-last-failed-by-product"),
  logStatsFirstFailedByProduct: $("log-stats-first-failed-by-product"),
  logStatsAvgLatencyByProduct: $("log-stats-avg-latency-by-product"),
  logStatsFailuresByProduct: $("log-stats-failures-by-product"),
  logStatsLatencyRangeByProduct: $("log-stats-latency-range-by-product"),
  logStatsOkShareByProduct: $("log-stats-ok-share-by-product"),
  logStatsFailedShareByProduct: $("log-stats-failed-share-by-product"),
  logStatsEntryShareByProduct: $("log-stats-entry-share-by-product"),
  logStatsEntryCountByProduct: $("log-stats-entry-count-by-product"),
  logStatsFirstEntryByProduct: $("log-stats-first-entry-by-product"),
  logStatsLastEntryByProduct: $("log-stats-last-entry-by-product"),
  logStatsEntrySpanByProduct: $("log-stats-entry-span-by-product"),
  logStatsFailedSpanByProduct: $("log-stats-failed-span-by-product"),
  logStatsOkSpanByProduct: $("log-stats-ok-span-by-product"),
  logStatsOkSpan: $("log-stats-ok-span"),
  logStatsFailedSpan: $("log-stats-failed-span"),
  logStatsEntrySpan: $("log-stats-entry-span"),
  logStatsOkShare: $("log-stats-ok-share"),
  logStatsFailedShare: $("log-stats-failed-share"),
  logStatsMedianLatency: $("log-stats-median-latency"),
  logStatsFirstEntry: $("log-stats-first-entry"),
  logStatsLastEntry: $("log-stats-last-entry"),
  logStatsMedianLatencyByProduct: $("log-stats-median-latency-by-product"),
  logStatsFailedShareByStatusByProduct: $("log-stats-failed-share-by-status-by-product"),
  logStatsFailedShareByStatus: $("log-stats-failed-share-by-status"),
  logStatsFailedShareByStatusWithinProduct: $("log-stats-failed-share-by-status-within-product"),
  logStatsFirstFailed: $("log-stats-first-failed"),
  logStatsLastFailed: $("log-stats-last-failed"),
  logStatsOkLatencyShareByProduct: $("log-stats-ok-latency-share-by-product"),
  logStatsOkLatencyCount: $("log-stats-ok-latency-count"),
  logStatsOkLatencyCountByProduct: $("log-stats-ok-latency-count-by-product"),
  logStatsOkShareOfOkByProduct: $("log-stats-ok-share-of-ok-by-product"),
  logStatsOkLatencySum: $("log-stats-ok-latency-sum"),
  logStatsOkLatencySumByProduct: $("log-stats-ok-latency-sum-by-product"),
  logStatsFailedShareOfFailedByProduct: $("log-stats-failed-share-of-failed-by-product"),
  logStatsFailedShareOfEntriesByProduct: $("log-stats-failed-share-of-entries-by-product"),
  logStatsOkShareOfTotalByProduct: $("log-stats-ok-share-of-total-by-product"),
  logStatsFailedShareByStatusOfEntriesByProduct: $("log-stats-failed-share-by-status-of-entries-by-product"),
  logStatsFailedShareByStatusOfEntries: $("log-stats-failed-share-by-status-of-entries"),
  logStatsFailedShareByStatusOfEntriesWithinProduct: $("log-stats-failed-share-by-status-of-entries-within-product"),
  logStatsOkLatencyCountShareByProduct: $("log-stats-ok-latency-count-share-by-product"),
  logStatsEntrySpanShareByProduct: $("log-stats-entry-span-share-by-product"),
  logStatsOkLatencyCountShareOfEntriesByProduct: $("log-stats-ok-latency-count-share-of-entries-by-product"),
  logStatsOkSpanShareByProduct: $("log-stats-ok-span-share-by-product"),
  logStatsOkLatencyCountShareOfEntries: $("log-stats-ok-latency-count-share-of-entries"),
  logStatsFailedSpanShareByProduct: $("log-stats-failed-span-share-by-product"),
  logStatsOkLatencyCountShareOfOk: $("log-stats-ok-latency-count-share-of-ok"),
  logStatsOkLatencyCountShareOfOkByProduct: $("log-stats-ok-latency-count-share-of-ok-by-product"),
  logStatsOkSpanShareOfEntryWindowByProduct: $("log-stats-ok-span-share-of-entry-window-by-product"),
  logStatsOkLatencyCountShareOfOwnOkByProduct: $("log-stats-ok-latency-count-share-of-own-ok-by-product"),
  logStatsFailedSpanShareOfEntryWindowByProduct: $("log-stats-failed-span-share-of-entry-window-by-product"),
  logStatsOkLatencyCountShareOfOwnEntriesByProduct: $("log-stats-ok-latency-count-share-of-own-entries-by-product"),
  logStatsFailedSpanShareOfEntryWindow: $("log-stats-failed-span-share-of-entry-window"),
  logStatsOkSpanShareOfEntryWindow: $("log-stats-ok-span-share-of-entry-window"),
  logStatsFailedSpanShareOfOwnEntryWindowByProduct: $("log-stats-failed-span-share-of-own-entry-window-by-product"),
  logStatsOkSpanShareOfOwnEntryWindowByProduct: $("log-stats-ok-span-share-of-own-entry-window-by-product"),
  logStatsOkShareOfOwnEntriesByProduct: $("log-stats-ok-share-of-own-entries-by-product"),
  logStatsFailedSpanShareOfOwnOkWindowByProduct: $("log-stats-failed-span-share-of-own-ok-window-by-product"),
  logStatsOkSpanShareOfOwnFailedWindowByProduct: $("log-stats-ok-span-share-of-own-failed-window-by-product"),
  logStatsOkSpanShareOfFailedWindow: $("log-stats-ok-span-share-of-failed-window"),
  logStatsFailedSpanShareOfOkWindow: $("log-stats-failed-span-share-of-ok-window"),
  logStatsEntrySpanShareOfOkWindow: $("log-stats-entry-span-share-of-ok-window"),
  logStatsEntrySpanShareOfFailedWindow: $("log-stats-entry-span-share-of-failed-window"),
  logStatsEntrySpanShareOfOwnOkWindowByProduct: $("log-stats-entry-span-share-of-own-ok-window-by-product"),
  logStatsEntrySpanShareOfOwnFailedWindowByProduct: $("log-stats-entry-span-share-of-own-failed-window-by-product"),
  logStatsEntrySpanShareOfOkWindowByProduct: $("log-stats-entry-span-share-of-ok-window-by-product"),
  logStatsEntrySpanShareOfFailedWindowByProduct: $("log-stats-entry-span-share-of-failed-window-by-product"),
  logStatsFailedSpanShareOfOkWindowByProduct: $("log-stats-failed-span-share-of-ok-window-by-product"),
  logStatsOkSpanShareOfFailedWindowByProduct: $("log-stats-ok-span-share-of-failed-window-by-product"),
  ignisScoreboard: $("ignis-scoreboard"),
  ignisConfidence: $("ignis-confidence"),
  ignisReviewQueue: $("ignis-review-queue"),
  ignisEvidence: $("ignis-evidence"),
  contactsList: $("contacts-list"),
  contactsEmpty: $("contacts-empty"),
  contactName: $("contact-name"),
  contactRole: $("contact-role"),
  contactOrg: $("contact-org"),
  btnContactAdd: $("btn-contact-add"),
  contactsFormNote: $("contacts-form-note"),
  imageInput: $("image-input"),
  imagePreview: $("image-preview"),
  imageState: $("image-state"),
  btnImageAssess: $("btn-image-assess"),
  btnImageClear: $("btn-image-clear"),
  imageAssessing: $("image-assessing"),
  videoInput: $("video-input"),
  videoPreview: $("video-preview"),
  videoState: $("video-state"),
  btnVideoAssess: $("btn-video-assess"),
  btnVideoClear: $("btn-video-clear"),
  videoAssessing: $("video-assessing"),
};

const camera = new Camera(els.video);
// The log survives a reload: entries are kept in this browser's local
// storage (assessments and errors only, never frames) until exported or
// cleared. A store that is unavailable simply leaves the log in memory.
const log = new SessionLog({
  storage: typeof localStorage !== "undefined" ? localStorage : null,
});

// Contacts directory (Del direction 2026-10-29: Milo leads contacts,
// Sanitas first). Same local-only storage pattern as the session log:
// entries survive a reload, and an unavailable store leaves the panel
// working in memory. Nothing here sends or notifies anyone.
const contacts = new ContactsStore({
  storage: typeof localStorage !== "undefined" ? localStorage : null,
});

// The product selected in the UI. Every assess request carries this id,
// and every log entry records it; switching applies from the next tick.
let currentProductId = "vigiles";

function currentProduct() {
  return PRODUCT_BY_ID[currentProductId];
}

function renderProduct() {
  const product = currentProduct();
  document.body.dataset.product = product.id;
  els.productBadge.textContent = product.displayName;
  els.productDepartment.textContent = product.department;
  els.productTagline.textContent = product.tagline;
  els.productGuidance.textContent = product.inputGuidance;
  els.productLimitations.textContent = product.limitations;
  els.productCategories.replaceChildren();
  for (const category of product.categories) {
    const chip = document.createElement("li");
    chip.className = "chip";
    chip.textContent = category;
    els.productCategories.appendChild(chip);
  }
  // Rebuild the scenario options for this product and reset the choice:
  // carrying a previous product's scenario into this product's log
  // entries would mislabel the ground truth.
  els.scenarioSelect.replaceChildren();
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "— no label —";
  els.scenarioSelect.appendChild(none);
  for (const scenario of product.scenarios) {
    const option = document.createElement("option");
    option.value = scenario;
    option.textContent = scenario;
    els.scenarioSelect.appendChild(option);
  }
  els.scenarioSelect.value = "";
  renderContacts();
}

// Contacts panel: the directory for the currently selected product.
// Sample entries are flagged sample by the store and shown with a SAMPLE
// chip, so a placeholder is never mistaken for a real person. Delete is
// a human action on one entry; there is no send, notify, or dispatch
// action anywhere in this panel.
function renderContacts() {
  const entries = contacts.list(currentProductId);
  els.contactsList.replaceChildren();
  els.contactsEmpty.hidden = entries.length !== 0;
  for (const entry of entries) {
    const item = document.createElement("li");
    item.className = "contact-item";
    const name = document.createElement("strong");
    name.textContent = entry.name;
    item.appendChild(name);
    if (entry.sample) {
      const chip = document.createElement("span");
      chip.className = "sample-chip";
      chip.textContent = "SAMPLE";
      item.appendChild(chip);
    }
    const meta = document.createElement("p");
    meta.className = "contact-meta";
    meta.textContent = `${entry.role} · ${entry.organization}`;
    item.appendChild(meta);
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "Delete";
    del.setAttribute("aria-label", `Delete contact ${entry.name}`);
    del.addEventListener("click", () => {
      contacts.remove(entry.id);
      renderContacts();
    });
    item.appendChild(del);
    els.contactsList.appendChild(item);
  }
}

// Native parity: the native interval Stepper can only hold 1–60, so
// the value on screen is always the value being sampled at. The web
// number box accepted anything — 99, 0, or blank — while the interval
// below silently fell back to 3 s, so the box and the disclosure (and
// the sampler) disagreed about the real interval. Clamp to the range
// instead, with the 3 s default only for a blank or non-numeric box,
// and write the clamped value back into the box on change, so what the
// box shows is what runs.
function currentIntervalSeconds() {
  const seconds = Number(els.intervalSeconds.value);
  if (!Number.isFinite(seconds)) return 3;
  return Math.min(60, Math.max(1, seconds));
}

function currentIntervalMs() {
  return Math.round(currentIntervalSeconds() * 1000);
}

function currentEndpoint() {
  const value = els.endpoint.value.trim();
  return value || "/api/assess";
}

function currentScenarioLabel() {
  const custom = els.scenarioLabel.value.trim();
  if (custom !== "") return custom;
  const selected = els.scenarioSelect.value;
  return selected === "" ? null : selected;
}

function setBackendStatus(state, message) {
  // state: "unknown" | "connected" | "error"
  els.backendStatus.textContent = message;
  els.backendStatus.dataset.state = state;
}

function setCameraState(message) {
  els.cameraState.textContent = message;
}

function updateSamplingDisclosure() {
  const seconds = currentIntervalMs() / 1000;
  els.samplingDisclosure.textContent =
    `Analysis uses sampled frames: one frame every ${seconds} second${seconds === 1 ? "" : "s"} ` +
    "is sent to the assessment endpoint. This is not continuous video analysis, and events " +
    "between samples are not seen by the system.";
}

function updateSamplerStats() {
  els.samplerStats.textContent =
    `Ticks: ${sampler.tickCount} · Sent: ${sampler.sampledCount} · ` +
    `Skipped (request in flight): ${sampler.skippedCount} · Failed: ${sampler.errorCount}`;
}

// Native parity: the native app's status bar shows the last round trip,
// so the web Camera panel shows it too. It is the client-measured time
// for the last completed assessment request, success or failure — never
// the server-reported processing.latency_ms inside a response. Hidden
// until the first request completes; Reset clears it, exactly like the
// native Reset Session. A frame-capture failure makes no request, so it
// leaves the previous value alone, and the backend health check never
// touches it (it sends no frame).
function updateLastRoundTrip(latencyMs) {
  els.lastRoundTrip.textContent = `Last round trip: ${latencyMs} ms (client-measured)`;
  els.lastRoundTrip.hidden = false;
}

function clearLastRoundTrip() {
  els.lastRoundTrip.textContent = "";
  els.lastRoundTrip.hidden = true;
}

function updateLogStats() {
  els.logStats.textContent = `Session log entries: ${log.count}`;
  const stats = log.stats();
  els.logStatsByProduct.textContent =
    `Assessments by product: Vigiles ${stats.byProduct.vigiles} · Ignis ${stats.byProduct.ignis} · Sanitas ${stats.byProduct.sanitas} · Failed ${stats.failed}`;
  // DETAIL-34: the failed-by-product line breaks DETAIL-1's
  // global failed total down per product — the failure mirror
  // of the per-product ok counts, and the count behind
  // DETAIL-12's failed shares — always-rendered zeros, so a
  // product with no failures reads 0, never a missing bucket,
  // and successes never move a bucket. A failure with an
  // unknown or missing product still counts in DETAIL-1's
  // global total but moves no bucket here.
  els.logStatsFailedByProduct.textContent =
    `Failed by product: Vigiles ${stats.failedCountByProduct.vigiles} · Ignis ${stats.failedCountByProduct.ignis} · Sanitas ${stats.failedCountByProduct.sanitas}`;
  // DETAIL-2: the failure line breaks the same failed total down by
  // recorded cause, from the same stats() call — no new data, no
  // sampling, no model. It always renders (zeros included), like the
  // per-product line, so an empty session and a failing session read
  // the same shape and the line never appears or vanishes mid-run.
  els.logStatsByFailure.textContent =
    `Failures by cause: Network ${stats.failedByStatus.network_error} · HTTP ${stats.failedByStatus.http_error} · Invalid response ${stats.failedByStatus.invalid_response}`;
  // DETAIL-3: the last-success line names the most recent recorded
  // success by its request timestamp, or "none" when the log holds no
  // ok entry — same always-renders shape as the other stats lines, so
  // an empty session and a quiet session never change the panel's
  // shape, and failures never move the timestamp.
  els.logStatsLastOk.textContent =
    `Last successful assessment: ${stats.lastOkAt ?? "none"}`;
  // DETAIL-30: the global first-success line opens DETAIL-3's
  // last-success line — the session's first recorded success by
  // its request timestamp, or "none" when the log holds no ok
  // entry — same always-renders shape as the other stats lines,
  // so an empty session never changes the panel's shape. No new
  // stats field: stats() already exposes firstOkAt from
  // DETAIL-22, set once by insertion order, so a success with an
  // unknown or missing product still opens it (the per-product
  // DETAIL-18 buckets stay product-gated), a timestamp-less
  // success leaves it open for a later usable success, and
  // failures never move it. The pair with the last-success line
  // says when the session's successes began and when they last
  // happened, where DETAIL-22's success span alone does not
  // name the endpoints.
  els.logStatsFirstOk.textContent =
    `First successful assessment: ${stats.firstOkAt ?? "none"}`;
  // DETAIL-4: the average-latency line means the recorded round-trip
  // latency over successful assessments only, rounded to whole
  // milliseconds, or "none" when no success carries a usable latency
  // — same always-renders shape as the other stats lines.
  els.logStatsAvgLatency.textContent =
    `Average successful latency: ${stats.avgOkLatencyMs === null ? "none" : `${Math.round(stats.avgOkLatencyMs)} ms`}`;
  // DETAIL-6: the latency-range line bounds the average with the
  // fastest and slowest recorded successful latencies, rounded to
  // whole milliseconds, or "none" when no success carries a usable
  // latency — same always-renders shape as the other stats lines.
  // min null implies max null by construction, so one check covers
  // both ends.
  els.logStatsLatencyRange.textContent =
    `Fastest/slowest successful latency: ${stats.minOkLatencyMs === null ? "none" : `${Math.round(stats.minOkLatencyMs)} ms / ${Math.round(stats.maxOkLatencyMs)} ms`}`;
  // DETAIL-5: the per-product last-success line names each product's
  // most recent recorded success by its request timestamp, or "none"
  // per product with no success — same always-renders shape as the
  // other stats lines, so a quiet product never changes the panel's
  // shape, and failures never move a bucket.
  els.logStatsLastOkByProduct.textContent =
    `Last success by product: Vigiles ${stats.lastOkAtByProduct.vigiles ?? "none"} · Ignis ${stats.lastOkAtByProduct.ignis ?? "none"} · Sanitas ${stats.lastOkAtByProduct.sanitas ?? "none"}`;
  // DETAIL-18: the per-product first-success line opens DETAIL-5's
  // last-success line — each product's first recorded success by
  // its request timestamp, or "none" per product with no success —
  // same always-renders shape as the other stats lines, and
  // failures never move a bucket.
  els.logStatsFirstOkByProduct.textContent =
    `First success by product: Vigiles ${stats.firstOkAtByProduct.vigiles ?? "none"} · Ignis ${stats.firstOkAtByProduct.ignis ?? "none"} · Sanitas ${stats.firstOkAtByProduct.sanitas ?? "none"}`;
  // DETAIL-7: the per-product last-failure line mirrors DETAIL-5 on
  // the failure side — each product's most recent recorded failure
  // by its request timestamp, or "none" per product with no failure
  // — same always-renders shape as the other stats lines, and
  // successes never move a bucket.
  els.logStatsLastFailedByProduct.textContent =
    `Last failure by product: Vigiles ${stats.lastFailedAtByProduct.vigiles ?? "none"} · Ignis ${stats.lastFailedAtByProduct.ignis ?? "none"} · Sanitas ${stats.lastFailedAtByProduct.sanitas ?? "none"}`;
  // DETAIL-19: the per-product first-failure line opens DETAIL-7's
  // last-failure line — each product's first recorded failure by
  // its request timestamp, or "none" per product with no failure —
  // same always-renders shape as the other stats lines, and
  // successes never move a bucket.
  els.logStatsFirstFailedByProduct.textContent =
    `First failure by product: Vigiles ${stats.firstFailedAtByProduct.vigiles ?? "none"} · Ignis ${stats.firstFailedAtByProduct.ignis ?? "none"} · Sanitas ${stats.firstFailedAtByProduct.sanitas ?? "none"}`;
  // DETAIL-8: the per-product average-latency line splits DETAIL-4's
  // mean per product, rounded to whole milliseconds, or "none" per
  // product with no success carrying a usable latency — same
  // always-renders shape as the other stats lines, and failures
  // never contribute to any bucket.
  els.logStatsAvgLatencyByProduct.textContent =
    `Average successful latency by product: Vigiles ${stats.avgOkLatencyMsByProduct.vigiles === null ? "none" : `${Math.round(stats.avgOkLatencyMsByProduct.vigiles)} ms`} · Ignis ${stats.avgOkLatencyMsByProduct.ignis === null ? "none" : `${Math.round(stats.avgOkLatencyMsByProduct.ignis)} ms`} · Sanitas ${stats.avgOkLatencyMsByProduct.sanitas === null ? "none" : `${Math.round(stats.avgOkLatencyMsByProduct.sanitas)} ms`}`;
  // DETAIL-9: the per-product failures-by-cause line splits
  // DETAIL-2's cause breakdown per product, from the same stats()
  // call — same always-renders shape as the other stats lines, so
  // a product with no failure of a cause reads zero, never a
  // missing bucket, and successes never move a bucket.
  els.logStatsFailuresByProduct.textContent =
    `Failures by cause by product: Vigiles Network ${stats.failedByStatusByProduct.vigiles.network_error}, HTTP ${stats.failedByStatusByProduct.vigiles.http_error}, Invalid response ${stats.failedByStatusByProduct.vigiles.invalid_response} · Ignis Network ${stats.failedByStatusByProduct.ignis.network_error}, HTTP ${stats.failedByStatusByProduct.ignis.http_error}, Invalid response ${stats.failedByStatusByProduct.ignis.invalid_response} · Sanitas Network ${stats.failedByStatusByProduct.sanitas.network_error}, HTTP ${stats.failedByStatusByProduct.sanitas.http_error}, Invalid response ${stats.failedByStatusByProduct.sanitas.invalid_response}`;
  // DETAIL-10: the per-product latency-range line splits DETAIL-6's
  // range per product, rounded to whole milliseconds, or "none" per
  // product with no success carrying a usable latency — same
  // always-renders shape as the other stats lines, and failures
  // never contribute to any bucket. Min null implies max null per
  // bucket by construction, so one check covers both ends.
  els.logStatsLatencyRangeByProduct.textContent =
    `Fastest/slowest successful latency by product: Vigiles ${stats.minOkLatencyMsByProduct.vigiles === null ? "none" : `${Math.round(stats.minOkLatencyMsByProduct.vigiles)} ms / ${Math.round(stats.maxOkLatencyMsByProduct.vigiles)} ms`} · Ignis ${stats.minOkLatencyMsByProduct.ignis === null ? "none" : `${Math.round(stats.minOkLatencyMsByProduct.ignis)} ms / ${Math.round(stats.maxOkLatencyMsByProduct.ignis)} ms`} · Sanitas ${stats.minOkLatencyMsByProduct.sanitas === null ? "none" : `${Math.round(stats.minOkLatencyMsByProduct.sanitas)} ms / ${Math.round(stats.maxOkLatencyMsByProduct.sanitas)} ms`}`;
  // DETAIL-11: the per-product successful-share line splits each
  // product's own entries into the share that succeeded, rendered
  // as a whole percent, or "none" per product with no entries —
  // same always-renders shape as the other stats lines, and a
  // product that only failed reads 0%, never "none".
  els.logStatsOkShareByProduct.textContent =
    `Successful share by product: Vigiles ${stats.okShareByProduct.vigiles === null ? "none" : `${Math.round(stats.okShareByProduct.vigiles * 100)}%`} · Ignis ${stats.okShareByProduct.ignis === null ? "none" : `${Math.round(stats.okShareByProduct.ignis * 100)}%`} · Sanitas ${stats.okShareByProduct.sanitas === null ? "none" : `${Math.round(stats.okShareByProduct.sanitas * 100)}%`}`;
  // DETAIL-12: the mirror line — each product's own entries split
  // into the share that failed, rendered as a whole percent, or
  // "none" per product with no entries. A product that only
  // succeeded reads 0%, never "none".
  els.logStatsFailedShareByProduct.textContent =
    `Failed share by product: Vigiles ${stats.failedShareByProduct.vigiles === null ? "none" : `${Math.round(stats.failedShareByProduct.vigiles * 100)}%`} · Ignis ${stats.failedShareByProduct.ignis === null ? "none" : `${Math.round(stats.failedShareByProduct.ignis * 100)}%`} · Sanitas ${stats.failedShareByProduct.sanitas === null ? "none" : `${Math.round(stats.failedShareByProduct.sanitas * 100)}%`}`;
  // DETAIL-13: the session-mix line — each product's entries as a
  // share of the session total, rendered as a whole percent, or
  // "none" per product only on an empty log. A product with no
  // entries in a non-empty session reads 0%, never "none".
  els.logStatsEntryShareByProduct.textContent =
    `Session share by product: Vigiles ${stats.entryShareByProduct.vigiles === null ? "none" : `${Math.round(stats.entryShareByProduct.vigiles * 100)}%`} · Ignis ${stats.entryShareByProduct.ignis === null ? "none" : `${Math.round(stats.entryShareByProduct.ignis * 100)}%`} · Sanitas ${stats.entryShareByProduct.sanitas === null ? "none" : `${Math.round(stats.entryShareByProduct.sanitas * 100)}%`}`;
  // DETAIL-14: the per-product entry-count line exposes the
  // counts behind DETAIL-13's shares — ok plus failed per
  // product, always-rendered zeros, so a product that only
  // failed still shows its full count here, unlike DETAIL-1's
  // success-only line.
  els.logStatsEntryCountByProduct.textContent =
    `Entries by product: Vigiles ${stats.entryCountByProduct.vigiles} · Ignis ${stats.entryCountByProduct.ignis} · Sanitas ${stats.entryCountByProduct.sanitas}`;
  // DETAIL-15: the per-product first-entry line names each
  // product's first recorded entry by its request timestamp, any
  // status — the opening counterpart to DETAIL-5/7's last-success
  // and last-failure lines — or "none" per product with no entry
  // carrying a usable timestamp, same always-renders shape as the
  // other stats lines, so a quiet product never changes the
  // panel's shape.
  els.logStatsFirstEntryByProduct.textContent =
    `First entry by product: Vigiles ${stats.firstEntryAtByProduct.vigiles ?? "none"} · Ignis ${stats.firstEntryAtByProduct.ignis ?? "none"} · Sanitas ${stats.firstEntryAtByProduct.sanitas ?? "none"}`;
  // DETAIL-16: the per-product last-entry line names each
  // product's most recent recorded entry by its request timestamp,
  // any status — the closing counterpart to DETAIL-15's first-entry
  // line — or "none" per product with no entry carrying a usable
  // timestamp, same always-renders shape as the other stats lines,
  // so a quiet product never changes the panel's shape.
  els.logStatsLastEntryByProduct.textContent =
    `Last entry by product: Vigiles ${stats.lastEntryAtByProduct.vigiles ?? "none"} · Ignis ${stats.lastEntryAtByProduct.ignis ?? "none"} · Sanitas ${stats.lastEntryAtByProduct.sanitas ?? "none"}`;
  // DETAIL-17: the per-product entry-span line names each
  // product's first-to-last recorded stretch in whole
  // milliseconds — the span DETAIL-15/16's endpoints imply but do
  // not state — or "none" per product with no usable entry pair,
  // same always-renders shape as the other stats lines, so a
  // quiet product never changes the panel's shape.
  els.logStatsEntrySpanByProduct.textContent =
    `Entry span by product: Vigiles ${stats.entrySpanMsByProduct.vigiles === null ? "none" : `${stats.entrySpanMsByProduct.vigiles} ms`} · Ignis ${stats.entrySpanMsByProduct.ignis === null ? "none" : `${stats.entrySpanMsByProduct.ignis} ms`} · Sanitas ${stats.entrySpanMsByProduct.sanitas === null ? "none" : `${stats.entrySpanMsByProduct.sanitas} ms`}`;
  // DETAIL-20: the per-product failure-span line names each
  // product's first-to-last recorded failure stretch in whole
  // milliseconds — the span DETAIL-19/7's endpoints imply but do
  // not state — or "none" per product with no usable failure pair,
  // same always-renders shape as the other stats lines, so a
  // quiet product never changes the panel's shape.
  els.logStatsFailedSpanByProduct.textContent =
    `Failure span by product: Vigiles ${stats.failedSpanMsByProduct.vigiles === null ? "none" : `${stats.failedSpanMsByProduct.vigiles} ms`} · Ignis ${stats.failedSpanMsByProduct.ignis === null ? "none" : `${stats.failedSpanMsByProduct.ignis} ms`} · Sanitas ${stats.failedSpanMsByProduct.sanitas === null ? "none" : `${stats.failedSpanMsByProduct.sanitas} ms`}`;
  // DETAIL-21: the per-product success-span line names each
  // product's first-to-last recorded success stretch in whole
  // milliseconds — the span DETAIL-18/5's endpoints imply but do
  // not state — or "none" per product with no usable success pair,
  // same always-renders shape as the other stats lines, so a
  // quiet product never changes the panel's shape.
  els.logStatsOkSpanByProduct.textContent =
    `Success span by product: Vigiles ${stats.okSpanMsByProduct.vigiles === null ? "none" : `${stats.okSpanMsByProduct.vigiles} ms`} · Ignis ${stats.okSpanMsByProduct.ignis === null ? "none" : `${stats.okSpanMsByProduct.ignis} ms`} · Sanitas ${stats.okSpanMsByProduct.sanitas === null ? "none" : `${stats.okSpanMsByProduct.sanitas} ms`}`;
  // DETAIL-22: the global success-span line names the session's
  // first-to-last recorded success stretch in whole milliseconds
  // — the span the per-product DETAIL-21 line implies but does
  // not state across products — or "none" with no usable success
  // pair, same always-renders shape as the other stats lines, so
  // a quiet session never changes the panel's shape.
  els.logStatsOkSpan.textContent =
    `Success span: ${stats.okSpanMs === null ? "none" : `${stats.okSpanMs} ms`}`;
  // DETAIL-23: the global failure-span line names the session's
  // first-to-last recorded failure stretch in whole milliseconds
  // — the span the per-product DETAIL-20 line implies but does
  // not state across products — or "none" with no usable failure
  // pair, same always-renders shape as the other stats lines, so
  // a quiet session never changes the panel's shape.
  els.logStatsFailedSpan.textContent =
    `Failure span: ${stats.failedSpanMs === null ? "none" : `${stats.failedSpanMs} ms`}`;
  // DETAIL-24: the global entry-span line names the session's
  // first-to-last recorded entry stretch in whole milliseconds,
  // across products and across statuses — the span the
  // per-product DETAIL-17 line implies but does not state
  // across products — or "none" with no usable entry pair,
  // same always-renders shape as the other stats lines, so a
  // quiet session never changes the panel's shape.
  els.logStatsEntrySpan.textContent =
    `Entry span: ${stats.entrySpanMs === null ? "none" : `${stats.entrySpanMs} ms`}`;
  // DETAIL-25: the global successful-share line names the
  // session's successes as a share of all entries, rendered
  // as a whole percent, or "none" on an empty log — the
  // share the per-product DETAIL-11 line implies but does
  // not state across products — same always-renders shape
  // as the other stats lines, so a quiet session never
  // changes the panel's shape. A session with no successes
  // reads 0%, never "none".
  els.logStatsOkShare.textContent =
    `Successful share: ${stats.okShare === null ? "none" : `${Math.round(stats.okShare * 100)}%`}`;
  // DETAIL-25: the mirror line — the session's failures as
  // a share of all entries, rendered as a whole percent, or
  // "none" on an empty log. A session with no failures reads
  // 0%, never "none", and the two shares sum to 100%
  // wherever either is non-null.
  els.logStatsFailedShare.textContent =
    `Failed share: ${stats.failedShare === null ? "none" : `${Math.round(stats.failedShare * 100)}%`}`;
  // DETAIL-26: the median-latency line names the middle recorded
  // successful latency, rounded to whole milliseconds, or "none"
  // when no success carries a usable latency — the typical
  // success DETAIL-4's mean and DETAIL-6's range imply but do
  // not state — same always-renders shape as the other stats
  // lines, so a quiet session never changes the panel's shape.
  els.logStatsMedianLatency.textContent =
    `Median successful latency: ${stats.medianOkLatencyMs === null ? "none" : `${Math.round(stats.medianOkLatencyMs)} ms`}`;
  // DETAIL-27: the global first- and last-entry lines name the
  // endpoints DETAIL-24's entry span already spans — the first
  // and last recorded entry timestamps, any status, across
  // products — or "none" per endpoint with no usable entry,
  // same always-renders shape as the other stats lines, so a
  // quiet session never changes the panel's shape. An entry
  // with an unknown or missing product still opens and closes
  // these endpoints (the per-product DETAIL-15/16 buckets stay
  // product-gated), and a timestamp-less entry leaves both
  // endpoints in place. The endpoints follow insertion order,
  // not timestamp order, exactly as the span does.
  els.logStatsFirstEntry.textContent =
    `First entry: ${stats.firstEntryAt ?? "none"}`;
  els.logStatsLastEntry.textContent =
    `Last entry: ${stats.lastEntryAt ?? "none"}`;
  // DETAIL-28: the per-product median-latency line splits
  // DETAIL-26's global median per product, rounded to whole
  // milliseconds, or "none" per product with no success carrying
  // a usable latency — the typical success DETAIL-8's mean and
  // DETAIL-10's range imply per product but do not state —
  // same always-renders shape as the other stats lines, so a
  // quiet session never changes the panel's shape.
  els.logStatsMedianLatencyByProduct.textContent =
    `Median successful latency by product: Vigiles ${stats.medianOkLatencyMsByProduct.vigiles === null ? "none" : `${Math.round(stats.medianOkLatencyMsByProduct.vigiles)} ms`} · Ignis ${stats.medianOkLatencyMsByProduct.ignis === null ? "none" : `${Math.round(stats.medianOkLatencyMsByProduct.ignis)} ms`} · Sanitas ${stats.medianOkLatencyMsByProduct.sanitas === null ? "none" : `${Math.round(stats.medianOkLatencyMsByProduct.sanitas)} ms`}`;
  // DETAIL-29: the per-product failure-cause-share line splits
  // DETAIL-9's counts into shares of all failures in the
  // session, rendered as whole percents, or "none" per cell
  // with no failures in the session — the slice DETAIL-9's
  // counts imply but do not state — same always-renders shape
  // as the other stats lines, so a quiet session never changes
  // the panel's shape, and successes never move a cell.
  els.logStatsFailedShareByStatusByProduct.textContent =
    `Failure-cause share of all failures by product: Vigiles Network ${stats.failedShareByStatusByProduct.vigiles.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusByProduct.vigiles.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusByProduct.vigiles.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusByProduct.vigiles.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusByProduct.vigiles.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusByProduct.vigiles.invalid_response * 100)}%`} · Ignis Network ${stats.failedShareByStatusByProduct.ignis.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusByProduct.ignis.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusByProduct.ignis.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusByProduct.ignis.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusByProduct.ignis.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusByProduct.ignis.invalid_response * 100)}%`} · Sanitas Network ${stats.failedShareByStatusByProduct.sanitas.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusByProduct.sanitas.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusByProduct.sanitas.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusByProduct.sanitas.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusByProduct.sanitas.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusByProduct.sanitas.invalid_response * 100)}%`}`;
  // DETAIL-31: the global failure-cause-share line collapses
  // DETAIL-29's nine product-cause cells into three shares of
  // all failures, rendered as whole percents, or "none" per
  // cause with no failures in the session — the slice
  // DETAIL-9's global counts imply but do not state — same
  // always-renders shape as the other stats lines, so a quiet
  // session never changes the panel's shape, and successes
  // never move a cell.
  els.logStatsFailedShareByStatus.textContent =
    `Failure-cause share of all failures: Network ${stats.failedShareByStatus.network_error === null ? "none" : `${Math.round(stats.failedShareByStatus.network_error * 100)}%`}, HTTP ${stats.failedShareByStatus.http_error === null ? "none" : `${Math.round(stats.failedShareByStatus.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatus.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatus.invalid_response * 100)}%`}`;
  // DETAIL-33: the per-product failure-cause-share line re-bases
  // DETAIL-29's cells on each product's own failures, rendered
  // as whole percents, or "none" per product with no failures
  // of that product — the slice DETAIL-9's counts imply but do
  // not state — same always-renders shape as the other stats
  // lines, so a quiet session never changes the panel's shape,
  // and successes never move a cell.
  els.logStatsFailedShareByStatusWithinProduct.textContent =
    `Failure-cause share of that product's failures: Vigiles Network ${stats.failedShareByStatusWithinProduct.vigiles.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusWithinProduct.vigiles.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusWithinProduct.vigiles.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusWithinProduct.vigiles.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusWithinProduct.vigiles.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusWithinProduct.vigiles.invalid_response * 100)}%`} · Ignis Network ${stats.failedShareByStatusWithinProduct.ignis.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusWithinProduct.ignis.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusWithinProduct.ignis.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusWithinProduct.ignis.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusWithinProduct.ignis.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusWithinProduct.ignis.invalid_response * 100)}%`} · Sanitas Network ${stats.failedShareByStatusWithinProduct.sanitas.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusWithinProduct.sanitas.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusWithinProduct.sanitas.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusWithinProduct.sanitas.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusWithinProduct.sanitas.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusWithinProduct.sanitas.invalid_response * 100)}%`}`;
  // DETAIL-32: the global first- and last-failure lines name
  // the endpoints DETAIL-23's failure span already spans —
  // the first and last recorded failure timestamps, any
  // cause, across products — or "none" per endpoint with no
  // usable failure, same always-renders shape as the other
  // stats lines, so a quiet session never changes the
  // panel's shape. No new stats fields: stats() already
  // exposes firstFailedAt/lastFailedAt, set by insertion
  // order, so a failure with an unknown or missing product
  // still opens and closes these endpoints (the per-product
  // DETAIL-19/7 buckets stay product-gated), a
  // timestamp-less failure leaves both endpoints in place,
  // and successes never move them — mirroring DETAIL-27's
  // first/last-entry lines and DETAIL-30's first-success
  // line, where the per-product first/last-failure lines
  // alone do not say it at a glance.
  els.logStatsFirstFailed.textContent =
    `First failure: ${stats.firstFailedAt ?? "none"}`;
  els.logStatsLastFailed.textContent =
    `Last failure: ${stats.lastFailedAt ?? "none"}`;
  // DETAIL-35: the per-product successful-latency-share line
  // re-bases DETAIL-8's latency sums on the session total,
  // rendered as whole percents, or "none" per product with no
  // usable ok latency in the session — the latency-total
  // slice DETAIL-8's means imply but do not state — same
  // always-renders shape as the other stats lines, so a
  // quiet session never changes the panel's shape, and
  // failures never move a share.
  els.logStatsOkLatencyShareByProduct.textContent =
    `Successful latency share by product: Vigiles ${stats.okLatencyShareByProduct.vigiles === null ? "none" : `${Math.round(stats.okLatencyShareByProduct.vigiles * 100)}%`} · Ignis ${stats.okLatencyShareByProduct.ignis === null ? "none" : `${Math.round(stats.okLatencyShareByProduct.ignis * 100)}%`} · Sanitas ${stats.okLatencyShareByProduct.sanitas === null ? "none" : `${Math.round(stats.okLatencyShareByProduct.sanitas * 100)}%`}`;
  // DETAIL-36: the usable-latency count lines name how many
  // successes carried a usable latency, globally and per
  // product — the count behind DETAIL-4's mean and DETAIL-8's
  // per-product means, so a mean over one measurement reads
  // differently from a mean over a hundred — same
  // always-renders shape as the other stats lines, so a quiet
  // session reads 0, never a missing line. No new counting
  // rule: stats() already counts them for the means, so
  // failures never contribute (even a failure carrying a
  // latency value), an ok entry with no finite latency is
  // skipped rather than counted as zero, and an ok entry
  // with an unknown or missing product counts globally but
  // moves no bucket.
  els.logStatsOkLatencyCount.textContent =
    `Successful latencies measured: ${stats.okLatencyCount}`;
  els.logStatsOkLatencyCountByProduct.textContent =
    `Successful latencies measured by product: Vigiles ${stats.okLatencyCountByProduct.vigiles} · Ignis ${stats.okLatencyCountByProduct.ignis} · Sanitas ${stats.okLatencyCountByProduct.sanitas}`;
  // DETAIL-37: the per-product successful-count-share line
  // re-bases DETAIL-1's ok counts on the session ok total,
  // rendered as whole percents, or "none" per product with no
  // successes in the session — the count slice DETAIL-1's raw
  // counts imply but do not state — same always-renders shape
  // as the other stats lines, so a quiet session never changes
  // the panel's shape, and failures never move a share.
  els.logStatsOkShareOfOkByProduct.textContent =
    `Successful share of successes by product: Vigiles ${stats.okShareOfOkByProduct.vigiles === null ? "none" : `${Math.round(stats.okShareOfOkByProduct.vigiles * 100)}%`} · Ignis ${stats.okShareOfOkByProduct.ignis === null ? "none" : `${Math.round(stats.okShareOfOkByProduct.ignis * 100)}%`} · Sanitas ${stats.okShareOfOkByProduct.sanitas === null ? "none" : `${Math.round(stats.okShareOfOkByProduct.sanitas * 100)}%`}`;
  // DETAIL-38: the usable-latency sum lines name the total
  // measured round-trip time, globally and per product — the
  // total behind DETAIL-4's mean, DETAIL-8's per-product
  // means, and DETAIL-35's per-product shares (the denominator
  // those shares divide by), rendered in whole milliseconds,
  // so a share of half the total reads against a real total —
  // same always-renders shape as the other stats lines, so a
  // quiet session reads 0 ms, never a missing line. No new
  // summing rule: stats() already sums them for the means and
  // shares, so failures never contribute (even a failure
  // carrying a latency value), an ok entry with no finite
  // latency is skipped rather than summed as zero, and an ok
  // entry with an unknown or missing product sums globally
  // but moves no bucket.
  els.logStatsOkLatencySum.textContent =
    `Total successful latency: ${Math.round(stats.okLatencySum)} ms`;
  els.logStatsOkLatencySumByProduct.textContent =
    `Total successful latency by product: Vigiles ${Math.round(stats.okLatencySumByProduct.vigiles)} ms · Ignis ${Math.round(stats.okLatencySumByProduct.ignis)} ms · Sanitas ${Math.round(stats.okLatencySumByProduct.sanitas)} ms`;
  // DETAIL-39: the per-product failed-count-share line
  // re-bases DETAIL-34's failed counts on the session
  // failed total, rendered as whole percents, or "none"
  // per product with no failures in the session — the
  // failure slice DETAIL-34's raw counts imply but do not
  // state — same always-renders shape as the other stats
  // lines, so a quiet session never changes the panel's
  // shape, and successes never move a share.
  els.logStatsFailedShareOfFailedByProduct.textContent =
    `Failed share of failures by product: Vigiles ${stats.failedShareOfFailedByProduct.vigiles === null ? "none" : `${Math.round(stats.failedShareOfFailedByProduct.vigiles * 100)}%`} · Ignis ${stats.failedShareOfFailedByProduct.ignis === null ? "none" : `${Math.round(stats.failedShareOfFailedByProduct.ignis * 100)}%`} · Sanitas ${stats.failedShareOfFailedByProduct.sanitas === null ? "none" : `${Math.round(stats.failedShareOfFailedByProduct.sanitas * 100)}%`}`;
  // DETAIL-40: the per-product failed-share-of-all-entries
  // line re-bases DETAIL-34's failed counts on the session
  // entry total, rendered as whole percents, or "none" per
  // product on an empty log — the failure slice DETAIL-34's
  // raw counts imply but do not state, and the failed
  // mirror of DETAIL-37's success shares — same
  // always-renders shape as the other stats lines, so a
  // quiet session never changes the panel's shape, and
  // successes never move a share (they sit in the
  // denominator only). A success-only log reads 0% per
  // product, never "none".
  els.logStatsFailedShareOfEntriesByProduct.textContent =
    `Failed share of all entries by product: Vigiles ${stats.failedShareOfEntriesByProduct.vigiles === null ? "none" : `${Math.round(stats.failedShareOfEntriesByProduct.vigiles * 100)}%`} · Ignis ${stats.failedShareOfEntriesByProduct.ignis === null ? "none" : `${Math.round(stats.failedShareOfEntriesByProduct.ignis * 100)}%`} · Sanitas ${stats.failedShareOfEntriesByProduct.sanitas === null ? "none" : `${Math.round(stats.failedShareOfEntriesByProduct.sanitas * 100)}%`}`;
  // DETAIL-41: the per-product successful-count-share line
  // re-bases DETAIL-1's ok counts on the session entry
  // total, rendered as whole percents, or "none" per product
  // on an empty log — the entry-total slice DETAIL-37's
  // ok-total shares imply but do not state, and the success
  // mirror of DETAIL-40's failed-share line — same
  // always-renders shape as the other stats lines, so a
  // quiet session never changes the panel's shape, and
  // failures sit in the denominator but move no bucket.
  els.logStatsOkShareOfTotalByProduct.textContent =
    `Successful share of all entries by product: Vigiles ${stats.okShareOfTotalByProduct.vigiles === null ? "none" : `${Math.round(stats.okShareOfTotalByProduct.vigiles * 100)}%`} · Ignis ${stats.okShareOfTotalByProduct.ignis === null ? "none" : `${Math.round(stats.okShareOfTotalByProduct.ignis * 100)}%`} · Sanitas ${stats.okShareOfTotalByProduct.sanitas === null ? "none" : `${Math.round(stats.okShareOfTotalByProduct.sanitas * 100)}%`}`;
  // DETAIL-42: the per-product failure-cause-share-of-all-entries
  // line re-bases DETAIL-9's product-cause counts on the session
  // entry total, rendered as whole percents, or "none" per cell
  // on an empty log — the entry-total slice DETAIL-29's
  // failed-total cells imply but do not state, and the cause
  // split of DETAIL-40's failed-share line — same
  // always-renders shape as the other stats lines, so a quiet
  // session never changes the panel's shape, and successes
  // never move a cell (they sit in the denominator only). A
  // success-only log reads 0% per cell, never "none".
  els.logStatsFailedShareByStatusOfEntriesByProduct.textContent =
    `Failure-cause share of all entries by product: Vigiles Network ${stats.failedShareByStatusOfEntriesByProduct.vigiles.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesByProduct.vigiles.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusOfEntriesByProduct.vigiles.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesByProduct.vigiles.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusOfEntriesByProduct.vigiles.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesByProduct.vigiles.invalid_response * 100)}%`} · Ignis Network ${stats.failedShareByStatusOfEntriesByProduct.ignis.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesByProduct.ignis.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusOfEntriesByProduct.ignis.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesByProduct.ignis.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusOfEntriesByProduct.ignis.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesByProduct.ignis.invalid_response * 100)}%`} · Sanitas Network ${stats.failedShareByStatusOfEntriesByProduct.sanitas.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesByProduct.sanitas.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusOfEntriesByProduct.sanitas.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesByProduct.sanitas.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusOfEntriesByProduct.sanitas.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesByProduct.sanitas.invalid_response * 100)}%`}`;
  // DETAIL-43: the global failure-cause-share-of-all-entries
  // line collapses DETAIL-42's nine product-cause cells into
  // three shares of all entries, rendered as whole percents,
  // or "none" per cause on an empty log — the entry-total
  // slice DETAIL-31's failed-total shares imply but do not
  // state — same always-renders shape as the other stats
  // lines, so a quiet session never changes the panel's
  // shape, and successes never move a cell (they sit in the
  // denominator only). A success-only log reads 0% per cause,
  // never "none", and the three cells always sum to the
  // global failed share, unknown-product failures included.
  els.logStatsFailedShareByStatusOfEntries.textContent =
    `Failure-cause share of all entries: Network ${stats.failedShareByStatusOfEntries.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntries.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusOfEntries.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntries.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusOfEntries.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntries.invalid_response * 100)}%`}`;
  // DETAIL-44: the per-product failure-cause-share-of-that-
  // product's-entries line re-bases DETAIL-9's product-cause
  // counts on each product's own entry total, rendered as
  // whole percents, or "none" per product with no entries of
  // that product — the within-product slice DETAIL-42's
  // global-entry cells imply but do not state, and the cause
  // split of DETAIL-12's per-product failed-share line.
  // A success-only product reads 0% per cause, never "none".
  els.logStatsFailedShareByStatusOfEntriesWithinProduct.textContent =
    `Failure-cause share of that product's entries by product: Vigiles Network ${stats.failedShareByStatusOfEntriesWithinProduct.vigiles.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesWithinProduct.vigiles.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusOfEntriesWithinProduct.vigiles.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesWithinProduct.vigiles.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusOfEntriesWithinProduct.vigiles.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesWithinProduct.vigiles.invalid_response * 100)}%`} · Ignis Network ${stats.failedShareByStatusOfEntriesWithinProduct.ignis.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesWithinProduct.ignis.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusOfEntriesWithinProduct.ignis.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesWithinProduct.ignis.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusOfEntriesWithinProduct.ignis.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesWithinProduct.ignis.invalid_response * 100)}%`} · Sanitas Network ${stats.failedShareByStatusOfEntriesWithinProduct.sanitas.network_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesWithinProduct.sanitas.network_error * 100)}%`}, HTTP ${stats.failedShareByStatusOfEntriesWithinProduct.sanitas.http_error === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesWithinProduct.sanitas.http_error * 100)}%`}, Invalid response ${stats.failedShareByStatusOfEntriesWithinProduct.sanitas.invalid_response === null ? "none" : `${Math.round(stats.failedShareByStatusOfEntriesWithinProduct.sanitas.invalid_response * 100)}%`}`;
  // DETAIL-45: the per-product usable-latency-count-share
  // line re-bases DETAIL-36's counts on the session's total
  // usable-latency count, rendered as whole percents, or
  // "none" per product with no usable ok latency in the
  // session — the count slice DETAIL-35's latency-sum
  // shares imply but do not state, so a product supplying
  // most measurements reads differently from one eating
  // most measured time. Failures never move a share.
  els.logStatsOkLatencyCountShareByProduct.textContent =
    `Successful latency-measurement share by product: Vigiles ${stats.okLatencyCountShareByProduct.vigiles === null ? "none" : `${Math.round(stats.okLatencyCountShareByProduct.vigiles * 100)}%`} · Ignis ${stats.okLatencyCountShareByProduct.ignis === null ? "none" : `${Math.round(stats.okLatencyCountShareByProduct.ignis * 100)}%`} · Sanitas ${stats.okLatencyCountShareByProduct.sanitas === null ? "none" : `${Math.round(stats.okLatencyCountShareByProduct.sanitas * 100)}%`}`;
  // DETAIL-46: the per-product entry-span-share-of-session-window
  // line re-bases DETAIL-17's per-product entry spans on the
  // session's global entry span, rendered as whole percents,
  // or "none" per product with no usable session window or no
  // usable timestamp pair — the window-coverage companion to
  // DETAIL-13's entry-count-share line. Raw ratios, never
  // clamped: a share above 100% or below 0% means timestamps
  // ran out of insertion order, and the three shares do not
  // sum to 100% because product windows overlap.
  els.logStatsEntrySpanShareByProduct.textContent =
    `Entry-span share of session window by product: Vigiles ${stats.entrySpanShareByProduct.vigiles === null ? "none" : `${Math.round(stats.entrySpanShareByProduct.vigiles * 100)}%`} · Ignis ${stats.entrySpanShareByProduct.ignis === null ? "none" : `${Math.round(stats.entrySpanShareByProduct.ignis * 100)}%`} · Sanitas ${stats.entrySpanShareByProduct.sanitas === null ? "none" : `${Math.round(stats.entrySpanShareByProduct.sanitas * 100)}%`}`;
  // DETAIL-47: the per-product usable-latency-count-share-
  // of-all-entries line re-bases DETAIL-36's counts on the
  // session's total entries, rendered as whole percents, or
  // "none" per product only on an empty log — the
  // entry-total slice DETAIL-45's measurement-total shares
  // imply but do not state, so a product whose measurements
  // are a small slice of everything recorded reads
  // differently from one supplying most measurements in a
  // quiet session. Failures and latency-less successes
  // never move a share; they sit in the denominator only.
  // A failure-only log reads 0% per product, never "none".
  els.logStatsOkLatencyCountShareOfEntriesByProduct.textContent =
    `Successful latency-measurement share of all entries by product: Vigiles ${stats.okLatencyCountShareOfEntriesByProduct.vigiles === null ? "none" : `${Math.round(stats.okLatencyCountShareOfEntriesByProduct.vigiles * 100)}%`} · Ignis ${stats.okLatencyCountShareOfEntriesByProduct.ignis === null ? "none" : `${Math.round(stats.okLatencyCountShareOfEntriesByProduct.ignis * 100)}%`} · Sanitas ${stats.okLatencyCountShareOfEntriesByProduct.sanitas === null ? "none" : `${Math.round(stats.okLatencyCountShareOfEntriesByProduct.sanitas * 100)}%`}`;
  // DETAIL-48: the per-product ok-span-share-of-ok-window
  // line re-bases DETAIL-21's per-product ok spans on the
  // session's global ok span, rendered as whole percents,
  // or "none" per product with no usable ok window or no
  // usable timestamp pair — the ok-only companion to
  // DETAIL-46's entry-span-share line. Raw ratios, never
  // clamped: a share above 100% or below 0% means
  // timestamps ran out of insertion order, and the three
  // shares do not sum to 100% because product ok windows
  // overlap. Failures never move a share.
  els.logStatsOkSpanShareByProduct.textContent =
    `Success-span share of ok window by product: Vigiles ${stats.okSpanShareByProduct.vigiles === null ? "none" : `${Math.round(stats.okSpanShareByProduct.vigiles * 100)}%`} · Ignis ${stats.okSpanShareByProduct.ignis === null ? "none" : `${Math.round(stats.okSpanShareByProduct.ignis * 100)}%`} · Sanitas ${stats.okSpanShareByProduct.sanitas === null ? "none" : `${Math.round(stats.okSpanShareByProduct.sanitas * 100)}%`}`;
  // DETAIL-49: the global usable-latency-count-share-
  // of-all-entries line collapses DETAIL-47's three
  // shares into one, rendered as a whole percent, or
  // "none" only on an empty log — the single number a
  // product split cannot state, so a session where half
  // of everything recorded carries a usable latency
  // reads at a glance. A failure-only log reads 0%,
  // never "none", and an unknown-product success still
  // moves this share even though it moves no bucket.
  els.logStatsOkLatencyCountShareOfEntries.textContent =
    `Successful latency-measurement share of all entries: ${stats.okLatencyCountShareOfEntries === null ? "none" : `${Math.round(stats.okLatencyCountShareOfEntries * 100)}%`}`;
  // DETAIL-50: the per-product failed-span-share-of-
  // failed-window line re-bases DETAIL-20's per-product
  // failed spans on the session's global failed span,
  // rendered as whole percents, or "none" per product
  // with no usable failed window or no usable timestamp
  // pair — the failed-only mirror of DETAIL-48's
  // ok-span-share line. Raw ratios, never clamped: a
  // share above 100% or below 0% means timestamps ran
  // out of insertion order, and the three shares do not
  // sum to 100% because product failed windows overlap.
  // Successes never move a share.
  els.logStatsFailedSpanShareByProduct.textContent =
    `Failure-span share of failed window by product: Vigiles ${stats.failedSpanShareByProduct.vigiles === null ? "none" : `${Math.round(stats.failedSpanShareByProduct.vigiles * 100)}%`} · Ignis ${stats.failedSpanShareByProduct.ignis === null ? "none" : `${Math.round(stats.failedSpanShareByProduct.ignis * 100)}%`} · Sanitas ${stats.failedSpanShareByProduct.sanitas === null ? "none" : `${Math.round(stats.failedSpanShareByProduct.sanitas * 100)}%`}`;
  // DETAIL-51: the global usable-latency-count-share-
  // of-ok-successes line re-bases DETAIL-36's global
  // count on the session's ok total, rendered as a whole
  // percent, or "none" only when the session holds no
  // successes at all — the success-only slice DETAIL-49's
  // entry-total share implies but does not state, so a
  // session where most successes carry a latency reads
  // differently from one where the same measurements sit
  // in a failure-heavy log. A success-only log with no
  // finite latency reads 0%, never "none", and failures
  // move neither side of the share.
  els.logStatsOkLatencyCountShareOfOk.textContent =
    `Successful latency-measurement share of successes: ${stats.okLatencyCountShareOfOk === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOk * 100)}%`}`;
  // DETAIL-52: the per-product usable-latency-count-share-
  // of-ok-successes line splits DETAIL-51's global share
  // by product, rendered as whole percents, or "none"
  // per product only when the session holds no successes
  // at all — the product slice DETAIL-51's single number
  // implies but does not state, so a session where
  // Vigiles measurements are half of all successes reads
  // differently from one where Ignis supplied them. A
  // success-only log with no finite latency reads 0% per
  // product, never "none", and failures move no share.
  els.logStatsOkLatencyCountShareOfOkByProduct.textContent =
    `Successful latency-measurement share of successes by product: Vigiles ${stats.okLatencyCountShareOfOkByProduct.vigiles === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOkByProduct.vigiles * 100)}%`} · Ignis ${stats.okLatencyCountShareOfOkByProduct.ignis === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOkByProduct.ignis * 100)}%`} · Sanitas ${stats.okLatencyCountShareOfOkByProduct.sanitas === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOkByProduct.sanitas * 100)}%`}`;
  // DETAIL-53: the per-product ok-span-share-of-entry-
  // window line re-bases DETAIL-21's per-product ok spans
  // on the session's global entry span, rendered as whole
  // percents, or "none" per product with no usable entry
  // window or no usable timestamp pair — the entry-window
  // re-basing of DETAIL-48's ok-span-share line. Raw
  // ratios, never clamped: a share above 100% or below 0%
  // means timestamps ran out of insertion order, and the
  // three shares do not sum to 100% because product ok
  // windows overlap. Failures stretch the denominator
  // without moving any bucket.
  els.logStatsOkSpanShareOfEntryWindowByProduct.textContent =
    `Success-span share of entry window by product: Vigiles ${stats.okSpanShareOfEntryWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.okSpanShareOfEntryWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.okSpanShareOfEntryWindowByProduct.ignis === null ? "none" : `${Math.round(stats.okSpanShareOfEntryWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.okSpanShareOfEntryWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.okSpanShareOfEntryWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-54: the per-product usable-latency-count-share-
  // of-that-product's-own-successes line re-bases
  // DETAIL-36's counts on each product's own ok total,
  // rendered as whole percents, or "none" per product
  // with no successes of that product — the within-
  // product slice DETAIL-52's global-ok shares imply
  // but do not state, so a product whose own successes
  // are all measured reads 100% whatever its share of
  // the session. A product with successes but no finite
  // latency reads 0%, never "none", and failures move
  // no share.
  els.logStatsOkLatencyCountShareOfOwnOkByProduct.textContent =
    `Successful latency-measurement share of that product's own successes by product: Vigiles ${stats.okLatencyCountShareOfOwnOkByProduct.vigiles === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOwnOkByProduct.vigiles * 100)}%`} · Ignis ${stats.okLatencyCountShareOfOwnOkByProduct.ignis === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOwnOkByProduct.ignis * 100)}%`} · Sanitas ${stats.okLatencyCountShareOfOwnOkByProduct.sanitas === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOwnOkByProduct.sanitas * 100)}%`}`;
  // DETAIL-55: the per-product failed-span-share-of-
  // entry-window line re-bases DETAIL-20's per-product
  // failed spans on the session's global entry span,
  // rendered as whole percents, or "none" per product
  // with no usable entry window or no usable timestamp
  // pair — the failed mirror of DETAIL-53's ok-span-
  // share line, and the entry-window re-basing of
  // DETAIL-50's failed-span-share line. Raw ratios,
  // never clamped: a share above 100% or below 0%
  // means timestamps ran out of insertion order, and
  // the three shares do not sum to 100% because
  // product failed windows overlap. Successes stretch
  // the denominator without moving any bucket.
  els.logStatsFailedSpanShareOfEntryWindowByProduct.textContent =
    `Failure-span share of entry window by product: Vigiles ${stats.failedSpanShareOfEntryWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.failedSpanShareOfEntryWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.failedSpanShareOfEntryWindowByProduct.ignis === null ? "none" : `${Math.round(stats.failedSpanShareOfEntryWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.failedSpanShareOfEntryWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.failedSpanShareOfEntryWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-56 (renumbered after Rowan's distinct DETAIL-55 landed first): the per-product usable-latency-count-share-
  // of-that-product's-own-entries line re-bases
  // DETAIL-36's counts on each product's own entry total,
  // rendered as whole percents, or "none" per product
  // with no entries of that product — the within-
  // product slice DETAIL-47's entry-total shares imply
  // but do not state, so a product whose every entry is
  // a measured success reads 100% whatever its share of
  // the session. A product with entries but no finite
  // latency reads 0%, never "none", and failures sit in
  // the denominator but move no bucket.
  els.logStatsOkLatencyCountShareOfOwnEntriesByProduct.textContent =
    `Successful latency-measurement share of that product's own entries by product: Vigiles ${stats.okLatencyCountShareOfOwnEntriesByProduct.vigiles === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOwnEntriesByProduct.vigiles * 100)}%`} · Ignis ${stats.okLatencyCountShareOfOwnEntriesByProduct.ignis === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOwnEntriesByProduct.ignis * 100)}%`} · Sanitas ${stats.okLatencyCountShareOfOwnEntriesByProduct.sanitas === null ? "none" : `${Math.round(stats.okLatencyCountShareOfOwnEntriesByProduct.sanitas * 100)}%`}`;
  // DETAIL-57: the global failure-span-share-of-entry-
  // window line re-bases DETAIL-23's global failed span
  // on the session's global entry span, rendered as a
  // whole percent, or "none" with no usable entry window
  // or no usable failed span — the collapsed form of
  // DETAIL-55's per-product shares, so failures covering
  // half the whole window read at a glance. Raw ratio,
  // never clamped: above 100% or below 0% means
  // timestamps ran out of insertion order, and this is
  // not the sum of DETAIL-55's shares because product
  // failed windows overlap. Successes stretch the
  // denominator without moving the numerator, and an
  // unknown- or missing-product failure still moves
  // this product-blind numerator, unlike DETAIL-55.
  els.logStatsFailedSpanShareOfEntryWindow.textContent =
    `Failure-span share of entry window: ${stats.failedSpanShareOfEntryWindow === null ? "none" : `${Math.round(stats.failedSpanShareOfEntryWindow * 100)}%`}`;
  // DETAIL-58: the global success-span-share-of-entry-
  // window line re-bases DETAIL-22's global ok span on
  // the session's global entry span, rendered as a
  // whole percent, or "none" with no usable entry window
  // or no usable ok span — the ok mirror of DETAIL-57
  // and the collapsed form of DETAIL-53's per-product
  // shares, so successes covering half the whole window
  // read at a glance. Raw ratio, never clamped: above
  // 100% or below 0% means timestamps ran out of
  // insertion order, and this is not the sum of
  // DETAIL-53's shares because product ok windows
  // overlap. Failures stretch the denominator without
  // moving the numerator, and an unknown- or
  // missing-product success still moves this
  // product-blind numerator, unlike DETAIL-53.
  els.logStatsOkSpanShareOfEntryWindow.textContent =
    `Success-span share of entry window: ${stats.okSpanShareOfEntryWindow === null ? "none" : `${Math.round(stats.okSpanShareOfEntryWindow * 100)}%`}`;
  // DETAIL-59 (renumbered after Rowan's distinct DETAIL-58 landed first): the per-product failure-span-share-of-
  // that-product's-own-entry-window line re-bases
  // DETAIL-20's per-product failed spans on each
  // product's own entry span, rendered as whole
  // percents, or "none" per product with no usable
  // own entry window or no usable timestamp pair —
  // the within-product slice DETAIL-55's global-
  // entry shares imply but do not state, so a
  // product whose failures span half of everything
  // it recorded reads that at a glance whatever its
  // share of the session. A product with entries
  // but no failures reads 0%, never "none", and
  // other products' entries move no share. Raw
  // ratios, never clamped: above 100% or below 0%
  // means timestamps ran out of insertion order.
  els.logStatsFailedSpanShareOfOwnEntryWindowByProduct.textContent =
    `Failure-span share of that product's own entry window by product: Vigiles ${stats.failedSpanShareOfOwnEntryWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.failedSpanShareOfOwnEntryWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.failedSpanShareOfOwnEntryWindowByProduct.ignis === null ? "none" : `${Math.round(stats.failedSpanShareOfOwnEntryWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.failedSpanShareOfOwnEntryWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.failedSpanShareOfOwnEntryWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-60: the per-product success-span-share-of-
  // that-product's-own-entry-window line re-bases
  // DETAIL-21's per-product ok spans on each
  // product's own entry span, rendered as whole
  // percents, or "none" per product with no usable
  // own entry window or no usable timestamp pair —
  // the ok mirror of DETAIL-59's failed shares, so a
  // product whose successes span half of everything
  // it recorded reads that at a glance whatever its
  // share of the session. A product with entries
  // but no successes reads 0%, never "none", and
  // other products' entries move no share. Raw
  // ratios, never clamped: above 100% or below 0%
  // means timestamps ran out of insertion order.
  els.logStatsOkSpanShareOfOwnEntryWindowByProduct.textContent =
    `Success-span share of that product's own entry window by product: Vigiles ${stats.okSpanShareOfOwnEntryWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.okSpanShareOfOwnEntryWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.okSpanShareOfOwnEntryWindowByProduct.ignis === null ? "none" : `${Math.round(stats.okSpanShareOfOwnEntryWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.okSpanShareOfOwnEntryWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.okSpanShareOfOwnEntryWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-61: the per-product success-share-of-
  // that-product's-own-entries line re-bases
  // DETAIL-1's per-product ok counts on each
  // product's own entry total, rendered as whole
  // percents, or "none" per product with no entries
  // of that product — the product's own success
  // rate, the within-product slice DETAIL-41's
  // entry-total shares imply but do not state, so a
  // product that succeeded on three of its own four
  // entries reads 75% whatever its share of the
  // session. A product with entries but no successes
  // reads 0%, never "none", and other products'
  // entries move no share.
  els.logStatsOkShareOfOwnEntriesByProduct.textContent =
    `Success share of that product's own entries by product: Vigiles ${stats.okShareOfOwnEntriesByProduct.vigiles === null ? "none" : `${Math.round(stats.okShareOfOwnEntriesByProduct.vigiles * 100)}%`} · Ignis ${stats.okShareOfOwnEntriesByProduct.ignis === null ? "none" : `${Math.round(stats.okShareOfOwnEntriesByProduct.ignis * 100)}%`} · Sanitas ${stats.okShareOfOwnEntriesByProduct.sanitas === null ? "none" : `${Math.round(stats.okShareOfOwnEntriesByProduct.sanitas * 100)}%`}`;
  // DETAIL-62: the per-product failure-span-share-
  // of-that-product's-own-success-window line re-bases
  // DETAIL-20's per-product failed spans on each
  // product's own DETAIL-21 ok span, rendered as whole
  // percents, or "none" per product with no usable own
  // success window or no usable failed timestamp pair
  // — the cross-span slice DETAIL-59/60's own-entry
  // shares imply but do not state, so a product whose
  // failures stretch across half of everything it
  // succeeded across reads 50% whatever its share of
  // the session. A product with successes but no
  // failures reads 0%, never "none", and other
  // products' entries move no share. Raw ratios, never
  // clamped: above 100% or below 0% means timestamps
  // ran out of insertion order.
  els.logStatsFailedSpanShareOfOwnOkWindowByProduct.textContent =
    `Failure-span share of that product's own success window by product: Vigiles ${stats.failedSpanShareOfOwnOkWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.failedSpanShareOfOwnOkWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.failedSpanShareOfOwnOkWindowByProduct.ignis === null ? "none" : `${Math.round(stats.failedSpanShareOfOwnOkWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.failedSpanShareOfOwnOkWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.failedSpanShareOfOwnOkWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-63: the per-product success-span-share-
  // of-that-product's-own-failure-window line re-bases
  // DETAIL-21's per-product ok spans on each
  // product's own DETAIL-20 failed span, rendered as whole
  // percents, or "none" per product with no usable own
  // failure window or no usable ok timestamp pair
  // — the mirror of DETAIL-62, so a product whose
  // successes stretch across half of everything it
  // failed across reads 50% whatever its share of
  // the session. A product with failures but no
  // successes reads 0%, never "none", and other
  // products' entries move no share. Raw ratios, never
  // clamped: above 100% or below 0% means timestamps
  // ran out of insertion order.
  els.logStatsOkSpanShareOfOwnFailedWindowByProduct.textContent =
    `Success-span share of that product's own failure window by product: Vigiles ${stats.okSpanShareOfOwnFailedWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.okSpanShareOfOwnFailedWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.okSpanShareOfOwnFailedWindowByProduct.ignis === null ? "none" : `${Math.round(stats.okSpanShareOfOwnFailedWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.okSpanShareOfOwnFailedWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.okSpanShareOfOwnFailedWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-64: the global success-span-share-of-
  // failure-window line re-bases DETAIL-22's global
  // ok span on DETAIL-23's global failed span,
  // rendered as a whole percent, or "none" with no
  // usable failed window or no usable ok span —
  // the cross-span re-base DETAIL-57's and
  // DETAIL-58's entry-window shares imply but do
  // not state, so a session where successes
  // stretched twice as long as failures reads that
  // at a glance. A session with failures but no
  // successes reads 0%, never "none". Raw ratio,
  // never clamped: above 100% or below 0% means
  // timestamps ran out of insertion order.
  els.logStatsOkSpanShareOfFailedWindow.textContent =
    `Success-span share of failure window: ${stats.okSpanShareOfFailedWindow === null ? "none" : `${Math.round(stats.okSpanShareOfFailedWindow * 100)}%`}`;
  // DETAIL-65: the global failure-span-share-of-
  // ok-window line re-bases DETAIL-23's global
  // failed span on DETAIL-22's global ok span,
  // rendered as a whole percent, or "none" with no
  // usable ok window or no usable failed span —
  // the mirror of DETAIL-64, so a session where
  // failures stretched twice as long as successes
  // reads that at a glance. A session with
  // successes but no failures reads 0%, never
  // "none". Raw ratio, never clamped: above 100%
  // or below 0% means timestamps ran out of
  // insertion order.
  els.logStatsFailedSpanShareOfOkWindow.textContent =
    `Failure-span share of success window: ${stats.failedSpanShareOfOkWindow === null ? "none" : `${Math.round(stats.failedSpanShareOfOkWindow * 100)}%`}`;
  // DETAIL-66: the global entry-span-share-of-
  // success-window line re-bases DETAIL-24's global
  // entry span on DETAIL-22's global ok span,
  // rendered as a whole percent, or "none" with no
  // usable ok window — the recording window read
  // against the success window, the inverse
  // direction of DETAIL-57's line. Above 100% is
  // the normal case (the recording outlasts its
  // successes); exactly 100% means every entry was
  // a success spanning the whole recording. Raw
  // ratio, never clamped: below 100% or below 0%
  // means timestamps ran out of insertion order.
  els.logStatsEntrySpanShareOfOkWindow.textContent =
    `Entry-span share of success window: ${stats.entrySpanShareOfOkWindow === null ? "none" : `${Math.round(stats.entrySpanShareOfOkWindow * 100)}%`}`;
  // DETAIL-67: the global entry-span-share-of-
  // failure-window line re-bases DETAIL-24's global
  // entry span on DETAIL-23's global failed span,
  // rendered as a whole percent, or "none" with no
  // usable failed window or no usable entry span —
  // the mirror of DETAIL-66, the inverse
  // direction of DETAIL-57's line. Above 100% is
  // the normal case (the recording outlasts its
  // failures); exactly 100% means every entry was
  // a failure spanning the whole recording. Raw
  // ratio, never clamped: below 100% or below 0%
  // means timestamps ran out of insertion order.
  els.logStatsEntrySpanShareOfFailedWindow.textContent =
    `Entry-span share of failure window: ${stats.entrySpanShareOfFailedWindow === null ? "none" : `${Math.round(stats.entrySpanShareOfFailedWindow * 100)}%`}`;
  // DETAIL-68: the per-product entry-span-share-of-
  // that-product's-own-success-window line re-bases
  // DETAIL-17's per-product entry spans on each
  // product's own DETAIL-21 ok span, rendered as whole
  // percents, or "none" per product with no usable own
  // success window or no usable own entry span —
  // the within-product re-base of DETAIL-66, so a
  // product whose recording stretches twice as long
  // as its own successes reads 200% whatever its
  // share of the session. A product whose every
  // entry succeeded reads 100%, and other products'
  // entries move no share. Raw ratios, never
  // clamped: above 100% is the normal case, below
  // 100% or below 0% means timestamps ran out of
  // insertion order.
  els.logStatsEntrySpanShareOfOwnOkWindowByProduct.textContent =
    `Entry-span share of that product's own success window by product: Vigiles ${stats.entrySpanShareOfOwnOkWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.entrySpanShareOfOwnOkWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.entrySpanShareOfOwnOkWindowByProduct.ignis === null ? "none" : `${Math.round(stats.entrySpanShareOfOwnOkWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.entrySpanShareOfOwnOkWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.entrySpanShareOfOwnOkWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-69: the per-product entry-span-share-
  // of-that-product's-own-failure-window line re-bases
  // DETAIL-17's per-product entry spans on each
  // product's own DETAIL-20 failed span, rendered as whole
  // percents, or "none" per product with no usable own
  // failure window or no usable own entry timestamp
  // pair — the mirror of DETAIL-68, the within-product
  // mirror of DETAIL-67, so a product whose recording
  // ran twice everything it itself failed across reads
  // 200% whatever its share of the session. A product
  // whose every entry failed reads 100%, and other
  // products' entries move no share. Raw ratios, never
  // clamped: above 100% is the normal case, below
  // 100% or below 0% means timestamps ran out of
  // insertion order.
  els.logStatsEntrySpanShareOfOwnFailedWindowByProduct.textContent =
    `Entry-span share of that product's own failure window by product: Vigiles ${stats.entrySpanShareOfOwnFailedWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.entrySpanShareOfOwnFailedWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.entrySpanShareOfOwnFailedWindowByProduct.ignis === null ? "none" : `${Math.round(stats.entrySpanShareOfOwnFailedWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.entrySpanShareOfOwnFailedWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.entrySpanShareOfOwnFailedWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-70: the per-product entry-span-share-
  // of-success-window line re-bases DETAIL-17's
  // per-product entry spans on the session's global
  // DETAIL-22 ok span, rendered as whole percents,
  // or "none" per product with no usable global ok
  // window or no usable own entry timestamp pair
  // — the entry-side companion to DETAIL-48, the
  // global-window mirror of DETAIL-68, so a product
  // whose recording ran twice the whole success
  // window reads 200% whatever its share of the
  // successes. A failure-only product still covers
  // the window its failures stretched across, and
  // other products' entries move no share. Raw
  // ratios, never clamped: above 100% is the normal
  // case, below 100% or below 0% means timestamps
  // ran out of insertion order.
  els.logStatsEntrySpanShareOfOkWindowByProduct.textContent =
    `Entry-span share of success window by product: Vigiles ${stats.entrySpanShareOfOkWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.entrySpanShareOfOkWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.entrySpanShareOfOkWindowByProduct.ignis === null ? "none" : `${Math.round(stats.entrySpanShareOfOkWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.entrySpanShareOfOkWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.entrySpanShareOfOkWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-71: the per-product entry-span-share-of-
  // the-global-failure-window line re-bases
  // DETAIL-17's per-product entry spans on the
  // global DETAIL-23 failed span, rendered as whole
  // percents, or "none" per product with no usable
  // global failed window or no usable own entry
  // timestamp pair — the failed-side mirror of
  // DETAIL-70, so a product whose recording ran
  // twice the whole failure window reads 200%
  // whatever its share of the failures. A
  // success-only product still covers the window
  // its successes stretched across, and other
  // products' entries move no share. Raw ratios,
  // never clamped: above 100% is the normal case,
  // below 100% or below 0% means timestamps ran
  // out of insertion order.
  els.logStatsEntrySpanShareOfFailedWindowByProduct.textContent =
    `Entry-span share of failure window by product: Vigiles ${stats.entrySpanShareOfFailedWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.entrySpanShareOfFailedWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.entrySpanShareOfFailedWindowByProduct.ignis === null ? "none" : `${Math.round(stats.entrySpanShareOfFailedWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.entrySpanShareOfFailedWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.entrySpanShareOfFailedWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-72: the per-product failed-span shares of
  // the global DETAIL-22 ok window, rendered as whole
  // percents, or "none" per product with no usable
  // global ok window or no usable own failed
  // timestamp pair — the by-product split of
  // DETAIL-65, so a product whose failures stretch
  // across twice the whole success window reads 200%
  // whatever its share of the failures. Successes
  // move no bucket, only the denominator, and other
  // products' failures move no share. Raw ratios,
  // never clamped: above 100% is the normal case,
  // below 100% or below 0% means timestamps ran
  // out of insertion order.
  els.logStatsFailedSpanShareOfOkWindowByProduct.textContent =
    `Failure-span share of success window by product: Vigiles ${stats.failedSpanShareOfOkWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.failedSpanShareOfOkWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.failedSpanShareOfOkWindowByProduct.ignis === null ? "none" : `${Math.round(stats.failedSpanShareOfOkWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.failedSpanShareOfOkWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.failedSpanShareOfOkWindowByProduct.sanitas * 100)}%`}`;
  // DETAIL-73: the per-product ok-span shares of
  // the global DETAIL-23 failed window, rendered as
  // whole percents, or "none" per product with no
  // usable global failed window or no usable own
  // ok timestamp pair — the by-product split of
  // DETAIL-64, so a product whose successes stretch
  // across twice the whole failure window reads 200%
  // whatever its share of the successes. Failures
  // move no bucket, only the denominator, and other
  // products' successes move no share. Raw ratios,
  // never clamped: above 100% is the normal case,
  // below 100% or below 0% means timestamps ran
  // out of insertion order.
  els.logStatsOkSpanShareOfFailedWindowByProduct.textContent =
    `Success-span share of failure window by product: Vigiles ${stats.okSpanShareOfFailedWindowByProduct.vigiles === null ? "none" : `${Math.round(stats.okSpanShareOfFailedWindowByProduct.vigiles * 100)}%`} · Ignis ${stats.okSpanShareOfFailedWindowByProduct.ignis === null ? "none" : `${Math.round(stats.okSpanShareOfFailedWindowByProduct.ignis * 100)}%`} · Sanitas ${stats.okSpanShareOfFailedWindowByProduct.sanitas === null ? "none" : `${Math.round(stats.okSpanShareOfFailedWindowByProduct.sanitas * 100)}%`}`;
  // IGNIS-ONEOFONE-1: the look-alike scoreboard re-reads the same
  // log entries updateLogStats already runs on — no new stats field,
  // no new data — and renders the Ignis-only panel from recorded
  // assessments alone. An empty session reads all zeros, a held
  // session (no model calls) stays zeros rather than inventing a
  // reading, and failures never move a bucket. The panel itself is
  // hidden under Vigiles and Sanitas by CSS, so this line only ever
  // shows under Ignis.
  const scoreboard = ignisLookAlikeScoreboard(log.entries());
  els.ignisScoreboard.textContent =
    `Look-alikes — Steam or fog ${scoreboard.steamOrFog} · Flame-like lighting ${scoreboard.flameLikeLighting} | Hazards — Visible smoke ${scoreboard.visibleSmoke} · Visible flame ${scoreboard.visibleFlame} | Other — Obscured or distant hazard ${scoreboard.obscuredOrDistant} · No hazard visible ${scoreboard.noHazard} · Indeterminate ${scoreboard.indeterminate}`;
  // IGNIS-ONEOFONE-2: the reported-confidence spread re-reads the
  // same log entries — no new stats field, no new data — and renders
  // the Ignis-only panel from recorded observation confidences
  // alone. Bands group reported values; they never re-score an
  // assessment or collapse it to alarm / no-alarm. A held session
  // stays zeros, and the panel itself is hidden under Vigiles and
  // Sanitas by CSS, so this line only ever shows under Ignis.
  const confidence = ignisReportedConfidence(log.entries());
  els.ignisConfidence.textContent =
    `High (≥ 0.8) ${confidence.high} · Medium (≥ 0.5) ${confidence.medium} · Low (< 0.5) ${confidence.low} · Unreported ${confidence.unreported}`;
  // IGNIS-ONEOFONE-3: the review queue re-reads the same log
  // entries — no new stats field, no new data — and renders the
  // Ignis-only panel from the requires_human_review flags recorded
  // assessments themselves carried. It never flags anything itself
  // and never notifies anyone. A held session stays zeros, and the
  // panel itself is hidden under Vigiles and Sanitas by CSS, so
  // this line only ever shows under Ignis.
  const reviewQueue = ignisReviewQueue(log.entries());
  els.ignisReviewQueue.textContent =
    `Flagged for human review ${reviewQueue.flagged} · Clear ${reviewQueue.clear} · Flag not recorded ${reviewQueue.unknown}`;
  // IGNIS-ONEOFONE-4: the evidence-transparency panel re-reads the
  // same log entries — no new stats field, no new data — and renders
  // the Ignis-only panel from the evidence strings recorded
  // assessments themselves carried. A filled field never means the
  // assessment is correct; this counts strings only. A held session
  // stays zeros, and the panel itself is hidden under Vigiles and
  // Sanitas by CSS, so this line only ever shows under Ignis.
  const evidence = ignisEvidenceTransparency(log.entries());
  els.ignisEvidence.textContent =
    `Fully evidenced ${evidence.fullyEvidenced} · Partially evidenced ${evidence.partiallyEvidenced} · No evidence recorded ${evidence.unevidenced} · Not assessable ${evidence.unassessable}`;
}

// Native parity: the native timeline's empty state says analysis is
// running when it is, and "No events yet. Assessments and errors will
// appear here." when it is not — not just "No events yet." The web
// history note must say the same in both cases, so an empty history
// during a run does not look like nothing is happening, and an idle
// empty history still says what will appear there. This only sets the
// text; whether the note shows at all is separate — addHistoryItem
// hides it once the first entry arrives, and Reset shows it again.
function updateHistoryEmpty() {
  els.historyEmpty.textContent = sampler.running
    ? "Analysis is running — assessments and errors will appear here as they arrive."
    : "No events yet. Assessments and errors will appear here.";
}

// Native parity: the native camera panel shows an ANALYSIS ACTIVE
// banner while sampling runs, with the live interval, so a run is
// visible at a glance instead of only in the moving counters. The web
// Camera panel shows the same line: hidden while idle, shown while the
// sampler runs, and reworded when the interval changes mid-run. It is
// a polite, atomic live region, so starting analysis reads the banner
// aloud: the backend-status line only ever says a request path is
// opening, never that sampling is running or at what interval, and on
// native even that line changes silently. The line changes only on
// user actions — start, stop, or an interval change — never on a
// sampler tick, so unlike the sampler-stats line there is no
// per-second spam risk in announcing it. Stopping hides the line
// without a word: the user tapped Stop themselves, like Clear.
function updateAnalysisActive() {
  const seconds = currentIntervalMs() / 1000;
  els.analysisActive.textContent =
    `Analysis active — sampling one frame every ${seconds} second${seconds === 1 ? "" : "s"}.`;
  els.analysisActive.hidden = !sampler.running;
}

function refreshButtons() {
  const camActive = camera.active;
  els.btnCameraStart.disabled = camActive || cameraStartPending || cameraUnsupported;
  // Stop stays enabled while a start is pending, not just while the
  // camera is live: the Stop handler already clears the pending flag
  // and bumps the start generation, so it is the cancel for a
  // permission wait — but the button used to be disabled exactly
  // during that wait (camActive is false until the prompt resolves),
  // so the only way to abandon the wait was Reset, which also clears
  // the latest assessment and the history. A pending start cancelled
  // this way leaves the view alone: the stale Start settle touches
  // nothing, and the Camera class discards the stream if permission
  // is granted after the stop.
  els.btnCameraStop.disabled = !camActive && !cameraStartPending;
  // The facing picker waits out a pending start too, and a pending
  // live facing switch too. The Start call fixes its getUserMedia
  // constraints when it is made, so a facing change landing mid-wait
  // would only record a choice the stream being requested does not
  // use: the picker would say rear while the camera that attaches
  // shows the front view. A live switch has the same shape: it stops
  // the stream, then awaits a start fixed to the first facing, and a
  // second change landing in that window only records (the camera is
  // not active while its stream is stopped, so switchFacing takes its
  // record-only path) — the picker would say the new facing while
  // the stream that attaches shows the old one. Stop stays enabled
  // as the cancel, and every path that clears a pending flag (the
  // Start settle, the switch settle, Stop, Reset) refreshes the
  // buttons, so the picker comes back the moment the wait ends.
  // Native needs no equivalent: its configureAndStart reads the
  // facing when permission is granted, and its queued facing restart
  // likewise reads the facing when it configures, so a mid-wait or
  // mid-restart pick there is honestly the camera that opens.
  els.cameraFacing.disabled = cameraStartPending || facingSwitchPending;
  els.btnAnalysisStart.disabled = !camActive || sampler.running;
  els.btnAnalysisStop.disabled = !sampler.running;
  updateHistoryEmpty();
  updateAnalysisActive();
}

function describeCameraError(err) {
  switch (err && err.name) {
    case "NotAllowedError":
      return "Camera permission denied. Allow camera access in the browser to use the live feed.";
    case "NotFoundError":
    case "OverconstrainedError":
      return "No usable camera was found on this device.";
    case "NotReadableError":
      return "The camera is present but could not be read (it may be in use by another application).";
    case "NotSupportedError":
      return err.message;
    default:
      return `Camera error: ${err && err.message ? err.message : String(err)}`;
  }
}

// Native parity: the native app's Latest panel says "Waiting for the
// first assessment…" while a request is outstanding and no assessment
// has been shown yet, instead of leaving "No assessment received yet."
// on screen as if nothing were happening. The web panel does the same:
// submitAssessment shows the waiting line only while no assessment has
// ever been displayed (a displayed assessment, live or re-shown from
// history, stays put during later requests), and a failed first request
// shows the real backend error, exactly like the native panel —
// "No assessment received yet." is only for when nothing has been
// attempted at all, so a failure is never mistaken for "not tried yet."
let latestAssessmentShown = false;

// Reset generation: a request outstanding when Reset is tapped must not
// repopulate the cleared view when it settles. submitAssessment captures
// this number when it starts; Reset bumps it. Display updates (latest
// panel, history, backend status, last round trip) happen only when the
// captured number still matches. The session-log entry is still recorded:
// the request genuinely happened, and the log survives Reset by design,
// so a stale entry is honest there while a stale panel is not.
let viewGeneration = 0;

// Camera-start generation: bumped by Stop and by Reset, captured by
// the Start and facing handlers before their await. A start still
// awaiting the permission prompt when Stop or Reset lands must not
// repaint the stopped view with "Camera is live." when it settles —
// the Camera class already discards that stream, so the stale handler
// simply touches nothing (Stop/Reset already set the state and the
// buttons), instead of re-announcing a camera that is off.
let cameraStartGeneration = 0;

// Whether this browser exposes no camera API at all. refreshButtons()
// owns the Start button from this too: the init block used to disable
// Start directly, and the init refreshButtons() right after it
// re-enabled it, so a camera-less browser offered a Start button
// whose tap could only fail with the unsupported error.
const cameraUnsupported = !cameraSupported();

// Whether a camera start is still awaiting the permission prompt.
// refreshButtons() owns the Start button from this flag, not from a
// one-off disable in the Start handler: that direct disable used to
// be undone by any other path that refreshed the buttons mid-wait —
// changing the facing selector while the prompt was up re-enabled
// Start, and a second tap fired a second permission request. Stop and
// Reset clear the flag, since their settle paths already own the
// buttons; a stale Start settle touches nothing, so it must never
// clear a flag a newer start now owns — and a stale settle only ever
// follows a Stop or Reset, which already cleared it.
let cameraStartPending = false;

// Whether a live facing switch is still awaiting its restart. The
// switch stops the stream, then awaits a start fixed to the facing
// chosen when the switch began; a second change in that window only
// records, because switchFacing takes its record-only path while the
// camera is not active — so refreshButtons() owns the picker from
// this flag too, exactly like the pending-start flag. The switch's
// own settle clears it (in finally, so a stale settle after Stop or
// Reset clears it as well as a live one), and Stop and Reset clear
// it directly so the picker comes back at once instead of waiting
// for a restart that will settle stale.
let facingSwitchPending = false;

// In-flight request count: the Camera panel's "Analysis request in
// flight…" line is shared by every submit path — a live sampled frame,
// a still image, and a prerecorded-video frame can all be outstanding
// at once (the sampler guards only live-vs-live, and each panel guards
// only itself), so a single boolean hid the line as soon as the first
// of several requests settled, while another was still out. Count
// instead: the line shows while at least one request is outstanding
// and hides only when the last one settles. Reset never touches the
// count — a request outstanding across Reset is still outstanding, and
// its settle path still hides the line, exactly as before.
let inFlightCount = 0;

function showInFlight() {
  inFlightCount += 1;
  els.inFlight.hidden = false;
}

function hideInFlight() {
  inFlightCount = Math.max(0, inFlightCount - 1);
  els.inFlight.hidden = inFlightCount === 0;
}

function renderLatest(assessment, earlierNote = null) {
  latestAssessmentShown = true;
  const product = PRODUCT_BY_ID[assessment.product] || null;
  const wrap = document.createElement("div");

  // HANA Agent1: the panel wash follows the assessment's own product,
  // not the selected product's — the web counterpart to the native
  // UI-6 panel wash. The theme blocks wash every .panel in the
  // selected product's accent, so without this a redisplayed
  // assessment re-tinted on every product switch (flat under Vigiles,
  // green under Sanitas for an Ignis assessment). The section is
  // tagged, not the inner wrap, because the gradient lives on the
  // section; stale classes are removed first so a redisplayed
  // assessment never keeps its predecessor's wash. An unknown product
  // key gets no class and keeps the selection wash, like the
  // product-name fallback.
  const latestPanel = els.latest.closest(".panel");
  if (latestPanel) {
    latestPanel.classList.remove(
      "latest-product-vigiles",
      "latest-product-ignis",
      "latest-product-sanitas",
    );
    const washByProduct = {
      vigiles: "latest-product-vigiles",
      ignis: "latest-product-ignis",
      sanitas: "latest-product-sanitas",
    };
    const wash = washByProduct[assessment.product];
    if (wash) latestPanel.classList.add(wash);
  }

  if (earlierNote) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = earlierNote;
    wrap.appendChild(note);
  }
  const head = document.createElement("p");
  head.className = "assessment-head";
  // HANA Agent1: the category reads at the native panel's title3
  // size, like its product name and timestamp already match their
  // native sizes (12.5px, UI-19). The native category is a title3
  // Text (20pt, bold), but the web category was a bare strong, so
  // it read at the 15px body size — a title that did not stand out
  // from the summary and observation text below it, while the native
  // title stands above them. The class is the only change: the
  // category keeps its bold weight (strong), its position first in
  // the head line, and its wording, and the product, timestamp, and
  // review-flag spans keep their own sizes.
  const type = document.createElement("strong");
  type.className = "assessment-category";
  type.textContent = assessment.assessment.category;
  head.appendChild(type);
  const productEl = document.createElement("span");
  productEl.className = "assessment-product";
  // HANA Agent1: the product name keeps the assessment's own product
  // accent, not the selected product's. The base .assessment-product
  // rule uses var(--accent), which follows the current selection, so
  // a past assessment shown again under another product — or a fresh
  // one whose request was in flight across a switch — read its name
  // in the wrong product's color. Same fixed-hex classes as the
  // history-product edges; an unknown product key gets no class and
  // keeps the base selection accent.
  if (assessment.product === "vigiles") {
    productEl.classList.add("assessment-product-vigiles");
  } else if (assessment.product === "ignis") {
    productEl.classList.add("assessment-product-ignis");
  } else if (assessment.product === "sanitas") {
    productEl.classList.add("assessment-product-sanitas");
  }
  productEl.textContent = ` ${product ? product.displayName : assessment.product}`;
  head.appendChild(productEl);
  const time = document.createElement("span");
  time.className = "assessment-time";
  time.textContent = ` ${assessment.timestamp}`;
  head.appendChild(time);
  if (assessment.assessment.requires_human_review) {
    const flag = document.createElement("span");
    flag.className = "review-flag";
    flag.textContent = " REQUIRES HUMAN REVIEW";
    head.appendChild(flag);
  }
  wrap.appendChild(head);

  // Native parity: the native panel renders the summary paragraph only
  // when the server reported one, and renders an observation's Evidence
  // line only when its evidence string is non-empty. The web panel did
  // neither — an empty summary left a blank paragraph, and an empty
  // evidence string left a bare "(; confidence …)" slot that reads as
  // a missing value rather than "no evidence stated". Both are valid
  // v2 responses (summary and evidence need only be strings), so the
  // panel omits the empty field instead of inventing a placeholder.
  if (assessment.assessment.summary !== "") {
    const text = document.createElement("p");
    text.textContent = assessment.assessment.summary;
    wrap.appendChild(text);
  }

  if (assessment.observations.length > 0) {
    const list = document.createElement("ul");
    list.className = "observations";
    for (const obs of assessment.observations) {
      const item = document.createElement("li");
      const category = document.createElement("strong");
      category.textContent = obs.category;
      item.appendChild(category);
      // HANA Agent1: the confidence label carries the native panel's
      // colon — AssessmentView confidenceText reads "confidence:
      // 0.72" and "confidence: not reported", but the web line used
      // the colon-less form, so the same value read as a bare label
      // on one surface and a labeled value on the other. The colon
      // is the only change: the web
      // line keeps its single-line layout (native shows confidence
      // on its own caption row), the two-decimal format, and the
      // "not reported" wording for a null confidence, never invented.
      const confidence = obs.confidence === null ? "confidence: not reported" : `confidence: ${obs.confidence.toFixed(2)}`;
      const evidencePart = obs.evidence !== "" ? `${obs.evidence}; ` : "";
      item.appendChild(document.createTextNode(` — ${obs.description} (${evidencePart}${confidence})`));
      list.appendChild(item);
    }
    wrap.appendChild(list);
  }

  // Native parity: the native panel gives uncertainty its own
  // labeled section — one line per item, and "The model reported no
  // uncertainty items." when the server reported none — instead of
  // squeezing the items into one joined paragraph. The web panel did
  // the latter, so a multi-item uncertainty read as one run-on
  // sentence and an empty one read as "none stated", which softens
  // the fact that the model reported nothing. Uncertainty is never
  // softened or hidden: same heading, same per-item lines, same
  // empty wording as the native panel.
  const uncertaintyHead = document.createElement("h3");
  uncertaintyHead.className = "subhead";
  uncertaintyHead.textContent = "Uncertainty";
  wrap.appendChild(uncertaintyHead);
  if (assessment.assessment.uncertainty.length > 0) {
    const uncertainty = document.createElement("ul");
    uncertainty.className = "uncertainty";
    for (const item of assessment.assessment.uncertainty) {
      const line = document.createElement("li");
      line.textContent = item;
      uncertainty.appendChild(line);
    }
    wrap.appendChild(uncertainty);
  } else {
    // HANA Agent1: the empty uncertainty note now reads at body size,
    // like the native panel's note. The native empty note is a plain
    // Text — body size, secondary — and the web's own populated
    // uncertainty items read at body size in --muted, but the web
    // empty note used class "note" (13px), so an assessment with no
    // uncertainty items read its note smaller than both its own
    // populated list and the native note. The note now carries class
    // "uncertainty" — muted color, body size inherited — changing no
    // wording, no heading, and no populated-list rendering; the
    // earlierNote paragraph above the panel keeps class "note".
    const uncertainty = document.createElement("p");
    uncertainty.className = "uncertainty";
    uncertainty.textContent = "The model reported no uncertainty items.";
    wrap.appendChild(uncertainty);
  }

  // Native parity: the native panel puts a Divider between the
  // uncertainty section and the processing line, so the model and
  // latency line reads as footer metadata, not as another finding.
  // The web panel ran the processing line straight after the
  // uncertainty list (or its "no uncertainty items" note) with no
  // rule at all, so the footer blended into the findings. The rule
  // is aria-hidden: it is a visual separator only, like the native
  // Divider, not a landmark a screen reader should stop on.
  const divider = document.createElement("hr");
  divider.className = "assessment-divider";
  divider.setAttribute("aria-hidden", "true");
  wrap.appendChild(divider);

  // Native parity: the native panel's processing line reads
  // "Model: … · Server-reported latency: …", with the latency as a
  // whole number when it is one and one decimal otherwise — the
  // native serverLatencyText rule. The web line said "server
  // latency" and interpolated the raw number, so a fractional
  // latency printed at full precision (812.55 ms) and, worse, the
  // wording did not say whose latency it was: the panel also shows
  // a client-measured round trip elsewhere, so "server latency"
  // could be read as that round trip. "Server-reported" names the
  // source exactly, like the native line, and the formatting matches
  // it: a null latency still reads "not reported", never invented.
  const latencyMs = assessment.processing.latency_ms;
  const serverLatency =
    latencyMs === null
      ? "not reported"
      : Number.isInteger(latencyMs)
        ? `${latencyMs} ms`
        : `${latencyMs.toFixed(1)} ms`;
  const processing = document.createElement("p");
  processing.className = "note mono";
  processing.textContent =
    `Model: ${assessment.processing.model} · Server-reported latency: ${serverLatency}`;
  wrap.appendChild(processing);

  els.latest.replaceChildren(wrap);
}

function addHistoryItem({ title, timestamp, body, kind, assessment = null, product = null }) {
  els.historyEmpty.hidden = true;
  const item = document.createElement("li");
  item.className = `history-item history-${kind}`;
  // M3 (Sanitas identity in results): a Sanitas entry's edge uses the
  // Sanitas product accent, not its status color. Only Sanitas entries
  // got the product class at first; other products kept their status
  // edges. IGNIS-UI-3 adds the Ignis counterpart: an Ignis entry's
  // edge uses the Ignis product accent, not its status color. HANA
  // Agent1 completes the set: a Vigiles entry's edge uses the Vigiles
  // product accent, matching the native timeline rows, which carry
  // their own product's accent for all three products (UI-4). Without
  // this branch the web Vigiles entries kept status edges while the
  // native Vigiles rows showed the blue product edge, so the two
  // surfaces disagreed on exactly the default product's rows.
  const entryProduct = assessment?.product ?? product;
  if (entryProduct === "sanitas") {
    item.classList.add("history-product-sanitas");
  } else if (entryProduct === "ignis") {
    item.classList.add("history-product-ignis");
  } else if (entryProduct === "vigiles") {
    item.classList.add("history-product-vigiles");
  }

  const head = document.createElement("p");
  head.className = "history-head";
  const titleEl = document.createElement("strong");
  titleEl.textContent = title;
  head.appendChild(titleEl);
  const timeEl = document.createElement("span");
  timeEl.className = "assessment-time";
  timeEl.textContent = ` ${timestamp}`;
  head.appendChild(timeEl);
  item.appendChild(head);

  if (body) {
    const bodyEl = document.createElement("p");
    bodyEl.textContent = body;
    item.appendChild(bodyEl);
  }

  // Native parity: the native timeline's assessment rows are selectable
  // and redisplay that assessment. The web history gains the same, as a
  // button, so a past result can be inspected again during the session.
  // Failure entries carry no assessment, so they get no button. Showing
  // an earlier assessment never re-sends a frame, never changes the
  // backend status, and is labelled as a past result in the panel, so
  // it cannot be mistaken for a new result.
  if (assessment) {
    const show = document.createElement("button");
    show.type = "button";
    show.className = "history-show";
    show.textContent = "Show assessment";
    show.setAttribute("aria-label", `Show assessment from ${timestamp}`);
    show.addEventListener("click", () => {
      renderLatest(
        assessment,
        `Showing an earlier assessment from ${timestamp}. This is a past result shown again for review, not a new assessment.`,
      );
    });
    item.appendChild(show);
  }

  els.history.prepend(item);
}

// One assessment request, shared by live sampled frames and by a chosen
// still image: same endpoint, same validation, same history entry, same
// session-log entry. Throws on failure after rendering and logging it,
// so the sampler can count the error and the still-image button can
// simply swallow it (it is already on screen). The scenario label is a
// parameter, captured by the caller at sample or tap time, exactly like
// the product: reading it here after the request returned would let a
// scenario change made mid-request relabel that request's log entry
// with ground truth it was never assessed under.
async function submitAssessment(product, timestamp, image, scenarioLabel) {
  const endpoint = currentEndpoint();
  const generation = viewGeneration;
  showInFlight();
  if (!latestAssessmentShown) {
    els.latest.textContent = "Waiting for the first assessment…";
  }
  const started = performance.now();
  try {
    const assessment = await assessFrame(endpoint, { product, timestamp, image });
    const latencyMs = Math.round(performance.now() - started);
    log.record({
      requestTimestamp: timestamp,
      product,
      latencyMs,
      status: "ok",
      response: assessment,
      scenarioLabel,
    });
    // A Reset while this request was out clears the view; the settling
    // request must not put its result back on screen. The log entry
    // above stands either way — the request genuinely happened.
    if (generation === viewGeneration) {
      updateLastRoundTrip(latencyMs);
      setBackendStatus("connected", `Model backend connected: ${endpoint}`);
      renderLatest(assessment);
      const category = assessment.assessment.category;
      // The history title uses the assessment's own product, not the
      // currently selected one: the user may have switched mid-request.
      const assessedProduct = PRODUCT_BY_ID[assessment.product];
      const assessedName = assessedProduct ? assessedProduct.displayName : assessment.product;
      addHistoryItem({
        title: assessment.assessment.requires_human_review
          ? `${assessedName} · ${category} (human review)`
          : `${assessedName} · ${category}`,
        timestamp: assessment.timestamp,
        body: assessment.assessment.summary,
        kind: assessment.assessment.requires_human_review ? "review" : "ok",
        assessment,
      });
    }
    return assessment;
  } catch (err) {
    // Native parity: a failure with no request behind it (the client
    // rejected the endpoint before sending) carries no measured
    // latency — the native client reports nil there, and AppModel
    // leaves the last round trip alone. The web path measured the time
    // until fetch rejected and stamped it as a round trip, which was
    // not a round trip at all, and logged it as a measured latency.
    // Log null and leave the previous round trip in place: it is real
    // information a typo'd endpoint should not erase. Only Reset
    // clears it. The still-image and video paths share this catch
    // through submitAssessment, so they inherit the same handling.
    const noRequest = err instanceof AssessError && err.noRequest;
    const latencyMs = noRequest ? null : Math.round(performance.now() - started);
    const kind = err instanceof AssessError ? err.kind : "network";
    const status = kind === "http" ? "http_error" : kind === "invalid" ? "invalid_response" : "network_error";
    log.record({
      requestTimestamp: timestamp,
      product,
      latencyMs,
      status,
      error: err.message,
      scenarioLabel,
    });
    // Same Reset rule as the success path: the log entry stands, but a
    // request that settled after a Reset must not repaint the cleared
    // view with its failure, its round trip, or a "failed first
    // request" line in the latest panel.
    if (generation === viewGeneration) {
      if (latencyMs !== null) {
        updateLastRoundTrip(latencyMs);
      }
      setBackendStatus("error", `Model backend not connected: ${err.message}`);
      if (!latestAssessmentShown) {
        els.latest.textContent = `Model backend not connected: ${err.message}`;
      }
      addHistoryItem({
        title: "Analysis request failed",
        timestamp,
        body: err.message,
        kind: "error",
        product,
      });
    }
    throw err;
  } finally {
    hideInFlight();
    updateLogStats();
  }
}

async function runSample() {
  const product = currentProductId;
  const timestamp = new Date().toISOString();
  // Captured with the product, before any capture or request: a
  // scenario change mid-sample must not relabel this sample's entry.
  const scenarioLabel = currentScenarioLabel();
  let image;
  try {
    image = camera.captureFrame(els.captureCanvas);
  } catch (err) {
    // Video-path parity: the prerecorded-video path records a capture
    // failure directly in the history and the backend status, in the
    // same shapes as a backend failure, because no request was made —
    // it shows the capture failure itself, not a backend message, and
    // it leaves the last round trip alone (there is no new
    // measurement). The live path only logged it, so a failed tick
    // during a run never reached the history a reviewer reads, even
    // though the sampler counted it as a failed tick. Same honest
    // handling otherwise: logged with a null latency, no assessment
    // invented, and the sampler keeps ticking — the camera may still
    // be live and the next tick may succeed, so the camera state text
    // is left alone.
    const message = `Frame capture failed: ${err.message}`;
    log.record({
      requestTimestamp: timestamp,
      product,
      latencyMs: null,
      status: "invalid_response",
      error: message,
      scenarioLabel,
    });
    updateLogStats();
    setBackendStatus("error", message);
    addHistoryItem({
      title: "Analysis request failed",
      timestamp,
      body: message,
      kind: "error",
    });
    throw err;
  }
  await submitAssessment(product, timestamp, image, scenarioLabel);
}

// Still-image input state: the chosen file's data URL lives in memory
// only, and is cleared by its Clear button or by Reset. It is assessed under whichever product
// is selected when "Assess this image" is tapped, exactly like the next
// live sampled frame.
let stillImageDataUrl = null;
let stillImageAssessing = false;
// One helper owns the still-image Assess button, exactly like the
// video helper and exactly like the native button's disabled rule
// (nil image or assessing): enabled only with a data URL ready and
// no assessment in flight. Every place that used to set the button
// directly tested only the data URL, so a new image chosen while a
// request was out — its read finishing mid-request — re-enabled the
// button under that request, and a tap was then silently dropped by
// the assessing guard. The read-in-flight window needs no equivalent:
// the data URL is null while a read is in flight, so a read settle
// already enables only a truly ready image; this helper covers the
// assessment-in-flight window instead.
function refreshStillImageAssessButton() {
  els.btnImageAssess.disabled = !stillImageDataUrl || stillImageAssessing;
}
// Still-image read generation: choosing a file reads it asynchronously
// (FileReader, then a decode probe), so a Reset, a Clear, or a second
// file choice can land while a read is still in flight. The read
// captures this number when it starts; Clear bumps it, each new choice
// bumps it, and the read touches nothing once its number is stale —
// otherwise a pre-reset image would repaint the panel Reset cleared,
// or an earlier file would overwrite a later one.
let stillImageReadGeneration = 0;

const sampler = new FrameSampler({
  intervalMs: 3000,
  onSample: runSample,
  // Failures are already rendered and logged inside runSample; the tick
  // callback only keeps the on-screen counters current.
  onTick: () => updateSamplerStats(),
});

els.productRadios.forEach((radio) => {
  radio.addEventListener("change", () => {
    if (radio.checked && isProductId(radio.value)) {
      currentProductId = radio.value;
      renderProduct();
    }
  });
});

els.btnContactAdd.addEventListener("click", () => {
  try {
    contacts.add({
      product: currentProductId,
      name: els.contactName.value,
      role: els.contactRole.value,
      organization: els.contactOrg.value,
    });
    els.contactName.value = "";
    els.contactRole.value = "";
    els.contactOrg.value = "";
    els.contactsFormNote.textContent = "";
    renderContacts();
  } catch {
    els.contactsFormNote.textContent = "Name, role, and organization are all required.";
  }
});

// Clears only the still-image input (preview, file choice, Assess
// disabled) without stopping the camera or analysis — the web match for
// the native panel's Clear button. Reset reuses this for the same panel.
function clearStillImageInput() {
  // Invalidate any read still in flight: its settle path must not
  // repaint this cleared panel (see stillImageReadGeneration).
  stillImageReadGeneration += 1;
  stillImageDataUrl = null;
  els.imageInput.value = "";
  els.imagePreview.hidden = true;
  els.imagePreview.removeAttribute("src");
  els.imageState.textContent = "No image chosen.";
  refreshStillImageAssessButton();
  // The "Sending still image…" line is owned by the request, not by
  // the input: Clear must not hide it for a request still out. The
  // line used to hide unconditionally here, so clearing (or choosing
  // a new image, or Reset, which reuses this helper) during a request
  // left the panel silent while that request was still outstanding —
  // the very wait the line exists to show. The native panel has no
  // such hole: it shows its progress line while stillImageAssessing
  // is true whatever the image is, and only its Task defer clears it.
  // So hide the line only when no request is out; the Assess settle
  // path still hides it when the request finishes.
  els.imageAssessing.hidden = !stillImageAssessing;
}

els.btnImageClear.addEventListener("click", () => {
  clearStillImageInput();
});

els.imageInput.addEventListener("change", async () => {
  // Captured before any await, and bumped even for a non-image file or
  // an emptied choice: either one supersedes a read still in flight,
  // and that read must not repaint the state this handler just set.
  const readGeneration = ++stillImageReadGeneration;
  const file = els.imageInput.files && els.imageInput.files[0];
  stillImageDataUrl = null;
  els.imagePreview.hidden = true;
  els.imagePreview.removeAttribute("src");
  refreshStillImageAssessButton();
  if (!file) {
    els.imageState.textContent = "No image chosen.";
    return;
  }
  if (!isSupportedImageFile(file)) {
    els.imageState.textContent = "That file is not an image. Choose an image file.";
    return;
  }
  els.imageState.textContent = "Reading image…";
  try {
    stillImageDataUrl = await readFileAsDataURL(file);
    // A Reset, Clear, or newer choice during the read invalidates it:
    // return without touching the panel, which now shows the newer
    // state (cleared, or the newer file's "Reading image…").
    if (readGeneration !== stillImageReadGeneration) return;
    // Live-capture parity: a phone photo can be far larger than the
    // 1280px cap live and video frames are downscaled to, and the
    // still-image path sent the file's original bytes. Decode it and,
    // only when the cap actually bites, replace the payload with the
    // downscaled JPEG — a small image keeps its original bytes and
    // format, and a file that will not decode fails here, honestly,
    // instead of sending undecodable bytes to the endpoint.
    const probe = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("That image could not be decoded."));
      img.src = stillImageDataUrl;
    });
    // Same guard after the decode probe: a Reset, Clear, or newer
    // choice during decoding must not let this read set the preview,
    // the ready text, or the Assess button.
    if (readGeneration !== stillImageReadGeneration) return;
    if (Math.max(probe.naturalWidth, probe.naturalHeight) > MAX_FRAME_DIMENSION) {
      stillImageDataUrl = downscaleImageToDataURL(probe, els.captureCanvas);
    }
    els.imagePreview.src = stillImageDataUrl;
    els.imagePreview.hidden = false;
    els.imageState.textContent =
      `Image ready: ${file.name}. Tap “Assess this image” to send it once to the assessment endpoint, under the product selected above. It is not stored by this app.`;
    // Through the helper, not a bare enable: a read finishing for a
    // new image chosen while a request is out must not enable the
    // button under that request.
    refreshStillImageAssessButton();
  } catch (err) {
    // A stale read's failure must not overwrite the newer state
    // either — not the cleared panel, and not a newer read's
    // "Reading image…" line.
    if (readGeneration !== stillImageReadGeneration) return;
    stillImageDataUrl = null;
    refreshStillImageAssessButton();
    els.imageState.textContent = `Could not read that image: ${err.message}`;
  }
});

els.btnImageAssess.addEventListener("click", async () => {
  if (!stillImageDataUrl || stillImageAssessing) return;
  stillImageAssessing = true;
  refreshStillImageAssessButton();
  // Native parity: the native Still image panel shows "Sending still
  // image…" in the panel while the request is outstanding. The web
  // panel only had the generic in-flight line in the distant Camera
  // panel, so a user watching this panel saw nothing move while the
  // request was out. Show the same line here, and hide it again when
  // the request settles, success or failure.
  els.imageAssessing.hidden = false;
  setBackendStatus("unknown", `Contacting model backend: ${currentEndpoint()} …`);
  // Scenario captured at tap time, like the product: a change made
  // while this request is out must not relabel its log entry.
  const scenarioLabel = currentScenarioLabel();
  try {
    await submitAssessment(currentProductId, new Date().toISOString(), stillImageDataUrl, scenarioLabel);
  } catch {
    // submitAssessment already rendered and logged the failure.
  } finally {
    stillImageAssessing = false;
    els.imageAssessing.hidden = true;
    // Through the helper: a new image chosen while this request was
    // out enables here only because the request is settled now, and
    // a Clear during the request keeps it disabled (no data URL).
    refreshStillImageAssessButton();
  }
});

// Prerecorded-video input state: the chosen file's object URL lives in
// memory only and is revoked by its Clear button or by Reset (and when another file is chosen).
// "Assess this frame" captures the frame showing at that moment and
// sends it once, under whichever product is selected, exactly like a
// live sampled frame. The assess button stays disabled until the video's
// metadata has loaded, so capture cannot be tapped on a frameless video.
let videoObjectUrl = null;
let videoAssessing = false;
// Video readiness, separate from the object URL: choosing a file creates
// the URL at once, but the video has no frame to capture until its
// metadata loads. The Assess button's own comment has always said it
// stays disabled until metadata loads, yet every place that re-enabled
// it tested only the URL — so a video chosen while a request was out
// (or whose metadata arrived while a request was out) re-enabled the
// button on a frameless video, and a tap then failed capture honestly
// but pointlessly, or was silently dropped by the assessing guard.
// One helper owns the button now: enabled only with a URL, loaded
// metadata, and no assessment in flight. The still-image panel needs
// no equivalent: its data URL itself is the readiness signal — it is
// null while a read is in flight, so its finally path already enables
// only a truly ready image. Native needs no change either: its Assess
// button is already gated on assessing, and a not-ready native player
// fails extraction with the real error instead of sending a blank
// frame, so no native button ever promises a frame it cannot capture.
let videoMetadataLoaded = false;

function refreshVideoAssessButton() {
  els.btnVideoAssess.disabled = !videoObjectUrl || !videoMetadataLoaded || videoAssessing;
}

function clearVideoInput() {
  if (videoObjectUrl) {
    URL.revokeObjectURL(videoObjectUrl);
    videoObjectUrl = null;
  }
  videoMetadataLoaded = false;
  els.videoPreview.removeAttribute("src");
  els.videoPreview.load();
  els.videoPreview.hidden = true;
  refreshVideoAssessButton();
  // Same rule as the still-image panel, for the same reason: the
  // "Sending video frame…" line is owned by the request, not by the
  // input, so Clear (a new choice, or Reset, which reuses this helper)
  // during a request must not hide it while that request is still out.
  // The native panel shows its progress line while videoAssessing is
  // true whatever the player is, and only its Task defer clears it;
  // the web Assess settle paths still hide this line when the request
  // finishes.
  els.videoAssessing.hidden = !videoAssessing;
}

// Clears only the prerecorded-video input (file choice, preview, Assess
// disabled) without stopping the camera or analysis — the web match for
// the native panel's Clear button. Reset reuses the same steps.
els.btnVideoClear.addEventListener("click", () => {
  els.videoInput.value = "";
  clearVideoInput();
  els.videoState.textContent = "No video chosen.";
});

els.videoInput.addEventListener("change", () => {
  const file = els.videoInput.files && els.videoInput.files[0];
  clearVideoInput();
  if (!file) {
    els.videoState.textContent = "No video chosen.";
    return;
  }
  if (!isSupportedVideoFile(file)) {
    els.videoState.textContent = "That file is not a video. Choose a video file.";
    return;
  }
  videoObjectUrl = URL.createObjectURL(file);
  els.videoPreview.src = videoObjectUrl;
  els.videoPreview.hidden = false;
  els.videoState.textContent = `Video ready: ${file.name}. Play it, pause on the frame you want assessed, and tap “Assess this frame”. Only that frame is sent; the video is not stored by this app.`;
});

els.videoPreview.addEventListener("loadedmetadata", () => {
  // Metadata loaded means the video has dimensions, so a frame capture
  // will succeed — but only if no assessment is in flight: metadata
  // arriving for a video chosen mid-request must not enable the button
  // under that request, or a tap would be silently dropped by the
  // assessing guard below. The helper keeps it disabled until the
  // request settles, and the settle path then enables it.
  videoMetadataLoaded = true;
  refreshVideoAssessButton();
});

els.videoPreview.addEventListener("error", () => {
  els.videoState.textContent = "That video could not be played in this browser. Try another file.";
  videoMetadataLoaded = false;
  refreshVideoAssessButton();
});

els.btnVideoAssess.addEventListener("click", async () => {
  if (!videoObjectUrl || !videoMetadataLoaded || videoAssessing) return;
  videoAssessing = true;
  refreshVideoAssessButton();
  // Native parity: the native video panel shows "Sending video
  // frame…" in the panel while the request is outstanding, for the
  // same reason as the still-image note above — the generic in-flight
  // line lives in the Camera panel, not here.
  els.videoAssessing.hidden = false;
  setBackendStatus("unknown", `Contacting model backend: ${currentEndpoint()} …`);
  const timestamp = new Date().toISOString();
  // Scenario captured at tap time, like the product: a change made
  // while capture or this request is outstanding must not relabel it.
  const scenarioLabel = currentScenarioLabel();
  let image;
  try {
    image = captureVideoFrame(els.videoPreview, els.captureCanvas);
  } catch (err) {
    // Native parity: the native app's video-frame path records a
    // capture failure directly in the timeline and the backend status,
    // in the same shapes as a backend failure, because no request was
    // made — it shows the capture failure itself, not a backend
    // message, and it leaves the last round trip alone (there is no
    // new measurement). The web panel only logged it and showed it in
    // the video panel, so the failure never reached the history a
    // reviewer reads. Same honest handling as a failed live capture
    // otherwise: logged, no assessment invented.
    const message = `Video frame capture failed: ${err.message}`;
    log.record({
      requestTimestamp: timestamp,
      product: currentProductId,
      latencyMs: null,
      status: "invalid_response",
      error: message,
      scenarioLabel,
    });
    updateLogStats();
    setBackendStatus("error", message);
    addHistoryItem({
      title: "Analysis request failed",
      timestamp,
      body: message,
      kind: "error",
    });
    els.videoState.textContent = `Could not capture this frame: ${err.message}`;
    videoAssessing = false;
    els.videoAssessing.hidden = true;
    // Not a blanket re-enable: a video chosen mid-request (or one
    // whose metadata never loaded) must not come back enabled here.
    refreshVideoAssessButton();
    return;
  }
  try {
    await submitAssessment(currentProductId, timestamp, image, scenarioLabel);
  } catch {
    // submitAssessment already rendered and logged the failure.
  } finally {
    videoAssessing = false;
    els.videoAssessing.hidden = true;
    // A video chosen while this request was out enables here only if
    // its metadata has actually loaded by now; otherwise the button
    // stays disabled until loadedmetadata, exactly as a fresh choice.
    refreshVideoAssessButton();
  }
});

els.btnCameraStart.addEventListener("click", async () => {
  // Native parity: the native camera has a requesting-permission state
  // ("Waiting for camera permission…") while the system prompt is up.
  // The web panel said "Camera is off." through that whole wait, which
  // reads as if nothing is happening while the user decides. Say the
  // wait out loud, and keep Start disabled until the prompt resolves —
  // the native Start button is disabled in its requesting state too —
  // so a second tap cannot fire a second permission request. One flag
  // owns that disabled state, through refreshButtons(): a direct
  // disable here used to be undone by the facing-change settle path
  // refreshing the buttons mid-wait, re-enabling Start while the
  // first permission request was still outstanding. The flag stays
  // set until this start settles (or Stop/Reset clears it), so no
  // mid-wait refresh can re-enable the button. The refreshButtons()
  // at the end restores the button to the real state: disabled once
  // live, enabled again after a denied or failed start.
  cameraStartPending = true;
  refreshButtons();
  setCameraState("Waiting for camera permission…");
  const startGeneration = cameraStartGeneration;
  try {
    await camera.start();
    // A Stop or Reset during the wait invalidates this start: the
    // Camera class discarded its stream, and this handler must not
    // repaint the stopped view with a live indicator and live text.
    // Stop/Reset already set the state and the buttons, so a stale
    // settle touches nothing at all.
    if (startGeneration !== cameraStartGeneration) return;
    // Native parity: the native camera checks its session is actually
    // running after configureAndStart and reports "Capture session did
    // not start" when it is not, instead of claiming live. The web
    // handler claimed live on any resolving start — but a stream can
    // end outside the app while permission or play is awaited (device
    // unplugged, camera revoked), and start() then resolves with no
    // live track. Say so honestly instead of showing CAMERA LIVE for
    // a dead preview; Start stays enabled, so a retry is one tap away.
    if (!camera.active) {
      els.cameraIndicator.hidden = true;
      setCameraState("Camera did not start — its stream ended before it went live. Try Start camera again.");
    } else {
      els.cameraIndicator.hidden = false;
      setCameraState("Camera is live. No frames are sent anywhere until analysis is started.");
    }
  } catch (err) {
    // Same rule on failure: a pre-stop permission denial must not
    // overwrite Reset's "Camera stopped. View reset." with its error.
    if (startGeneration !== cameraStartGeneration) return;
    els.cameraIndicator.hidden = true;
    setCameraState(describeCameraError(err));
  }
  cameraStartPending = false;
  refreshButtons();
});

els.btnCameraStop.addEventListener("click", () => {
  // Invalidate a start still awaiting permission, before stopping:
  // its settle path must not revive the camera this handler stops.
  cameraStartGeneration += 1;
  // And clear the pending-start flag, so refreshButtons() below
  // cannot leave Start disabled for a start that will never settle
  // as current — the stale settle path touches nothing.
  cameraStartPending = false;
  // And the pending-switch flag, for the same reason: a switch
  // settling stale must not leave the picker disabled, and Stop
  // should bring it back at once rather than when that switch
  // settles.
  facingSwitchPending = false;
  sampler.stop();
  camera.stop();
  els.cameraIndicator.hidden = true;
  setCameraState("Camera stopped.");
  refreshButtons();
  updateSamplerStats();
});

// Front vs rear camera. While the camera is off this only records the
// choice for the next Start. While it is live it restarts the stream on
// the new facing; a failed restart leaves the camera off and reports
// the real error, and analysis (if running) keeps ticking honestly
// against the restarted stream.
els.cameraFacing.addEventListener("change", async () => {
  // Same generation rule as Start: a restart still awaiting
  // permission when Stop or Reset lands must not repaint the stopped
  // view with a live indicator when it settles.
  const switchGeneration = cameraStartGeneration;
  // The picker waits out its own switch, through refreshButtons():
  // a second change while this restart is in flight would only
  // record (the camera is not active while its stream is stopped),
  // leaving the picker saying a facing the stream that attaches
  // does not show. The flag clears in finally, so a stale settle
  // after Stop or Reset brings the picker back too.
  facingSwitchPending = true;
  refreshButtons();
  try {
    await camera.switchFacing(els.cameraFacing.value);
    if (switchGeneration !== cameraStartGeneration) return;
    if (camera.active) {
      els.cameraIndicator.hidden = false;
      setCameraState("Camera is live. No frames are sent anywhere until analysis is started.");
    }
  } catch (err) {
    if (switchGeneration !== cameraStartGeneration) return;
    els.cameraIndicator.hidden = true;
    setCameraState(describeCameraError(err));
  } finally {
    facingSwitchPending = false;
    refreshButtons();
  }
});

els.btnAnalysisStart.addEventListener("click", () => {
  setBackendStatus("unknown", `Contacting model backend: ${currentEndpoint()} …`);
  sampler.setIntervalMs(currentIntervalMs());
  sampler.start();
  refreshButtons();
  updateSamplerStats();
});

els.btnAnalysisStop.addEventListener("click", () => {
  sampler.stop();
  refreshButtons();
  updateSamplerStats();
});

els.btnReset.addEventListener("click", () => {
  // Bump the view generation first: a request outstanding across this
  // Reset still logs when it settles, but must not repaint the view
  // this handler just cleared (see viewGeneration above).
  viewGeneration += 1;
  // A camera start still awaiting permission is invalidated too, so
  // its settle path cannot revive the camera Reset just stopped.
  cameraStartGeneration += 1;
  // And its pending-start flag clears with it, so refreshButtons()
  // below re-enables Start: a stale settle touches nothing, so
  // leaving the flag set would strand the button disabled for a
  // start that will never settle as current.
  cameraStartPending = false;
  // And the pending-switch flag, for the same reason: a switch
  // settling stale must not leave the picker disabled.
  facingSwitchPending = false;
  sampler.stop();
  camera.stop();
  els.cameraIndicator.hidden = true;
  clearStillImageInput();
  els.videoInput.value = "";
  clearVideoInput();
  els.videoState.textContent = "No video chosen.";
  setCameraState("Camera stopped. View reset.");
  setBackendStatus("unknown", "Model backend status unknown. Start analysis to contact the endpoint.");
  els.backendHealth.textContent = "Backend health not checked yet. Checking it contacts the server's health route only; it never sends a frame and never returns an assessment.";
  clearLastRoundTrip();
  latestAssessmentShown = false;
  els.latest.textContent = "No assessment received yet.";
  // HANA Agent1: Reset also clears the panel wash class, so the
  // cleared panel does not keep the last assessment's product tint.
  const resetLatestPanel = els.latest.closest(".panel");
  if (resetLatestPanel) {
    resetLatestPanel.classList.remove(
      "latest-product-vigiles",
      "latest-product-ignis",
      "latest-product-sanitas",
    );
  }
  els.history.replaceChildren();
  els.historyEmpty.hidden = false;
  refreshButtons();
  updateSamplerStats();
});

els.intervalSeconds.addEventListener("change", () => {
  els.intervalSeconds.value = String(currentIntervalSeconds());
  updateSamplingDisclosure();
  if (sampler.running) {
    sampler.setIntervalMs(currentIntervalMs());
  }
  updateAnalysisActive();
});

els.btnClearLog.addEventListener("click", () => {
  log.clear();
  updateLogStats();
});

els.btnExport.addEventListener("click", () => {
  const data = log.toExport({
    endpoint: currentEndpoint(),
    samplingIntervalSeconds: currentIntervalMs() / 1000,
    product: currentProductId,
  });
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `meta-trio-session-log-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

// Restore the on-screen history from a log kept across a reload.
// Entries are replayed oldest-first; addHistoryItem prepends, so the
// newest entry ends up on top, exactly as it would after live recording.
// The latest assessment shown is the newest successful one.
function restoreHistoryFromLog() {
  let latestOk = null;
  for (const entry of log.entries()) {
    if (entry.status === "ok" && entry.response) {
      latestOk = entry.response;
      const product = PRODUCT_BY_ID[entry.response.product];
      const name = product ? product.displayName : entry.response.product;
      const category = entry.response.assessment.category;
      addHistoryItem({
        title: entry.response.assessment.requires_human_review
          ? `${name} · ${category} (human review)`
          : `${name} · ${category}`,
        timestamp: entry.response.timestamp,
        body: entry.response.assessment.summary,
        kind: entry.response.assessment.requires_human_review ? "review" : "ok",
        assessment: entry.response,
      });
    } else {
      addHistoryItem({
        title: "Analysis request failed",
        timestamp: entry.request_timestamp,
        body: entry.error || "Unknown error.",
        kind: "error",
      });
    }
  }
  if (latestOk) renderLatest(latestOk);
}

// Backend health check: asks the server's health route whether it is up
// and what its model state is. A reachable server with the model held
// is reported exactly that way — reachable is not the same as ready to
// assess, and this check never sends a frame.
let backendChecking = false;

els.btnBackendCheck.addEventListener("click", async () => {
  if (backendChecking) return;
  backendChecking = true;
  els.btnBackendCheck.disabled = true;
  els.backendHealth.textContent = `Checking ${currentEndpoint()} …`;
  // Reset generation, captured like the assessment paths capture it: a
  // health check outstanding across Reset must not repaint the health
  // line Reset just cleared ("Backend health not checked yet.") with a
  // pre-reset result, success or failure — that result describes a
  // check from before the reset, and Reset's whole point for this line
  // is that a pre-reset check does not linger as if it were current.
  // The button still re-enables in finally; only the text is guarded,
  // exactly like submitAssessment guards its display updates but still
  // records its log entry.
  const generation = viewGeneration;
  try {
    const health = await checkHealth(currentEndpoint());
    const products = health.products.join(", ");
    const modelState = health.live_enabled
      ? "live calls on"
      : health.model.configured
        ? "key configured, live calls held"
        : "key not configured, live calls held";
    if (generation === viewGeneration) {
      els.backendHealth.textContent =
        `Backend reachable: ${health.service} · products: ${products} · model: ${modelState}. ` +
        "This does not mean an assessment is available — an assess request still has to succeed.";
    }
  } catch (err) {
    if (generation === viewGeneration) {
      els.backendHealth.textContent = `Backend health check failed: ${err.message}`;
    }
  } finally {
    backendChecking = false;
    els.btnBackendCheck.disabled = false;
  }
});

// Initial state.
if (cameraUnsupported) {
  setCameraState("This browser does not expose a camera API (getUserMedia unavailable). A secure context (HTTPS or localhost) and a camera are required.");
}
renderProduct();
updateSamplingDisclosure();
restoreHistoryFromLog();
updateLogStats();
refreshButtons();
