// Meta Trio operations surface — the same capabilities in all three pages.
//
// The split into Vigiles, Ignis and Medicus left each page with its own idea
// and without the working parts the old console had: a camera wall, local
// camera and still/video input, an event history, a session log, map modes,
// Ctrl+K. This module restores those as one behaviour with no styling of its
// own. Each page imports it and paints the same class names from its own
// stylesheet, so the features match and the three still look like three
// different programs.
//
// Every failure is a value with a reason that names the endpoint. Nothing here
// invents an assessment, and a camera that cannot load a snapshot says so.

import { backendBase, backendLabel, clock, el, MAX_WATCHED } from "./core.js";

const SESSION_PREFIX = "metaos.trio.session.";
const CONFIG_PREFIX = "metaos.trio.config.";

const TABS = [
  ["wall", "Wall"],
  ["inputs", "Inputs"],
  ["history", "History"],
  ["log", "Log"],
  ["analytics", "Analytics"],
  ["system", "System"],
];

const SOURCES = {
  camera: "Watched camera",
  local: "Local camera",
  still: "Still image",
  video: "Recorded video",
};

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Private mode or a full quota. The session still works until reload.
  }
}

function pct(part, whole) {
  if (!whole) return "—";
  return Math.round((part / whole) * 100) + "%";
}

function median(values) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : Math.round((sorted[mid - 1] + sorted[mid]) / 2);
}

