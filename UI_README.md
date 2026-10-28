# Meta Sentinel — Frontend

Camera interface and analysis client for the Meta Sentinel visual
event-assessment prototype (Meta Global AI Developer Hackathon 2026, Indie —
Push the Frontier). This is the Agent 1 deliverable from `BRIEF.md`: a real,
working frontend wired to the actual analysis pipeline contract. It contains
no detection logic and no sample results.

Dependency-free static web app: plain HTML/CSS/JS, ES modules, no build
step, no npm packages. (`package.json` exists only to mark the project as
ES modules for the node test runner; it declares zero dependencies.)

## What is built

- **Camera** (`js/camera.js`, wired in `js/app.js`): `getUserMedia`
  start/stop/reset, a visible CAMERA LIVE indicator while the stream is
  active, and honest states for permission denied, no camera found, camera
  busy, and unsupported browser/context.
- **Frame sampler** (`js/sampler.js`): while analysis is running, one frame
  every N seconds (default 3, configurable 1–60 in the UI) is drawn to a
  canvas and encoded as JPEG. If the previous request has not returned, the
  tick is skipped and counted — at most one request is ever in flight.
- **Analysis client** (`js/client.js`): POSTs each frame to the assessment
  endpoint and validates every response against the contract schema
  (`js/schema.js`). Malformed responses are reported as errors, never
  rendered as detections.
- **Honest disconnected state**: if the endpoint is unreachable, returns an
  HTTP error, or returns an invalid body, the UI shows "Model backend not
  connected" with the real error, records the failure in the history and the
  session log, and displays no assessment. The UI never invents a result.
- **Event display**: latest validated assessment (event type, timestamp,
  observations with evidence and confidence, assessment text, uncertainty,
  human-review flag), an event history timeline (failures included, styled
  distinctly), a loading indicator while a request is outstanding, and live
  sampler counters (ticks / sent / skipped / failed).
- **Evaluation session log** (`js/log.js`): every request is recorded in
  memory with its request timestamp, measured latency, outcome status, and
  the full validated response or the real error. An optional scenario-label
  field is written into each entry as ground-truth context for evaluation.
  **Export log (JSON)** downloads the log for the Agent 3 evaluation lane.

## Sampling disclosure

Analysis uses **sampled frames, not continuous video**. The UI states the
configured interval on screen at all times: one frame every N seconds is
sent to the endpoint, and events between samples are not seen by the
system. Frames are encoded in memory, sent only to the configured endpoint,
and are not stored by this app. The session log is in-memory only and is
lost on page reload unless exported.

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

Coverage: schema validation accepts a valid assessment and rejects 16
malformed shapes; the sampler skips ticks while a request is in flight,
resumes after it settles, surfaces errors without wedging, and stops
cleanly; the client maps network/HTTP/invalid failures to typed errors;
the session log export matches the documented shape. Current result:
**30 tests, 30 pass, 0 fail** (Node v24).

Note: `node --test tests/` (directory form) fails in this sandbox's Node
build; use the file form above.

## The /api/assess contract

Default endpoint: same-origin `/api/assess` (configurable in the UI).

Request — one per sampled frame:

```json
{
  "timestamp": "2026-10-28T10:15:00.000Z",
  "image": "data:image/jpeg;base64,..."
}
```

- `timestamp`: ISO-8601, the moment the frame was sampled.
- `image`: the sampled frame as a JPEG data URL.

Response — the assessment schema from the brief (Agent 2 owns the backend
implementation):

```json
{
  "timestamp": "ISO-8601 timestamp",
  "observations": [
    { "action": "observable action", "evidence": "visual evidence", "confidence": 0.0 }
  ],
  "event_type": "event category or unknown",
  "assessment": "brief explanation",
  "uncertainty": "what cannot be determined from the evidence",
  "requires_human_review": true
}
```

Validation rules enforced client-side: all fields required with the types
shown; each `confidence` must be a number in 0..1; `timestamp` must parse
as a date; `event_type` must be non-empty. Extra fields are tolerated.
Confidence is the model's self-report, not measured accuracy.

Session log export shape (consumed by the evaluation lane):

```json
{
  "app": "meta-sentinel-frontend",
  "exported_at": "ISO-8601",
  "endpoint": "/api/assess",
  "sampling_interval_seconds": 3,
  "entry_count": 0,
  "entries": [
    {
      "seq": 1,
      "recorded_at": "ISO-8601",
      "request_timestamp": "ISO-8601",
      "latency_ms": 0,
      "status": "ok | network_error | http_error | invalid_response",
      "scenario_label": null,
      "response": { "...assessment or null..." },
      "error": null
    }
  ]
}
```

## What is NOT connected yet

- **No model backend exists.** Nothing implements `/api/assess` yet; that
  is Agent 2's lane (Meta model integration). Until it lands, every
  analysis request fails and the UI's disconnected state is what you will
  see. That is the intended, honest behavior — not a bug.
- No evaluation harness consumes the exported log yet (Agent 3's lane).
- Camera behavior is verified only up to page load and module execution in
  headless Chromium: this sandbox has no camera device, so a live
  `getUserMedia` capture, real frame encoding from a device, and phone
  viewport behavior still need a pass on real hardware.

## Scope and safety

Experimental prototype for staged, consenting scenarios only. Assessments
describe observable evidence and uncertainty; they do not establish intent,
guilt, or that a crime occurred. The app never contacts police or
emergency services, and performs no face recognition or identity
inference.
