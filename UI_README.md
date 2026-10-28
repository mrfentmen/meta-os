# Meta Trio — Frontend

Camera interface and analysis client for the Meta Trio visual
event-assessment prototype (Meta Global AI Developer Hackathon 2026, Indie —
Push the Frontier): Meta Vigiles (incident awareness), Meta Ignis (fire and
smoke), and Meta Sanitas (sanitation), sharing one frontend. This is the
Agent 1 deliverable from `BRIEF.md` and `MASTER_DIRECTIVE_V2.md`: a real,
working frontend wired to the actual v2 analysis pipeline contract. It
contains no detection logic and no sample results.

Dependency-free static web app: plain HTML/CSS/JS, ES modules, no build
step, no npm packages. (`package.json` exists only to mark the project as
ES modules for the node test runner; it declares zero dependencies.)

## What is built

- **Product switcher** (`js/products.js`, wired in `js/app.js`): Vigiles /
  Ignis / Sanitas, mirroring the native app's `ProductConfig` — per-product
  display name, department, tagline, reportable categories, evaluation
  scenarios, input guidance, and a limitations notice that stays on screen.
  Switching products applies to the next sampled frame; earlier log entries
  keep the product they were assessed under. The active product also tints
  the UI accent (blue / orange / green). On both frontends, a switch made
  while a request is in flight cannot relabel that request: the product
  is captured when the sample starts or the Assess button is tapped, and
  that product labels the request's log and history/timeline entries.
- **Camera** (`js/camera.js`, wired in `js/app.js`): `getUserMedia`
  start/stop/reset, a visible CAMERA LIVE indicator while the stream is
  active, and honest states for permission denied, no camera found, camera
  busy, and unsupported browser/context. While the browser permission
  prompt is up, Start says "Waiting for camera permission…" and stays
  disabled until the prompt resolves, matching the native camera's
  requesting-permission state, instead of still saying "Camera is off." A facing selector offers the
  front camera and the rear camera — the one a phone demo points at the
  scene — as a preference, never an exact requirement, so a device with
  only one camera still gets that camera. Changing it while the camera
  is off applies to the next Start; changing it while live restarts the
  stream, and a failed restart leaves the camera off with the real error.
  While analysis is running, the Camera panel also shows "Analysis active
  — sampling one frame every N seconds", matching the native panel's
  ANALYSIS ACTIVE banner; it is hidden while idle and rewords itself
  when the interval changes.
  The native Mac app has a facing picker matching the web one: front
  vs rear, as a preference never a requirement — a rear pick on a
  single-camera Mac still opens the front camera instead of failing.
  Changing it while the camera is off applies to the next Start;
  changing it while live restarts the capture, and a failed restart
  shows the real error instead of silently keeping the old camera.
- **Frame sampler** (`js/sampler.js`): while analysis is running, one frame
  every N seconds (default 3, configurable 1–60 in the UI) is drawn to a
  canvas and encoded as JPEG. If the previous request has not returned, the
  tick is skipped and counted — at most one request is ever in flight.
  If capturing the frame itself fails, the tick is counted as failed and
  logged with a null latency, and — like a video-frame capture failure —
  it lands in the event history as an "Analysis request failed" entry and
  sets the backend status to the capture failure itself on both
  frontends; no request was made, so the last round trip is untouched,
  no assessment is invented, and the sampler keeps ticking.
- **Analysis client** (`js/client.js`): POSTs each frame with its product
  to the assessment endpoint and validates every response against the v2
  contract schema (`js/schema.js`), with the same strictness as the native
  validator. Malformed responses are reported as errors, never rendered as
  detections. Like the native clients, it rejects an endpoint that is not
  a valid http(s) URL before anything is sent (a relative endpoint such
  as `/api/assess` still goes to fetch as before); that no-request
  failure is logged with a null latency and leaves the last round trip
  alone, instead of stamping the time-to-reject as a round trip.
- **Honest disconnected state**: if the endpoint is unreachable, returns an
  HTTP error, returns a server `{"error": ...}` body, or returns an invalid
  body, the UI shows "Model backend not connected" with the real error,
  records the failure in the history and the session log, and displays no
  assessment. The UI never invents a result.
