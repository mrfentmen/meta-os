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
// sampler runs, and reworded when the interval changes mid-run.
function updateAnalysisActive() {
  const seconds = currentIntervalMs() / 1000;
  els.analysisActive.textContent =
    `Analysis active — sampling one frame every ${seconds} second${seconds === 1 ? "" : "s"}.`;
  els.analysisActive.hidden = !sampler.running;
}

function refreshButtons() {
  const camActive = camera.active;
  els.btnCameraStart.disabled = camActive;
  els.btnCameraStop.disabled = !camActive;
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

function renderLatest(assessment, earlierNote = null) {
  latestAssessmentShown = true;
  const product = PRODUCT_BY_ID[assessment.product] || null;
  const wrap = document.createElement("div");

  if (earlierNote) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = earlierNote;
    wrap.appendChild(note);
  }
  const head = document.createElement("p");
  head.className = "assessment-head";
  const type = document.createElement("strong");
  type.textContent = assessment.assessment.category;
  head.appendChild(type);
  const productEl = document.createElement("span");
  productEl.className = "assessment-product";
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
      const confidence = obs.confidence === null ? "confidence not reported" : `confidence ${obs.confidence.toFixed(2)}`;
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
    const uncertainty = document.createElement("p");
    uncertainty.className = "note";
    uncertainty.textContent = "The model reported no uncertainty items.";
    wrap.appendChild(uncertainty);
  }

  const processing = document.createElement("p");
  processing.className = "note mono";
  processing.textContent =
    `Model: ${assessment.processing.model} · server latency: ` +
    (assessment.processing.latency_ms === null ? "not reported" : `${assessment.processing.latency_ms} ms`);
  wrap.appendChild(processing);

  els.latest.replaceChildren(wrap);
}

function addHistoryItem({ title, timestamp, body, kind, assessment = null }) {
  els.historyEmpty.hidden = true;
  const item = document.createElement("li");
  item.className = `history-item history-${kind}`;

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
// simply swallow it (it is already on screen).
async function submitAssessment(product, timestamp, image) {
  const endpoint = currentEndpoint();
  els.inFlight.hidden = false;
  if (!latestAssessmentShown) {
    els.latest.textContent = "Waiting for the first assessment…";
  }
  const started = performance.now();
  try {
    const assessment = await assessFrame(endpoint, { product, timestamp, image });
    const latencyMs = Math.round(performance.now() - started);
    updateLastRoundTrip(latencyMs);
    log.record({
      requestTimestamp: timestamp,
      product,
      latencyMs,
      status: "ok",
      response: assessment,
      scenarioLabel: currentScenarioLabel(),
    });
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
    if (latencyMs !== null) {
      updateLastRoundTrip(latencyMs);
    }
    const kind = err instanceof AssessError ? err.kind : "network";
    const status = kind === "http" ? "http_error" : kind === "invalid" ? "invalid_response" : "network_error";
    log.record({
      requestTimestamp: timestamp,
      product,
      latencyMs,
      status,
      error: err.message,
      scenarioLabel: currentScenarioLabel(),
    });
    setBackendStatus("error", `Model backend not connected: ${err.message}`);
    if (!latestAssessmentShown) {
      els.latest.textContent = `Model backend not connected: ${err.message}`;
    }
    addHistoryItem({
      title: "Analysis request failed",
      timestamp,
      body: err.message,
      kind: "error",
    });
    throw err;
  } finally {
    els.inFlight.hidden = true;
    updateLogStats();
  }
}

async function runSample() {
  const product = currentProductId;
  const timestamp = new Date().toISOString();
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
      scenarioLabel: currentScenarioLabel(),
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
  await submitAssessment(product, timestamp, image);
}

// Still-image input state: the chosen file's data URL lives in memory
// only, and is cleared by its Clear button or by Reset. It is assessed under whichever product
// is selected when "Assess this image" is tapped, exactly like the next
// live sampled frame.
let stillImageDataUrl = null;
let stillImageAssessing = false;

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

// Clears only the still-image input (preview, file choice, Assess
// disabled) without stopping the camera or analysis — the web match for
// the native panel's Clear button. Reset reuses this for the same panel.
function clearStillImageInput() {
  stillImageDataUrl = null;
  els.imageInput.value = "";
  els.imagePreview.hidden = true;
  els.imagePreview.removeAttribute("src");
  els.imageState.textContent = "No image chosen.";
  els.btnImageAssess.disabled = true;
  els.imageAssessing.hidden = true;
}

els.btnImageClear.addEventListener("click", () => {
  clearStillImageInput();
});

els.imageInput.addEventListener("change", async () => {
  const file = els.imageInput.files && els.imageInput.files[0];
  stillImageDataUrl = null;
  els.imagePreview.hidden = true;
  els.imagePreview.removeAttribute("src");
  els.btnImageAssess.disabled = true;
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
    if (Math.max(probe.naturalWidth, probe.naturalHeight) > MAX_FRAME_DIMENSION) {
      stillImageDataUrl = downscaleImageToDataURL(probe, els.captureCanvas);
    }
    els.imagePreview.src = stillImageDataUrl;
    els.imagePreview.hidden = false;
    els.imageState.textContent =
      `Image ready: ${file.name}. Tap “Assess this image” to send it once to the assessment endpoint, under the product selected above. It is not stored by this app.`;
    els.btnImageAssess.disabled = false;
  } catch (err) {
    stillImageDataUrl = null;
    els.btnImageAssess.disabled = true;
    els.imageState.textContent = `Could not read that image: ${err.message}`;
  }
});