export function createOps({ store, division, mount, variant = "default" }) {
  const key = division.key;
  const session = read(SESSION_PREFIX + key, []);
  const rows = Array.isArray(session) ? session.slice(0, 500) : [];
  const config = Object.assign({ endpoint: "", scenario: "" }, read(CONFIG_PREFIX + key, {}));
  const seen = new Set();
  const media = {
    stream: null,
    cameraError: null,
    sampling: null,
    detail: null, // last media assessment, shown under the inputs
    lastImage: null,
  };
  let tab = "wall";
  let searchOpen = false;
  let helpOpen = false;
  let pendingClear = null;

  const endpointLabel = () =>
    config.endpoint.trim() || backendBase() + "/api/assess";

  // ------------------------------------------------------------ session log

  function addRow(entry) {
    rows.unshift(entry);
    if (rows.length > 500) rows.length = 500;
    write(SESSION_PREFIX + key, rows);
  }

  function syncFromStore() {
    let changed = false;
    for (const [id, r] of store.results) {
      const stamp = id + "@" + (r.at ?? 0);
      if (seen.has(stamp)) continue;
      seen.add(stamp);
      const cam = store.byId.get(id);
      addRow({
        at: r.at ?? Date.now(),
        id,
        name: cam ? cam.name : id,
        area: cam ? cam.area : "",
        status: r.status,
        category: r.category ?? null,
        summary: r.summary ?? "",
        flagged: Boolean(r.flagged),
        confidence: typeof r.confidence === "number" ? r.confidence : null,
        model: r.model ?? null,
        latency: typeof r.latency === "number" ? r.latency : null,
        product: r.product ?? division.product,
        source: "camera",
        scenario: config.scenario.trim() || null,
      });
      changed = true;
    }
    if (changed) render();
  }

  // --------------------------------------------------------------- framing

  const status = el("p", { class: "ops-status", role: "status", text: "" });
  const sourceLine = el("p", { class: "ops-source", text: "" });
  const body = el("div", { class: "ops-body" });
  const tabButtons = new Map();

  const nav = el(
    "nav",
    { class: "ops-tabs", "aria-label": "Operations sections" },
    TABS.map(([id, label]) => {
      const b = el("button", {
        class: "ops-tab",
        type: "button",
        "data-tab": id,
        text: label,
        "aria-pressed": id === tab ? "true" : "false",
      });
      b.addEventListener("click", () => show(id));
      tabButtons.set(id, b);
      return b;
    })
  );

  const closeBtn = el("button", {
    class: "ops-close",
    type: "button",
    "aria-label": "Close operations",
    title: "Close operations",
    html: "",
  });
  closeBtn.innerHTML =
    '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.4" fill="none"/></svg>';
  closeBtn.addEventListener("click", () => close());

  const root = el("section", { class: "ops", "data-ops": variant, hidden: true, "aria-label": "Operations" }, [
    el("header", { class: "ops-head" }, [
      el("div", { class: "ops-title" }, [
        el("h2", { text: "Operations" }),
        el("span", { class: "ops-badge", text: division.dept + " · " + division.brief }),
      ]),
      el("div", { class: "ops-head-right" }, [sourceLine, closeBtn]),
    ]),
    nav,
    status,
    body,
  ]);
  mount.append(root);

  function show(next) {
    tab = next;
    for (const [id, b] of tabButtons) b.setAttribute("aria-pressed", id === next ? "true" : "false");
    root.dataset.tab = next;
    render();
  }

  function open(next = tab) {
    root.hidden = false;
    show(next);
    root.classList.add("open");
  }

  function close() {
    root.classList.remove("open");
    root.hidden = true;
  }

  function toggle(next) {
    if (root.hidden) open(next);
    else close();
  }

  // ------------------------------------------------------------- primitives

  function note(text, kind = "") {
    return el("p", { class: "ops-note " + kind, text });
  }

  function block(title, hint, children) {
    return el("section", { class: "ops-block" }, [
      el("div", { class: "ops-block-head" }, [
        el("h3", { text: title }),
        hint ? el("p", { class: "ops-hint", text: hint }) : null,
      ]),
      ...[].concat(children),
    ]);
  }

  function action(label, onClick, cls = "") {
    const b = el("button", { class: "ops-btn " + cls, type: "button", text: label });
    b.addEventListener("click", onClick);
    return b;
  }

  function kv(label, value, cls = "") {
    return el("div", { class: "ops-kv " + cls }, [
      el("span", { class: "ops-k", text: label }),
      el("span", { class: "ops-v", text: value }),
    ]);
  }

  function metric(label, value, hint) {
    return el("div", { class: "ops-metric" }, [
      el("span", { class: "ops-metric-v", text: String(value) }),
      el("span", { class: "ops-metric-k", text: label }),
      hint ? el("span", { class: "ops-metric-h", text: hint }) : null,
    ]);
  }

  function table(headers, rowsOut) {
    return el("div", { class: "ops-table", role: "table" }, [
      el("div", { class: "ops-tr ops-thead", role: "row" }, headers.map((h) => el("span", { role: "columnheader", text: h }))),
      ...rowsOut.map((cells) =>
        el(
          "div",
          { class: "ops-tr", role: "row" },
          cells.map((c) => el("span", { role: "cell", text: c === null || c === undefined ? "—" : String(c) }))
        )
      ),
    ]);
  }

  // ------------------------------------------------------------------- wall

  function panelWall() {
    const watched = [...store.watch].map((id) => store.byId.get(id)).filter(Boolean);
    const out = [
      note(
        "Only watched cameras are sampled. A wall card shows the camera's own latest frame; a card that cannot load says so instead of going blank.",
        "muted"
      ),
    ];

    if (watched.length === 0) {
      out.push(
        note(
          "No cameras on the watch list. Watch one from the map or the camera list — the wall fills here, up to " +
            MAX_WATCHED +
            "."
        )
      );
      return out;
    }

    out.push(
      el(
        "div",
        { class: "ops-wall" },
        watched.map((cam) => {
          const r = store.results.get(cam.id) ?? null;
          const img = el("img", { class: "ops-wall-img", alt: "Latest frame from " + cam.name, loading: "lazy" });
          img.src = cam.imageUrl + (cam.imageUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
          img.addEventListener("error", () => {
            img.replaceWith(
              el("p", {
                class: "ops-wall-missing",
                text: "Frame did not load from the camera host. It is a public internet service and this machine may be offline.",
              })
            );
          });
          const busy = store.busy.has(cam.id);
          const last = r
            ? r.status === "failed"
              ? "Failed: " + r.reason
              : r.category + " · " + (r.latency ?? 0) + " ms" + (r.flagged ? " · needs a look" : "")
            : "Not assessed yet.";
          const assess = action(busy ? "Assessing…" : "Assess", () => store.assess(cam.id), "primary");
          assess.disabled = busy;
          const unwatch = action("Unwatch", () => store.toggleWatch(cam.id), "ghost");
          return el("article", { class: "ops-wall-card" }, [
            img,
            el("div", { class: "ops-wall-body" }, [
              el("h4", { text: cam.name }),
              el("p", { class: "ops-wall-area", text: cam.area }),
              el("p", { class: "ops-wall-last " + (r && r.status === "failed" ? "bad" : r && r.flagged ? "flag" : ""), text: last }),
              el("div", { class: "ops-row" }, [assess, unwatch]),
            ]),
          ]);
        })
      )
    );
    return out;
  }

  // ----------------------------------------------------------------- inputs

  const mediaStatus = el("p", { class: "ops-note", role: "status", text: "" });
  const mediaDetail = el("div", { class: "ops-detail" });
  const liveVideo = el("video", { class: "ops-video", playsinline: true, muted: true, autoplay: true });
  const stillPreview = el("img", { class: "ops-video", alt: "Chosen still image preview", hidden: true });
  const clipVideo = el("video", { class: "ops-video", controls: true, playsinline: true, hidden: true });
  let stillData = null;
  let stillName = "";
  let clipName = "";
  let startCameraBtn;
  let stopCameraBtn;
  let grabLiveBtn;
  let assessStillBtn;
  let grabClipBtn;
  let sampleBtn;
  const sampleSeconds = el("input", { class: "ops-input", type: "number", min: "5", max: "120", step: "5", value: "15", "aria-label": "Sampling interval in seconds" });

  function setMediaStatus(text, kind = "") {
    mediaStatus.textContent = text;
    mediaStatus.className = "ops-note " + kind;
  }

  function showMediaResult(outcome, label) {
    if (!outcome.ok) {
      mediaDetail.replaceChildren(note(label + " failed: " + outcome.reason, "bad"));
      return;
    }
    const { a, latency, model } = outcome;
    mediaDetail.replaceChildren(
      el("p", { class: "ops-cat " + (a.requires_human_review ? "flag" : ""), text: a.category }),
      el("p", { class: "ops-sum", text: a.summary || "No summary returned." }),
      el("p", { class: "ops-meta", text: latency + " ms" + (model ? " · " + model : "") + (a.requires_human_review ? " · needs a human look" : " · no flag") })
    );
  }

  async function postImage(image, source, name) {
    const endpoint = config.endpoint.trim() || backendBase() + "/api/assess";
    const started = Date.now();
    let res;
    try {
      res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product: division.product,
          timestamp: new Date().toISOString(),
          image,
        }),
      });
    } catch {
      return { ok: false, reason: "endpoint unreachable at " + endpoint };
    }
    const payload = await res.json().catch(() => null);
    if (!res.ok) {
      const detail = payload && typeof payload.error === "string" ? payload.error : "no error body";
      return { ok: false, reason: "HTTP " + res.status + " from " + endpoint + ": " + detail };
    }
    if (payload && typeof payload.error === "string") return { ok: false, reason: payload.error };
    const a = payload && payload.assessment ? payload.assessment : null;
    if (!a || typeof a.category !== "string") {
      return { ok: false, reason: "response from " + endpoint + " had no assessment.category" };
    }
    const latency = Date.now() - started;
    const model = payload.processing && payload.processing.model ? payload.processing.model : null;
    addRow({
      at: Date.now(),
      id: "media:" + source + ":" + Date.now(),
      name,
      area: SOURCES[source],
      status: "ok",
      category: a.category,
      summary: typeof a.summary === "string" ? a.summary : "",
      flagged: a.requires_human_review === true,
      confidence: typeof a.confidence === "number" ? a.confidence : null,
      model,
      latency,
      product: payload.product ?? division.product,
      source,
      scenario: config.scenario.trim() || null,
    });
    render();
    return { ok: true, a, latency, model };
  }

  function grab(video) {
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return { ok: false, reason: "the video has no decoded frame yet" };
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    canvas.getContext("2d").drawImage(video, 0, 0, w, h);
    return { ok: true, image: canvas.toDataURL("image/jpeg", 0.82) };
  }

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setMediaStatus(
        "This window has no getUserMedia, so a local camera cannot be opened here. Still image and recorded video below need no camera.",
        "bad"
      );
      return;
    }
    try {
      media.stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      liveVideo.srcObject = media.stream;
      liveVideo.hidden = false;
      media.cameraError = null;
      startCameraBtn.disabled = true;
      stopCameraBtn.disabled = false;
      grabLiveBtn.disabled = false;
      setMediaStatus("Local camera live. Nothing is sent until you press a button or start sampling.", "ok");
    } catch (err) {
      media.cameraError = err && err.name ? err.name : "unknown error";
      setMediaStatus("Camera was refused (" + media.cameraError + "). Permission is a person's decision; this app does not retry.", "bad");
    }
  }

  function stopCamera() {
    if (media.stream) for (const track of media.stream.getTracks()) track.stop();
    media.stream = null;
    liveVideo.srcObject = null;
    liveVideo.hidden = true;
    if (media.sampling) stopSampling("Sampling stopped with the camera.");
    startCameraBtn.disabled = false;
    stopCameraBtn.disabled = true;
    grabLiveBtn.disabled = true;
    setMediaStatus("Camera stopped.");
  }

  async function assessLive() {
    if (!media.stream) {
      setMediaStatus("No live camera. Start one first.", "bad");
      return;
    }
    const frame = grab(liveVideo);
    if (!frame.ok) {
      setMediaStatus(frame.reason, "bad");
      return;
    }
    setMediaStatus("Sending one frame to " + endpointLabel() + "…");
    const outcome = await postImage(frame.image, "local", "Local camera");
    if (outcome.ok) setMediaStatus("Answered in " + outcome.latency + " ms.");
    else setMediaStatus(outcome.reason, "bad");
    showMediaResult(outcome, "Local camera");
  }

  async function assessStill() {
    if (!stillData) {
      setMediaStatus("No image chosen.", "bad");
      return;
    }
    setMediaStatus("Sending " + (stillName || "the chosen image") + " to " + endpointLabel() + "…");
    const outcome = await postImage(stillData, "still", stillName || "Still image");
    if (outcome.ok) setMediaStatus("Answered in " + outcome.latency + " ms.");
    else setMediaStatus(outcome.reason, "bad");
    showMediaResult(outcome, stillName || "Still image");
  }

  async function assessClip() {
    if (!clipVideo.src) {
      setMediaStatus("No video chosen.", "bad");
      return;
    }
    const frame = grab(clipVideo);
    if (!frame.ok) {
      setMediaStatus(frame.reason, "bad");
      return;
    }
    const label = clipName || "Recorded video";
    setMediaStatus("Sending one frame of " + label + " to " + endpointLabel() + "…");
    const outcome = await postImage(frame.image, "video", label);
    if (outcome.ok) setMediaStatus("Answered in " + outcome.latency + " ms.");
    else setMediaStatus(outcome.reason, "bad");
    showMediaResult(outcome, label);
  }

  async function sampleOnce() {
    const result = await store.assessWatched();
    if (!result.ok) setMediaStatus(result.reason, "bad");
    else setMediaStatus("Sampled " + result.results.length + " watched camera(s).");
  }

  function startSampling() {
    if (store.watch.size === 0) {
      setMediaStatus("Nothing is on the watch list, so there is nothing to sample.", "bad");
      return;
    }
    const seconds = Math.max(5, Math.min(120, Number(sampleSeconds.value) || 15));
    if (media.sampling) clearInterval(media.sampling);
    media.sampling = setInterval(sampleOnce, seconds * 1000);
    sampleBtn.textContent = "Stop sampling";
    setMediaStatus("Sampling " + store.watch.size + " watched camera(s) every " + seconds + " s.");
  }

  function stopSampling(reason = "Sampling stopped.") {
    if (media.sampling) clearInterval(media.sampling);
    media.sampling = null;
    if (sampleBtn) sampleBtn.textContent = "Start sampling";
    setMediaStatus(reason);
  }

  // The inputs panel owns a live MediaStream, a chosen file and a decode
  // result. Rebuilding it on every store emit would kill the stream and reset
  // the buttons, so it is built exactly once and reused.
  let inputsBuilt = false;
  const inputsChildren = [];

  function buildInputs() {
    startCameraBtn = action("Start camera", startCamera, "primary");
    stopCameraBtn = action("Stop camera", stopCamera, "ghost");
    stopCameraBtn.disabled = true;
    grabLiveBtn = action("Assess this frame", assessLive);
    grabLiveBtn.disabled = true;
    assessStillBtn = action("Assess this image", assessStill);
    assessStillBtn.disabled = true;
    grabClipBtn = action("Assess this frame", assessClip);
    grabClipBtn.disabled = true;
    sampleBtn = action("Start sampling", () => (media.sampling ? stopSampling() : startSampling()));

    const stillInput = el("input", { class: "ops-file", type: "file", accept: "image/*", "aria-label": "Choose a still image" });
    stillInput.addEventListener("change", async () => {
      const file = stillInput.files && stillInput.files[0];
      if (!file) return;
      stillName = file.name;
      const dataUrl = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => resolve("");
        reader.readAsDataURL(file);
      });
      if (!dataUrl.startsWith("data:image/")) {
        setMediaStatus("That file is not an image this window can decode.", "bad");
        return;
      }
      // The assess API takes JPEG only; re-encode through a canvas so a PNG or
      // a HEIC-decodable image is accepted on the same terms as a live frame.
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        canvas.getContext("2d").drawImage(img, 0, 0);
        stillData = canvas.toDataURL("image/jpeg", 0.85);
        stillPreview.src = stillData;
        stillPreview.hidden = false;
        assessStillBtn.disabled = false;
        setMediaStatus("Image ready: " + stillName + " (" + img.naturalWidth + "×" + img.naturalHeight + ").");
      };
      img.onerror = () => {
        stillData = null;
        assessStillBtn.disabled = true;
        setMediaStatus("That image did not decode in this window.", "bad");
      };
      img.src = dataUrl;
    });

    const clipInput = el("input", { class: "ops-file", type: "file", accept: "video/*", "aria-label": "Choose a recorded video" });
    clipInput.addEventListener("change", () => {
      const file = clipInput.files && clipInput.files[0];
      if (!file) return;
      clipName = file.name;
      clipVideo.src = URL.createObjectURL(file);
      clipVideo.hidden = false;
      grabClipBtn.disabled = false;
      setMediaStatus("Video ready: " + clipName + ". Pause on a frame, then assess it.");
    });

    const endpointInput = el("input", { class: "ops-input", type: "text", value: config.endpoint, placeholder: backendBase() + "/api/assess", spellcheck: "false", "aria-label": "Assessment endpoint" });
    endpointInput.addEventListener("change", () => {
      config.endpoint = endpointInput.value.trim();
      write(CONFIG_PREFIX + key, config);
      setMediaStatus("Assessment endpoint is now " + endpointLabel() + ".");
    });
    const scenarioInput = el("input", { class: "ops-input", type: "text", value: config.scenario, placeholder: "e.g. staged-fall-01", "aria-label": "Scenario label written to the session log" });
    scenarioInput.addEventListener("change", () => {
      config.scenario = scenarioInput.value.trim();
      write(CONFIG_PREFIX + key, config);
      setMediaStatus("Scenario label saved. It is written to new log entries only.");
    });

    inputsChildren.push(
      note(
        "These inputs send one frame each to the assessment endpoint. Nothing is stored on this machine and no camera runs in the background.",
        "muted"
      ),
      block("Local camera", "A webcam in this window, if the device has one.", [
        liveVideo,
        el("div", { class: "ops-row" }, [startCameraBtn, stopCameraBtn, grabLiveBtn]),
      ]),
      block("Still image", "For a photograph or a screenshot.", [
        stillInput,
        stillPreview,
        el("div", { class: "ops-row" }, [assessStillBtn]),
      ]),
      block("Recorded video", "One frame of a clip, not the clip.", [
        clipInput,
        clipVideo,
        el("div", { class: "ops-row" }, [grabClipBtn]),
      ]),
      block("Sampling", "Assess every watched camera on a timer.", [
        el("div", { class: "ops-row" }, [
          el("label", { class: "ops-field" }, [el("span", { text: "Every (s)" }), sampleSeconds]),
          sampleBtn,
        ]),
        note("Sampling sends one frame per watched camera per interval. It stops when the tab closes.", "muted"),
      ]),
      block("Configuration", "Applies to the next request, never to entries already logged.", [
        el("label", { class: "ops-field" }, [el("span", { text: "Endpoint" }), endpointInput]),
        el("label", { class: "ops-field" }, [el("span", { text: "Scenario label" }), scenarioInput]),
        note("Backend on this machine: " + backendBase() + " · product id " + division.product, "muted"),
      ]),
      mediaStatus,
      mediaDetail
    );
  }

  function panelInputs() {
    if (!inputsBuilt) {
      buildInputs();
      inputsBuilt = true;
    }
    // Flat, not nested: replaceChildren() turns an array argument into the
    // string "[object HTMLElement]" instead of appending its children.
    return inputsChildren;
  }

  // ---------------------------------------------------------------- history

  let historyDetail = null;

  function renderHistoryDetail(entry) {
    if (!historyDetail) return;
    if (!entry) {
      historyDetail.replaceChildren(note("Select an entry to see its assessment.", "muted"));
      return;
    }
    const cam = store.byId.get(entry.id);
    const steps = [
      ["Captured", entry.status === "ok" || !String(entry.summary || "").startsWith("Snapshot failed")],
      ["Sent to endpoint", entry.status === "ok" || /HTTP \d/.test(String(entry.summary || entry.category || ""))],
      ["Response parsed", entry.status === "ok"],
      ["Recorded", true],
    ];
    const children = [
      el("h4", { text: entry.name }),
      el("p", { class: "ops-meta", text: clock(entry.at) + " · " + (SOURCES[entry.source] || entry.source) + (entry.scenario ? " · " + entry.scenario : "") }),
      entry.status === "ok"
        ? el("p", { class: "ops-cat " + (entry.flagged ? "flag" : ""), text: entry.category })
        : el("p", { class: "ops-cat bad", text: "Assessment failed" }),
      entry.summary ? el("p", { class: "ops-sum", text: entry.summary }) : null,
      el("p", {
        class: "ops-meta",
        text:
          (entry.latency === null ? "no latency recorded" : entry.latency + " ms") +
          (entry.model ? " · " + entry.model : "") +
          (entry.confidence === null ? "" : " · confidence " + entry.confidence) +
          (entry.flagged ? " · needs a human look" : ""),
      }),
      el(
        "ol",
        { class: "ops-steps" },
        steps.map(([label, done], i) =>
          el("li", { class: done ? "done" : "miss", text: (i + 1) + ". " + label + (done ? "" : " — not reached") })
        )
      ),
    ];
    if (entry.flagged) {
      const reviewed = store.reviewed.has(entry.id);
      const btn = action(reviewed ? "Reviewed" : "Mark reviewed", () => {
        if (!store.byId.has(entry.id)) return;
        store.markReviewed(entry.id);
        render();
      }, reviewed ? "ghost" : "primary");
      btn.disabled = reviewed || !cam;
      children.push(el("div", { class: "ops-row" }, [btn]));
      if (!cam) children.push(note("This entry came from an input, not a camera, so there is no queue item to review.", "muted"));
    }
    if (cam) {
      const focus = action("Show on map", () => store.setSelected(cam.id), "ghost");
      children.push(el("div", { class: "ops-row" }, [focus]));
    }
    historyDetail.replaceChildren(...children.filter(Boolean));
  }

  function panelHistory() {
    historyDetail = el("div", { class: "ops-detail" });
    const filter = el("input", { class: "ops-input", type: "search", placeholder: "Filter by camera, category or source", "aria-label": "Filter history" });
    const list = el("div", { class: "ops-list" });

    function draw() {
      const q = filter.value.trim().toLowerCase();
      const items = rows
        .filter(
          (r) =>
            !q ||
            String(r.name).toLowerCase().includes(q) ||
            String(r.category || "").toLowerCase().includes(q) ||
            String(SOURCES[r.source] || r.source).toLowerCase().includes(q)
        )
        .slice(0, 200);
      if (items.length === 0) {
        list.replaceChildren(note(rows.length ? "No entry matches that filter." : "No assessments yet. Assess a camera or use an input — each request is recorded here and survives a reload.", "muted"));
        return;
      }
      list.replaceChildren(
        ...items.map((r) => {
          const row = el("button", { class: "ops-hist-row", type: "button" }, [
            el("span", { class: "ops-hist-time", text: clock(r.at) }),
            el("span", { class: "ops-hist-name", text: r.name }),
            el("span", { class: "ops-hist-cat " + (r.status === "failed" ? "bad" : r.flagged ? "flag" : ""), text: r.status === "failed" ? "failed" : r.category }),
            el("span", { class: "ops-hist-src", text: SOURCES[r.source] || r.source }),
          ]);
          row.addEventListener("click", () => {
            for (const other of list.querySelectorAll(".ops-hist-row")) other.classList.remove("on");
            row.classList.add("on");
            renderHistoryDetail(r);
          });
          return row;
        })
      );
    }
    filter.addEventListener("input", draw);
    const out = [el("div", { class: "ops-row ops-row-between" }, [filter]), list, historyDetail];
    draw();
    renderHistoryDetail(null);
    return out;
  }

  // -------------------------------------------------------------------- log

  function stats() {
    const ok = rows.filter((r) => r.status === "ok");
    const failed = rows.filter((r) => r.status !== "ok");
    const latencies = ok.map((r) => r.latency).filter((n) => typeof n === "number");
    return { ok, failed, latencies };
  }

  function countBy(items, pick) {
    const map = new Map();
    for (const item of items) {
      const k = pick(item) ?? "—";
      map.set(k, (map.get(k) ?? 0) + 1);
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }

  function exportLog() {
    const payload = {
      division: division.key,
      product: division.product,
      exportedAt: new Date().toISOString(),
      endpoint: endpointLabel(),
      entries: rows,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "metaos-" + division.key + "-session.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function panelLog() {
    const { ok, failed, latencies } = stats();
    const first = rows.length ? rows[rows.length - 1].at : null;
    const last = rows.length ? rows[0].at : null;
    const e = el("div", { class: "ops-detail" });
    const exportBtn = action("Export JSON", exportLog);
    const clearBtn = action("Clear log", () => {
      if (pendingClear) {
        clearTimeout(pendingClear);
        pendingClear = null;
        rows.length = 0;
        write(SESSION_PREFIX + key, rows);
        clearBtn.textContent = "Clear log";
        render();
        return;
      }
      clearBtn.textContent = "Confirm clear";
      pendingClear = setTimeout(() => {
        pendingClear = null;
        clearBtn.textContent = "Clear log";
      }, 4000);
    }, "ghost");
    e.replaceChildren(
      el("div", { class: "ops-metrics" }, [
        metric("entries", rows.length, "this division, in this browser"),
        metric("answered", ok.length, "assessments returned"),
        metric("failed", failed.length, "no assessment produced"),
        metric("median", median(latencies) === null ? "—" : median(latencies) + " ms", "answered requests"),
      ]),
      note(
        rows.length
          ? "First entry " + clock(first) + " · last " + clock(last) + " · stored in this browser only"
          : "No entries yet. The log records every camera and input request, and the export is the same list.",
        "muted"
      ),
      block("By category", "", [table(["Category", "Count", "Share"], countBy(ok, (r) => r.category).map(([k, n]) => [k, n, pct(n, ok.length)]))]),
      block("By source", "", [table(["Source", "Count"], countBy(rows, (r) => SOURCES[r.source] || r.source).map(([k, n]) => [k, n]))]),
      block("By model", "", [table(["Model", "Answered"], countBy(ok, (r) => r.model).map(([k, n]) => [k || "unattributed", n]))]),
      el("div", { class: "ops-row" }, [exportBtn, clearBtn]),
      note("Export is a local file download. Nothing is uploaded.", "muted")
    );
    return [e];
  }

  // -------------------------------------------------------------- analytics

  function panelAnalytics() {
    const { ok, failed, latencies } = stats();
    const flagged = ok.filter((r) => r.flagged);
    const reviewed = [...store.reviewed].length;
    const conf = { high: 0, medium: 0, low: 0, none: 0 };
    for (const r of ok) {
      if (typeof r.confidence !== "number") conf.none += 1;
      else if (r.confidence >= 0.8) conf.high += 1;
      else if (r.confidence >= 0.5) conf.medium += 1;
      else conf.low += 1;
    }
    const bands = { fast: 0, steady: 0, slow: 0, unknown: 0 };
    for (const n of latencies) {
      if (n < 200) bands.fast += 1;
      else if (n < 800) bands.steady += 1;
      else bands.slow += 1;
    }
    bands.unknown = ok.length - latencies.length;
    const summary = ok.filter((r) => r.summary && r.summary.trim()).length;

    return [
      note(
        "Counts of what this session actually recorded. Nothing is re-scored, and a flag here never means an incident.",
        "muted"
      ),
      el("div", { class: "ops-metrics" }, [
        metric("awaiting review", store.flaggedCameras().length, "flags not yet seen"),
        metric("reviewed", reviewed, "cleared by a person"),
        metric("flags raised", flagged.length, "across all sources"),
        metric("failed", failed.length, "requests with no answer"),
      ]),
      block("Review queue", "A flag is a request for a human look, never a dispatch.", [
        table(["State", "Count", "Share of answered"], [
          ["Awaiting review", store.flaggedCameras().length, pct(store.flaggedCameras().length, ok.length)],
          ["Reviewed", reviewed, pct(reviewed, ok.length)],
          ["No flag", ok.length - flagged.length, pct(ok.length - flagged.length, ok.length)],
        ]),
      ]),
      block("Reported confidence", "Bands of the number each assessment itself returned.", [
        table(["Band", "Count"], [
          ["High (≥ 0.8)", conf.high],
          ["Medium (≥ 0.5)", conf.medium],
          ["Low (< 0.5)", conf.low],
          ["Not reported", conf.none],
        ]),
      ]),
      block("Evidence", "Whether the response carried a summary at all.", [
        table(["Observed", "Count"], [
          ["Summary present", summary],
          ["No summary", ok.length - summary],
          ["Failed request", failed.length],
        ]),
      ]),
      block("Latency", "Time from request to parsed response in this session.", [
        table(["Band", "Answered"], [
          ["Under 200 ms", bands.fast],
          ["200–799 ms", bands.steady],
          ["800 ms and over", bands.slow],
          ["Not measured", bands.unknown],
        ]),
      ]),
      block("Sources", "Where the frame came from.", [
        table(["Source", "Requests"], countBy(rows, (r) => SOURCES[r.source] || r.source).map(([k, n]) => [k, n])),
      ]),
    ];
  }

  // ----------------------------------------------------------------- system

  function panelSystem() {
    const health = store.health;
    const healthText = health
      ? "ok · model " + (health.model && health.model.configured ? "configured" : "not configured") + (health.model && health.model.live_enabled ? " · live" : " · stub")
      : store.healthError || "not checked yet";
    const crew = store.crew
      ? (store.crew.patrol ? "patrol " + (store.crew.patrol.status ?? "running") : "no patrol record") +
        " · " + (store.crew.events ?? []).length + " events"
      : store.crewError || "not loaded";

    const reload = action("Reload camera list", async () => {
      await store.loadCameras();
      render();
    });
    const recheck = action("Check health", async () => {
      await store.loadHealth();
      render();
    });
    const fires = action("Load fires layer", async () => {
      await store.loadFires();
      render();
    });

    return [
      el("div", { class: "ops-kvlist" }, [
        kv("Division", division.name + " · " + division.dept),
        kv("Product id", division.product),
        kv("Backend", backendLabel()),
        kv("Endpoint", endpointLabel()),
        kv("Health", healthText, store.healthError ? "bad" : ""),
        kv("Crew", crew, store.crewError ? "bad" : ""),
        kv("Cameras online", store.cameras.length + (store.usingOffline ? " (offline copy)" : "")),
        kv("Watching", store.watch.size + " / " + MAX_WATCHED),
        kv("Flags open", store.flaggedCameras().length),
        kv("Reviewed", store.reviewed.size),
        kv("Busy now", store.busy.size + " request(s)"),
        kv("Fires layer", store.firesError ? store.firesError : store.hotspots.length + " hotspots", store.firesError ? "bad" : ""),
      ]),
      el("div", { class: "ops-row" }, [reload, recheck, fires]),
      block("Map modes", "City draws every camera; Tactical draws watched and flagged; Incident draws flagged only; AI Focus keeps the selection and the watch list.", [
        el("div", { class: "ops-row" }, [
          ...["city", "tactical", "incident", "focus"].map((mode) => {
            const b = action(mode === "focus" ? "AI Focus" : mode[0].toUpperCase() + mode.slice(1), () => store.setMapMode(mode), store.mapMode === mode ? "primary" : "");
            return b;
          }),
        ]),
      ]),
      note("The health route never returns the model key, and this panel never asks for it.", "muted"),
    ];
  }

  // ---------------------------------------------------------------- search

  const searchInput = el("input", { class: "ops-search-input", type: "search", placeholder: "Search cameras and history", "aria-label": "Search cameras and history" });
  const searchResults = el("div", { class: "ops-search-results" });
  const searchOverlay = el("div", { class: "ops-search", hidden: true }, [
    el("div", { class: "ops-search-box" }, [
      el("label", { class: "ops-search-label", text: "Search cameras and history" }),
      searchInput,
      searchResults,
      note("Enter opens the top result, Esc closes.", "muted"),
    ]),
  ]);
  searchOverlay.addEventListener("click", (ev) => {
    if (ev.target === searchOverlay) closeSearch();
  });

  const helpOverlay = el("div", { class: "ops-search", hidden: true }, [
    el("div", { class: "ops-search-box" }, [
      el("h3", { text: "Keyboard" }),
      el("ul", { class: "ops-help" }, [
        el("li", { text: "Ctrl or Cmd + K — open or close search" }),
        el("li", { text: "? — this sheet" }),
        el("li", { text: "Esc — close search, help, or operations" }),
      ]),
      note("Everything else is a visible button.", "muted"),
    ]),
  ]);
  helpOverlay.addEventListener("click", (ev) => {
    if (ev.target === helpOverlay) closeHelp();
  });
  document.body.append(searchOverlay, helpOverlay);

  function drawSearch() {
    const q = searchInput.value.trim().toLowerCase();
    if (!q) {
      searchResults.replaceChildren(note("Type a camera name, borough, category, or source.", "muted"));
      return;
    }
    const cams = store.cameras
      .filter((c) => c.name.toLowerCase().includes(q) || c.area.toLowerCase().includes(q))
      .slice(0, 6);
    const hist = rows
      .filter((r) => String(r.name).toLowerCase().includes(q) || String(r.category || "").toLowerCase().includes(q))
      .slice(0, 6);
    const out = [];
    for (const cam of cams) {
      const b = el("button", { class: "ops-search-row", type: "button" }, [
        el("span", { class: "ops-search-name", text: cam.name }),
        el("span", { class: "ops-search-meta", text: cam.area }),
      ]);
      b.addEventListener("click", () => {
        store.setSelected(cam.id);
        closeSearch();
        close();
      });
      out.push(b);
    }
    for (const r of hist) {
      const b = el("button", { class: "ops-search-row", type: "button" }, [
        el("span", { class: "ops-search-name", text: r.name }),
        el("span", { class: "ops-search-meta", text: clock(r.at) + " · " + (r.status === "failed" ? "failed" : r.category) }),
      ]);
      b.addEventListener("click", () => {
        if (store.byId.has(r.id)) store.setSelected(r.id);
        searchInput.value = r.name;
        drawSearch();
      });
      out.push(b);
    }
    searchResults.replaceChildren(...(out.length ? out : [note("No camera or entry matches that.", "muted")]));
  }

  function openSearch() {
    searchOpen = true;
    searchOverlay.hidden = false;
    searchInput.value = "";
    drawSearch();
    searchInput.focus();
  }
  function closeSearch() {
    searchOpen = false;
    searchOverlay.hidden = true;
  }
  function openHelp() {
    helpOpen = true;
    helpOverlay.hidden = false;
  }
  function closeHelp() {
    helpOpen = false;
    helpOverlay.hidden = true;
  }

  searchInput.addEventListener("input", drawSearch);
  searchInput.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      const first = searchResults.querySelector("button");
      if (first) first.click();
    }
  });

  document.addEventListener("keydown", (ev) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "");
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
      ev.preventDefault();
      if (searchOpen) closeSearch();
      else openSearch();
      return;
    }
    if (ev.key === "Escape") {
      if (searchOpen) closeSearch();
      else if (helpOpen) closeHelp();
      else if (!root.hidden) close();
      return;
    }
    if (!typing && ev.key === "?") {
      ev.preventDefault();
      openHelp();
    }
  });

  // ----------------------------------------------------------------- render

  function render() {
    const panels = {
      wall: panelWall,
      inputs: panelInputs,
      history: panelHistory,
      log: panelLog,
      analytics: panelAnalytics,
      system: panelSystem,
    };
    if (root.hidden) return;
    body.replaceChildren(...panels[tab]());
    sourceLine.textContent = store.source.note || "";
    sourceLine.className =
      "ops-source " + (store.source.kind === "live" ? "live" : store.source.kind === "offline" ? "warn" : "bad");
  }

  store.subscribe(() => {
    syncFromStore();
    if (!root.hidden) render();
  });

  // Seed the seen set from what is already in the store (a page that imports
  // ops after its first render should not log the same result twice).
  for (const [id, r] of store.results) seen.add(id + "@" + (r.at ?? 0));

  return {
    root,
    open,
    close,
    toggle,
    isOpen: () => !root.hidden,
    render,
    refresh: render,
    add: addRow,
  };
}
