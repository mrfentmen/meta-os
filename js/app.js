// Meta Sentinel frontend wiring. Connects camera -> sampler -> analysis
// client -> event display + session log. This module contains no detection
// logic and no sample data: if the backend is unreachable, the UI shows the
// error and nothing else.

import { Camera, cameraSupported } from "./camera.js";
import { FrameSampler } from "./sampler.js";
import { assessFrame, AssessError } from "./client.js";
import { SessionLog } from "./log.js";

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
  endpoint: $("endpoint"),
  intervalSeconds: $("interval-seconds"),
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
};

const camera = new Camera(els.video);
const log = new SessionLog();

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
  const value = els.scenarioLabel.value.trim();
  return value === "" ? null : value;
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
  const wrap = document.createElement("div");

  const head = document.createElement("p");
  head.className = "assessment-head";
  const type = document.createElement("strong");
  type.textContent = assessment.event_type;
  head.appendChild(type);
  const time = document.createElement("span");
  time.className = "assessment-time";
  time.textContent = ` ${assessment.timestamp}`;
  head.appendChild(time);
  if (assessment.requires_human_review) {
    const flag = document.createElement("span");
    flag.className = "review-flag";
    flag.textContent = " REQUIRES HUMAN REVIEW";
    head.appendChild(flag);
  }
  wrap.appendChild(head);

  const text = document.createElement("p");
  text.textContent = assessment.assessment;
  wrap.appendChild(text);

  if (assessment.observations.length > 0) {
    const list = document.createElement("ul");
    list.className = "observations";
    for (const obs of assessment.observations) {
      const item = document.createElement("li");
      const action = document.createElement("strong");
      action.textContent = obs.action;
      item.appendChild(action);
      item.appendChild(document.createTextNode(` — ${obs.evidence} (confidence ${obs.confidence.toFixed(2)})`));
      list.appendChild(item);
    }
    wrap.appendChild(list);
  }

  const uncertainty = document.createElement("p");
  uncertainty.className = "uncertainty";
  uncertainty.textContent = `Uncertainty: ${assessment.uncertainty}`;
  wrap.appendChild(uncertainty);

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

async function runSample() {
  const endpoint = currentEndpoint();
  const timestamp = new Date().toISOString();
  let image;
  try {
    image = camera.captureFrame(els.captureCanvas);
  } catch (err) {
    log.record({
      requestTimestamp: timestamp,
      latencyMs: 0,
      status: "invalid_response",
      error: `Frame capture failed: ${err.message}`,
      scenarioLabel: currentScenarioLabel(),
    });
    updateLogStats();
    throw err;
  }

  els.inFlight.hidden = false;
  const started = performance.now();
  try {
    const assessment = await assessFrame(endpoint, { timestamp, image });
    const latencyMs = Math.round(performance.now() - started);
    log.record({
      requestTimestamp: timestamp,
      latencyMs,
      status: "ok",
      response: assessment,
      scenarioLabel: currentScenarioLabel(),
    });
    setBackendStatus("connected", `Model backend connected: ${endpoint}`);
    renderLatest(assessment);
    addHistoryItem({
      title: assessment.requires_human_review ? `${assessment.event_type} (human review)` : assessment.event_type,
      timestamp: assessment.timestamp,
      body: assessment.assessment,
      kind: assessment.requires_human_review ? "review" : "ok",
    });
  } catch (err) {
    const latencyMs = Math.round(performance.now() - started);
    const kind = err instanceof AssessError ? err.kind : "network";
    const status = kind === "http" ? "http_error" : kind === "invalid" ? "invalid_response" : "network_error";
    log.record({
      requestTimestamp: timestamp,
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

const sampler = new FrameSampler({
  intervalMs: 3000,
  onSample: runSample,
  // Failures are already rendered and logged inside runSample; the tick
  // callback only keeps the on-screen counters current.
  onTick: () => updateSamplerStats(),
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
  });
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `meta-sentinel-session-log-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
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
updateSamplingDisclosure();
updateLogStats();
refreshButtons();