els.btnImageAssess.addEventListener("click", async () => {
  if (!stillImageDataUrl || stillImageAssessing) return;
  stillImageAssessing = true;
  els.btnImageAssess.disabled = true;
  // Native parity: the native Still image panel shows "Sending still
  // image…" in the panel while the request is outstanding. The web
  // panel only had the generic in-flight line in the distant Camera
  // panel, so a user watching this panel saw nothing move while the
  // request was out. Show the same line here, and hide it again when
  // the request settles, success or failure.
  els.imageAssessing.hidden = false;
  setBackendStatus("unknown", `Contacting model backend: ${currentEndpoint()} …`);
  try {
    await submitAssessment(currentProductId, new Date().toISOString(), stillImageDataUrl);
  } catch {
    // submitAssessment already rendered and logged the failure.
  } finally {
    stillImageAssessing = false;
    els.imageAssessing.hidden = true;
    els.btnImageAssess.disabled = !stillImageDataUrl;
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

function clearVideoInput() {
  if (videoObjectUrl) {
    URL.revokeObjectURL(videoObjectUrl);
    videoObjectUrl = null;
  }
  els.videoPreview.removeAttribute("src");
  els.videoPreview.load();
  els.videoPreview.hidden = true;
  els.btnVideoAssess.disabled = true;
  els.videoAssessing.hidden = true;
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
  // will succeed. The button enables only while a video is loaded.
  els.btnVideoAssess.disabled = !videoObjectUrl;
});

els.videoPreview.addEventListener("error", () => {
  els.videoState.textContent = "That video could not be played in this browser. Try another file.";
  els.btnVideoAssess.disabled = true;
});

els.btnVideoAssess.addEventListener("click", async () => {
  if (!videoObjectUrl || videoAssessing) return;
  videoAssessing = true;
  els.btnVideoAssess.disabled = true;
  // Native parity: the native video panel shows "Sending video
  // frame…" in the panel while the request is outstanding, for the
  // same reason as the still-image note above — the generic in-flight
  // line lives in the Camera panel, not here.
  els.videoAssessing.hidden = false;
  setBackendStatus("unknown", `Contacting model backend: ${currentEndpoint()} …`);
  const timestamp = new Date().toISOString();
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
      scenarioLabel: currentScenarioLabel(),
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
    els.btnVideoAssess.disabled = false;
    return;
  }
  try {
    await submitAssessment(currentProductId, timestamp, image);
  } catch {
    // submitAssessment already rendered and logged the failure.
  } finally {
    videoAssessing = false;
    els.videoAssessing.hidden = true;
    els.btnVideoAssess.disabled = !videoObjectUrl;
  }
});

els.btnCameraStart.addEventListener("click", async () => {
  // Native parity: the native camera has a requesting-permission state
  // ("Waiting for camera permission…") while the system prompt is up.
  // The web panel said "Camera is off." through that whole wait, which
  // reads as if nothing is happening while the user decides. Say the
  // wait out loud, and keep Start disabled until the prompt resolves —
  // the native Start button is disabled in its requesting state too —
  // so a second tap cannot fire a second permission request. The
  // refreshButtons() at the end restores the button to the real state:
  // disabled once live, enabled again after a denied or failed start.
  els.btnCameraStart.disabled = true;
  setCameraState("Waiting for camera permission…");
  try {
    await camera.start();
    els.cameraIndicator.hidden = false;
    setCameraState("Camera is live. No frames are sent anywhere until analysis is started.");
  } catch (err) {
    els.cameraIndicator.hidden = true;
    setCameraState(describeCameraError(err));
  }
  refreshButtons();
});

els.btnCameraStop.addEventListener("click", () => {
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
  try {
    await camera.switchFacing(els.cameraFacing.value);
    if (camera.active) {
      els.cameraIndicator.hidden = false;
      setCameraState("Camera is live. No frames are sent anywhere until analysis is started.");
    }
  } catch (err) {
    els.cameraIndicator.hidden = true;
    setCameraState(describeCameraError(err));
  }
  refreshButtons();
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
  try {
    const health = await checkHealth(currentEndpoint());
    const products = health.products.join(", ");
    const modelState = health.live_enabled
      ? "live calls on"
      : health.model.configured
        ? "key configured, live calls held"
        : "key not configured, live calls held";
    els.backendHealth.textContent =
      `Backend reachable: ${health.service} · products: ${products} · model: ${modelState}. ` +
      "This does not mean an assessment is available — an assess request still has to succeed.";
  } catch (err) {
    els.backendHealth.textContent = `Backend health check failed: ${err.message}`;
  } finally {
    backendChecking = false;
    els.btnBackendCheck.disabled = false;
  }
});

// Initial state.
if (!cameraSupported()) {
  setCameraState("This browser does not expose a camera API (getUserMedia unavailable). A secure context (HTTPS or localhost) and a camera are required.");
  els.btnCameraStart.disabled = true;
}
renderProduct();
updateSamplingDisclosure();
restoreHistoryFromLog();
updateLogStats();
refreshButtons();
