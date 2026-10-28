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
  the UI accent (blue / orange / green).
- **Camera** (`js/camera.js`, wired in `js/app.js`): `getUserMedia`
  start/stop/reset, a visible CAMERA LIVE indicator while the stream is
  active, and honest states for permission denied, no camera found, camera
  busy, and unsupported browser/context.
- **Frame sampler** (`js/sampler.js`): while analysis is running, one frame
  every N seconds (default 3, configurable 1–60 in the UI) is drawn to a
  canvas and encoded as JPEG. If the previous request has not returned, the
  tick is skipped and counted — at most one request is ever in flight.
- **Analysis client** (`js/client.js`): POSTs each frame with its product
  to the assessment endpoint and validates every response against the v2
  contract schema (`js/schema.js`), with the same strictness as the native
  validator. Malformed responses are reported as errors, never rendered as
  detections.
- **Honest disconnected state**: if the endpoint is unreachable, returns an
  HTTP error, returns a server `{"error": ...}` body, or returns an invalid
  body, the UI shows "Model backend not connected" with the real error,
  records the failure in the history and the session log, and displays no
  assessment. The UI never invents a result.
- **Still-image input** (`js/image_input.js`, wired in `js/app.js`): a
  file picker for prerecorded or photographed scenes — the input the
  Ignis and Sanitas demos use when a live camera is not the source.
  Choosing an image shows an in-memory preview; "Assess this image"
  sends it once to the same endpoint, under the product selected at that
  moment, through the same client, validation, history entry, and
  session-log entry as a live frame. It needs no camera, accepts
  `image/*` files only, and stores nothing: the preview and the data URL
  live in memory and are cleared by Reset. Until the backend exists, a
  still-image request fails exactly like a live frame — honest error,
  no assessment.
- **Event display**: latest validated assessment (product, assessment
  category, timestamp, observations with category, description, evidence,
  and confidence or "not reported", uncertainty list, human-review flag,
  and server model/latency or "not reported"), an event history timeline
  (failures included, styled distinctly), a loading indicator while a
  request is outstanding, and live sampler counters (ticks / sent /
  skipped / failed).
- **Accessibility announcements**: the backend-status line and the
  latest-assessment panel are polite live regions, so a new assessment
  or a backend failure is announced to screen readers without stealing
  focus; the event history is deliberately not a live region, so it does
  not double-announce the same result. The product switcher's radios are
  visually hidden inputs, so keyboard focus shows as a visible outline on
  the option label itself.
- **Evaluation session log** (`js/log.js`): every request is recorded in
  memory with its request timestamp, product, measured latency, outcome
  status, and the full validated response or the real error. A scenario
  dropdown offers the current product's evaluation scenarios, and a custom
  label field overrides it; the chosen label is written into each entry as
  ground-truth context for evaluation. Switching products resets the
  dropdown choice so one product's scenario can never label another
  product's entries. **Export log (JSON)** downloads the log for the
  Agent 3 evaluation lane.

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
and resolve/reject with the file-reader result. Current result:
**71 tests, 71 pass, 0 fail** (Node v24).

Note: `node --test tests/` (directory form) fails in this sandbox's Node
build; use the file form above.

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

- **No model backend exists.** Nothing implements `/api/assess` yet; that
  is Agent 2's lane (Meta model integration). Until it lands, every
  analysis request fails and the UI's disconnected state is what you will
  see. That is the intended, honest behavior — not a bug.
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
