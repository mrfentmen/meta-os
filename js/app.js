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
