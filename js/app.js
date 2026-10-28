// Meta Trio frontend wiring. Connects camera -> sampler -> analysis
// client -> event display + session log, for whichever of the three
// products (Vigiles, Ignis, Sanitas) is selected. This module contains no
// detection logic and no sample data: if the backend is unreachable, the
// UI shows the error and nothing else.

import { Camera, cameraSupported } from "./camera.js";
import { FrameSampler } from "./sampler.js";
import { assessFrame, AssessError } from "./client.js";
import { SessionLog } from "./log.js";
import { PRODUCT_BY_ID, isProductId } from "./products.js";
import { isSupportedImageFile, readFileAsDataURL } from "./image_input.js";

const $ = (id) => document.getElementById(id);

const els = {
  video: $("preview"),
  captureCanvas: $("capture-canvas"),
  cameraIndicator: $("camera-indicator"),
  cameraState: $("camera-state"),
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
  intervalSeconds: $("interval-seconds"),
  scenarioSelect: $("scenario-select"),
  scenarioLabel: $("scenario-label"),
  samplingDisclosure: $("sampling-disclosure"),
  backendStatus: $("backend-status"),
  inFlight: $("in-flight"),
  samplerStats: $("sampler-stats"),
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
};

const camera = new Camera(els.video);
const log = new SessionLog();

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

function currentIntervalMs() {
  const seconds = Number(els.intervalSeconds.value);
  const safe = Number.isFinite(seconds) && seconds >= 1 && seconds <= 60 ? seconds : 3;
  return Math.round(safe * 1000);
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

function updateLogStats() {
  els.logStats.textContent = `Session log entries: ${log.count}`;
}

function refreshButtons() {
  const camActive = camera.active;
  els.btnCameraStart.disabled = camActive;
  els.btnCameraStop.disabled = !camActive;
  els.btnAnalysisStart.disabled = !camActive || sampler.running;
  els.btnAnalysisStop.disabled = !sampler.running;
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

function renderLatest(assessment) {
  const product = PRODUCT_BY_ID[assessment.product] || null;
  const wrap = document.createElement("div");

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

  const text = document.createElement("p");
  text.textContent = assessment.assessment.summary;
  wrap.appendChild(text);

  if (assessment.observations.length > 0) {
    const list = document.createElement("ul");
    list.className = "observations";
    for (const obs of assessment.observations) {
      const item = document.createElement("li");
      const category = document.createElement("strong");
      category.textContent = obs.category;
      item.appendChild(category);
      const confidence = obs.confidence === null ? "confidence not reported" : `confidence ${obs.confidence.toFixed(2)}`;
      item.appendChild(document.createTextNode(` — ${obs.description} (${obs.evidence}; ${confidence})`));
      list.appendChild(item);
    }
    wrap.appendChild(list);
  }

  const uncertainty = document.createElement("p");
  uncertainty.className = "uncertainty";
  uncertainty.textContent =
    assessment.assessment.uncertainty.length > 0
      ? `Uncertainty: ${assessment.assessment.uncertainty.join(" ")}`
      : "Uncertainty: none stated.";
  wrap.appendChild(uncertainty);

  const processing = document.createElement("p");
  processing.className = "note mono";
  processing.textContent =
    `Model: ${assessment.processing.model} · server latency: ` +
    (assessment.processing.latency_ms === null ? "not reported" : `${assessment.processing.latency_ms} ms`);
  wrap.appendChild(processing);

  els.latest.replaceChildren(wrap);
}

function addHistoryItem({ title, timestamp, body, kind }) {
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
    });
    return assessment;
  } catch (err) {
    const latencyMs = Math.round(performance.now() - started);
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
    log.record({
      requestTimestamp: timestamp,
      product,
      latencyMs: null,
      status: "invalid_response",
      error: `Frame capture failed: ${err.message}`,
      scenarioLabel: currentScenarioLabel(),
    });
    updateLogStats();
    throw err;
  }
  await submitAssessment(product, timestamp, image);
}

// Still-image input state: the chosen file's data URL lives in memory
// only, and is cleared by Reset. It is assessed under whichever product
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
    els.imagePreview.src = stillImageDataUrl;
    els.imagePreview.hidden = false;
    els.imageState.textContent =
      `Image ready: ${file.name}. Tap “Assess this image” to send it once to the assessment endpoint, under the product selected above. It is not stored by this app.`;
    els.btnImageAssess.disabled = false;
  } catch (err) {
    els.imageState.textContent = `Could not read that image: ${err.message}`;
  }
});

els.btnImageAssess.addEventListener("click", async () => {
  if (!stillImageDataUrl || stillImageAssessing) return;
  stillImageAssessing = true;
  els.btnImageAssess.disabled = true;
  setBackendStatus("unknown", `Contacting model backend: ${currentEndpoint()} …`);
  try {
    await submitAssessment(currentProductId, new Date().toISOString(), stillImageDataUrl);
  } catch {
    // submitAssessment already rendered and logged the failure.
  } finally {
    stillImageAssessing = false;
    els.btnImageAssess.disabled = !stillImageDataUrl;
  }
});

els.btnCameraStart.addEventListener("click", async () => {
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
  stillImageDataUrl = null;
  els.imageInput.value = "";
  els.imagePreview.hidden = true;
  els.imagePreview.removeAttribute("src");
  els.imageState.textContent = "No image chosen.";
  els.btnImageAssess.disabled = true;
  setCameraState("Camera stopped. View reset.");
  setBackendStatus("unknown", "Model backend status unknown. Start analysis to contact the endpoint.");
  els.latest.textContent = "No assessment received yet.";
  els.history.replaceChildren();
  els.historyEmpty.hidden = false;
  refreshButtons();
  updateSamplerStats();
});

els.intervalSeconds.addEventListener("change", () => {
  updateSamplingDisclosure();
  if (sampler.running) {
    sampler.setIntervalMs(currentIntervalMs());
  }
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

// Initial state.
if (!cameraSupported()) {
  setCameraState("This browser does not expose a camera API (getUserMedia unavailable). A secure context (HTTPS or localhost) and a camera are required.");
  els.btnCameraStart.disabled = true;
}
renderProduct();
updateSamplingDisclosure();
updateLogStats();
refreshButtons();