- **Prerecorded-video input** (`js/video_input.js`, wired in `js/app.js`): a
  file picker for a recorded clip — the input used when neither a live
  camera nor a still image is the source. The clip plays in the page;
  "Assess this frame" captures only the frame showing at that moment
  (paused where the user wants it) and sends that one JPEG through the
  same client, validation, history entry, and session-log entry as a
  live frame. The whole video is never sent; the object URL lives in
  memory and is revoked by Reset or when another file is chosen. The
  assess button stays disabled until the video's metadata has loaded,
  so a frame can never be requested from a frameless video, and a
  capture failure is logged honestly with no assessment invented — and,
  matching the native app, it also lands in the event history as an
  "Analysis request failed" entry and sets the backend status to the
  capture failure itself (no request was made, so it is not a backend
  message and the last round trip is untouched). A
  Clear button clears just this input (file choice, preview, Assess
  disabled) without stopping the camera or analysis, matching the
  native panel's Clear button; Reset still clears both inputs together
  with the rest of the view. While the frame is being sent, the panel
  shows "Sending video frame…", matching the native video panel, so
  the wait is visible where the button was tapped.
- **Still-image input** (`js/image_input.js`, wired in `js/app.js`): a
  file picker for prerecorded or photographed scenes — the input the
  Ignis and Sanitas demos use when a live camera is not the source.
  Choosing an image shows an in-memory preview; "Assess this image"
  sends it once to the same endpoint, under the product selected at that
  moment, through the same client, validation, history entry, and
  session-log entry as a live frame. It needs no camera, accepts
  `image/*` files only, and stores nothing: the preview and the data URL
  live in memory and are cleared by the panel's Clear button or by Reset
  (Clear touches only this input — it never stops the camera or
  analysis — matching the native panel's Clear button). While the image
  is being sent, the panel shows "Sending still image…", matching the
  native still-image panel, so the wait is visible where the button was
  tapped. Until the backend exists, a
  still-image request fails exactly like a live frame — honest error,
  no assessment.
- **Event display**: latest validated assessment (product, assessment
  category, timestamp, observations with category, description, evidence,
  and confidence or "not reported", uncertainty list, human-review flag,
  and server model/latency or "not reported"; while a request is
  outstanding and no assessment has been shown yet, the panel reads
  "Waiting for the first assessment…", matching the native app's
  Latest panel, and a failed first request shows the real backend
  error in the panel, matching the native panel — "No assessment
  received yet." is only for when nothing has been attempted), an event history timeline
  (failures included, styled distinctly; every assessment entry carries
  a "Show assessment" button that displays that past assessment again in
  the Latest assessment panel, labelled as a past result — the web match
  for the native timeline's selectable rows; while the history is still
  empty and analysis is running, its note reads "Analysis is running —
  assessments and errors will appear here as they arrive.", matching
  the native timeline's empty state, and while idle it reads "No events
  yet. Assessments and errors will appear here.", matching the native
  timeline's idle empty state, instead of just "No events yet."), a loading indicator while a
  request is outstanding, and live sampler counters (ticks / sent /
  skipped / failed). The Camera panel also shows the last round trip —
  the client-measured time for the last completed assessment request,
  success or failure, matching the native app's status bar. It is never
  the server-reported `processing.latency_ms` inside a response; it stays
  hidden until the first request completes, Reset clears it, a
  frame-capture failure leaves the previous value alone (no request was
  made), and the backend health check never touches it (it sends no
  frame).
- **Accessibility announcements**: the backend-status line and the
  latest-assessment panel are polite live regions, so a new assessment
  or a backend failure is announced to screen readers without stealing
  focus; the event history is deliberately not a live region, so it does
  not double-announce the same result. The product switcher's radios are
  visually hidden inputs, so keyboard focus shows as a visible outline on
  the option label itself.
- **Evaluation session log** (`js/log.js`): every request is recorded
  with its request timestamp, product, measured latency, outcome
  status, and the full validated response or the real error. A scenario
  dropdown offers the current product's evaluation scenarios, and a custom
  label field overrides it; the chosen label is written into each entry as
  ground-truth context for evaluation. Switching products resets the
  dropdown choice so one product's scenario can never label another
  product's entries. On load, the saved history and the latest
  assessment are restored on screen. **Export log (JSON)** downloads the log
  for the Agent 3 evaluation lane.

## Sampling disclosure

Analysis uses **sampled frames, not continuous video**. The UI states the
configured interval on screen at all times: one frame every N seconds is
sent to the endpoint, and events between samples are not seen by the
system. Frames are encoded in memory, sent only to the configured endpoint,
and are not stored by this app. The session log is kept in the browser's local storage, so it survives
page reloads until exported or cleared; it holds assessments and errors
only, never frames.

## Run it

Any static file server works:

```sh
cd meta-sentinel
python3 -m http.server 8000
# open http://localhost:8000
```

Camera access requires a secure context: `localhost` qualifies, as does
HTTPS. Serving the folder as-is is also how it can later be deployed to a
static host such as Cloudflare Pages.

## Tests

Node's built-in test runner, no dependencies:

```sh
npm test
# or directly:
node --test tests/ui.test.mjs
```

Coverage: trio product configs (ids, identity, categories, scenarios,
limitations, per-product scenario sets); v2 schema validation accepts a
valid assessment for each product and rejects 43 malformed shapes (wrong
product, non-ISO or impossible timestamps, missing/null-rule violations
for confidence and latency, wrong types including JSON booleans as
numbers); the sampler skips ticks while a request is in flight, resumes
after it settles, surfaces errors without wedging, and stops cleanly; the
client sends the product with every request and maps network/HTTP/invalid
(including wrong-product and server error-body) failures to typed errors;
the session log export matches the documented shape with per-entry and
top-level product; the still-image helpers accept `image/*` files only
and resolve/reject with the file-reader result; the history re-inspection
wiring (page note, Show assessment button, live and restored entries
carrying their assessment). Current result:
**100 tests, 100 pass, 0 fail** (Node v24).

Web↔native product-config parity (`tests/product-parity.test.mjs`): the
test reads the native app's `ProductConfig.swift` and asserts the web
`products.js` matches it exactly for every product — display name,
department, tagline, categories, scenarios, limitations, input guidance —
plus the accent mapping (native color name to web hex). The two
frontends cannot drift apart in how they describe a product without this
test failing. Current result: **5 tests, 5 pass, 0 fail**.

Live client↔server check (`tests/client-server.test.mjs`): the real web
client against the real server over HTTP, no fetch doubles, no model —
the server runs with an empty environment, so the health check reports
the model held (not configured, live calls off) and a valid assess
request surfaces the real 503 Spark-hold message as a typed HTTP error,
with no assessment rendered; a bad product surfaces the real 400; and
the server serves the actual frontend entry point. Full `npm test`
(including Agent 2 and Agent 3 suites): **202 tests, 202 pass, 0 fail**.

Note: `node --test tests/` (directory form) fails in this sandbox's Node
build; use the file form above.

Render check (headless, 2026-10-28): the page was served over local HTTP
and rendered in headless Chromium at 1280 px and at 390 px widths.
Desktop shows the two-column layout with the Vigiles badge, the product
switcher, categories, input guidance, and the limitations notice on
screen; the phone width shows a single column with the product switcher
stacked and no sideways overflow. The rendered DOM carries the Vigiles
scenario options in the scenario dropdown, which only the page's JS
builds (the shipped HTML leaves that select empty), so the modules
executed, not just the static markup. This covers layout and script
execution only: a live camera capture, a real phone browser, and a real
frame round trip still need the real-hardware pass in
`docs/HARDWARE_VERIFICATION.md`.

## The /api/assess contract (v2, shared with the native app)

Default endpoint: same-origin `/api/assess` (configurable in the UI).
This is the unified v2 contract from `MASTER_DIRECTIVE_V2.md` section 9,
frozen in `FIRST_RESPONSE.md`; the native app's `ContractValidator` is the
reference implementation and this frontend matches it.

Request — one per sampled frame:

```json
{
  "product": "vigiles | ignis | sanitas",
  "timestamp": "2026-10-28T10:15:00.000Z",
  "image": "data:image/jpeg;base64,..."
}
```

- `product`: the product selected in the UI; the server applies the
  matching prompt profile.
- `timestamp`: ISO-8601, the moment the frame was sampled.
- `image`: the sampled frame as a JPEG data URL.

Response — the v2 assessment shape (Agent 2 owns the backend
implementation). The server returns exactly this shape or an
`{"error": "..."}` object, which the client reports as a failure:

```json
{
  "product": "vigiles",
  "timestamp": "ISO-8601 timestamp",
  "observations": [
    {
      "category": "observable category",
      "description": "what was observed",
      "evidence": "visual evidence",
      "confidence": 0.72
    }
  ],
  "assessment": {
    "category": "assessment category",
    "summary": "brief explanation",
    "uncertainty": ["what cannot be determined from the evidence"],
    "requires_human_review": true
  },
  "processing": { "model": "model identifier", "latency_ms": 812 }
}
```

Validation rules enforced client-side, same strictness as the native
validator: `product` must be present and must match the product that was
requested; `timestamp` must be ISO-8601 with a `T` separator, a timezone,
and a real calendar date; every observation needs a non-empty `category`
and `description`, a string `evidence`, and a `confidence` key that is
either null (unreported, never defaulted) or a number in 0..1;
`assessment.category` must be non-empty, `summary` a string,
`uncertainty` an array of strings, `requires_human_review` a boolean;
`processing.model` must be non-empty and `latency_ms` must be present,
either null or a non-negative number. Booleans are never accepted as
numbers, and a missing `confidence` or `latency_ms` key is rejected even
though null is accepted. Extra fields are tolerated. Confidence is the
model's self-report, not measured accuracy.

Session log export shape (consumed by the evaluation lane):

```json
{
  "app": "meta-sentinel-frontend",
  "exported_at": "ISO-8601",
  "product": "vigiles | ignis | sanitas (active at export time)",
  "endpoint": "/api/assess",
  "sampling_interval_seconds": 3,
  "entry_count": 0,
  "entries": [
    {
      "seq": 1,
      "recorded_at": "ISO-8601",
      "request_timestamp": "ISO-8601",
      "product": "vigiles",
      "latency_ms": 0,
      "status": "ok | network_error | http_error | invalid_response",
      "scenario_label": null,
      "response": { "...assessment or null..." },
      "error": null
    }
  ]
}
```

`latency_ms` in an entry is the client-measured round trip; it is null
when no request was made (frame capture failed first), never a fake 0.
The server-reported `processing.latency_ms` lives inside `response` and is
never mixed with the client measurement.

## What is NOT connected yet

- **No live model assessment yet.** Agent 2's `/api/assess` server exists
  (`server/server.mjs`), but live model calls are held per Del's ruling
  (Spark stays off until the build is complete and Del green-lights the
  test phase). Verified 2026-10-28: the server answers `/api/health`
  with `live_enabled: false`, and a valid assess request returns HTTP
  503 with the real held message ("Live model calls are held: Spark
  stays off until the build is complete and Del green-lights the test
  phase."). Until live calls are enabled, every analysis request ends
  in that honest held error and no assessment renders. That is the
  intended behavior — not a bug. The full live round trip (a real frame
  returning a valid v2 assessment) is still unproven.
- No evaluation harness consumes the exported log yet (Agent 3's lane).
- Camera behavior is verified only up to page load and module execution in
  headless Chromium: this sandbox has no camera device, so a live
  `getUserMedia` capture, real frame encoding from a device, and phone
  viewport behavior still need a pass on real hardware. The exact
  checklist for that pass is `docs/HARDWARE_VERIFICATION.md`.

## Scope and safety

Experimental prototype for staged, consenting scenarios only. Assessments
describe observable evidence and uncertainty; each product's limitations
notice, shown in the UI at all times, states what its assessments never
claim (Vigiles: no crime, guilt, or intent findings; Ignis: not a
certified fire-detection system and never a reason to create a real fire;
Sanitas: no violation, ownership, or responsibility findings). The app
never contacts police or emergency services, never dispatches or cites
automatically, and performs no face recognition or identity inference.
