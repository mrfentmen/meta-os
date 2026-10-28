# MetaTrio — native macOS app (Vigiles · Ignis · Sanitas)

One native SwiftUI macOS application hosting all three products behind a
product switcher, on the shared foundation defined in
`~/workspace/hackathon/meta-sentinel/MASTER_DIRECTIVE_V2.md`:

- **Meta Vigiles** — NYPD-oriented visual incident awareness (live camera).
- **Meta Ignis** — FDNY-oriented fire/smoke hazard awareness (camera aimed at
  prerecorded footage or safe demonstrations — never a real fire).
- **Meta Sanitas** — Department of Sanitation-oriented sanitation observation.

This is a demo-grade prototype: no App Store, no notarization, ad-hoc
signing only. It compiles and runs on a Mac with Xcode; we iterate by
rebuilding.

> **Sandbox note:** this source tree was written in a Linux sandbox with no
> Xcode, no SwiftUI SDK, and no Swift toolchain at all, so it has **not been
> compiled or even parse-checked**. First build verification happens on the
> Mac, following the steps below. The Swift is written to be compilable by
> careful inspection only (see "What is verified" at the bottom).

## What the app does

- Product switcher (Vigiles / Ignis / Sanitas) with per-product identity,
  categories, evaluation scenarios, input guidance, and a limitations
  notice that is always on screen.
- Live camera preview via AVFoundation, with honest states: permission
  denied, no camera, camera error — shown as themselves, never papered over.
- Still-image input (web parity): an image-only file picker for
  prerecorded or photographed scenes — the input the Ignis and Sanitas
  demos use when a live camera is not the source. The chosen image is
  previewed in memory, sent once through the same submit path as a live
  frame (same endpoint, same v2 validation, same timeline entry, same
  session-log entry) under the product selected at assess time, and
  cleared by Clear or Reset Session. It needs no camera and is never
  written to disk by the app. Until the backend exists, a still-image
  request fails exactly like a live frame — honest error, no assessment.
- Prerecorded-video input (web parity): a video-only file picker for a
  recorded clip — the input used when neither a live camera nor a still
  image is the source. The clip plays in the app from its own location
  (never copied or stored by the app); "Assess this frame" extracts only
  the frame at the paused playback position and sends that one JPEG
  through the same submit path as a live frame. A frame-extraction
  failure is logged and shown as a failure, never replaced with a
  neighbouring frame. Until the backend exists, a video-frame request
  fails exactly like a live frame — honest error, no assessment.
- Frame sampler: one frame every N seconds (default 3, adjustable 1–60),
  with the sampled-not-continuous disclosure on screen. A tick that fires
  while a request is still in flight is skipped and counted — sampling can
  never outrun the endpoint.
- Each sample POSTs `{product, timestamp, image}` (image is a JPEG data
  URL) to the assessment endpoint and strictly validates the reply against
  the unified v2 contract before displaying anything:
  `product` (must match the request), `timestamp` (ISO-8601),
  `observations[{category, description, evidence, confidence}]`,
  `assessment{category, summary, uncertainty[], requires_human_review}`,
  `processing{model, latency_ms}`.
- Latest-assessment view with observations, evidence, and a plainly labeled
  Uncertainty section; an event timeline (failures included, in red);
  a session log with per-entry client-measured latency and JSON export in
  the same shape the web frontend produces, for the evaluation lane.
- Backend health check (web parity): a "Check Backend Health" button in
  Settings that GETs the server's /api/health for the configured
  endpoint (the /api/assess suffix is swapped for /api/health, so the
  check always points at the server the user configured). It reports
  the service name, the products list, and the model state — live calls
  on, or key configured / not configured with live calls held — and
  says plainly that reachable does not mean an assessment is available.
  The check never sends a frame and never returns an assessment, and it
  never changes the assessment status in the status bar.
- Empty states that say what is actually happening: the assessment area
  shows a waiting state while a request is in flight, the real backend
  error when the backend failed, and "No assessment received yet" only
  when nothing has been attempted; the timeline says analysis is running
  instead of looking empty. The assessment header shows the product's
  display name (Meta Vigiles / Ignis / Sanitas), not the raw contract key.
- VoiceOver labels matching the web frontend (web parity): the product
  picker, camera preview (with a plain-words camera state), still-image
  and video panels, settings fields, assessment header and observations,
  and timeline rows are labeled for VoiceOver, section headings carry
  the header trait, and decorative color dots are hidden from VoiceOver
  because the status is already stated in words next to them. No
  assessment information lives only in color or in an icon.
- Scenario picker matching the web frontend (web parity): a dropdown of
  the current product's evaluation scenarios, written into each session
  log entry as ground-truth context for the evaluation lane. A custom
  scenario label typed in the field below overrides the picked scenario,
  exactly like the web frontend. Switching products resets the picker
  (the custom field is left alone, also like the web frontend), so one
  product's scenario can never label another product's entries. The
  picker and the custom field both carry VoiceOver labels.

### Honesty rules (enforced in code, not just promised)

- **Zero hardcoded or fake detections.** With no backend, the app shows
  "Model backend not connected" plus the real error. That is the correct
  state until Agent 2's server exists.
- `confidence` stays `null` unless the server returns a real number;
  the UI prints "confidence: not reported".
- `processing.latency_ms` stays `null` unless the server reports it.
  The latency the app displays itself ("Last round trip") is measured
  client-side with a clock around the actual request — including failures.
- Contract violations (wrong product, bad timestamp, a boolean where a
  number belongs, confidence outside 0…1, missing `latency_ms` key, …)
  reject the whole response with the specific problems listed.

## Layout

```
Package.swift                     SwiftPM manifest (macOS 13+, executable target)
Scripts/make-app.sh               Builds + ad-hoc signs MetaTrio.app
MetaTrio.entitlements             Optional; only if you enable App Sandbox
Sources/MetaTrio/
  MetaTrioApp.swift               @main entry
  Models/
    Assessment.swift              V2 contract types (Codable)
    ProductConfig.swift           ProductID + per-product config as data
    SessionLog.swift              In-memory log + JSON export
  Services/
    ISO8601.swift                 Timestamp formatting/validation
    ContractValidator.swift       Strict v2 validation of server replies
    AssessClient.swift            POST /api/assess, measured latency, typed errors
    CameraService.swift           AVFoundation session, permission, frame grab
    FrameSampler.swift            Non-overlapping sampling timer + counters
    VideoFrameService.swift       One-frame JPEG extraction from a
                                  prerecorded video at a playback position
  ViewModels/
    AppModel.swift                Camera -> sampler -> client -> UI wiring,
                                  plus still-image and prerecorded-video
                                  input sharing the same submit path as
                                  live frames
  Views/
    ContentView.swift             Window layout, header, camera panel, settings, status bar
    CameraPreviewView.swift       AVCaptureVideoPreviewLayer host
    AssessmentView.swift          One validated assessment, uncertainty shown plainly
    TimelineView.swift            Session event timeline
```

## Build and run on the Mac

Requires: a Mac running macOS 13 or later, Xcode 15 or later installed.

### Path A — bundled app (recommended; required for reliable camera)

macOS grants camera permission to a bundled app with a camera usage
description in its Info.plist. A bare SwiftPM executable has no bundle, so
use the script — it builds, assembles `MetaTrio.app`, and ad-hoc signs it:

```bash
cd native
./Scripts/make-app.sh
open MetaTrio.app
```

- First launch: if Gatekeeper objects, right-click `MetaTrio.app` → Open.
- First camera start: macOS shows the permission prompt ("MetaTrio would
  like to access the camera") — allow it. If it was denied, re-enable under
  **System Settings → Privacy & Security → Camera**.
- Known ad-hoc quirk: the ad-hoc signature changes on every rebuild, so
  macOS may treat a rebuilt app as new and ask for camera permission again,
  or show it as off in Privacy & Security. Toggle it back on there if the
  app reports "permission denied" after a rebuild.

### Path B — Xcode loop (fast for UI/logic iteration)

1. Open `native/Package.swift` in Xcode (File → Open, select the
   `native` folder). Xcode resolves the package and shows the `MetaTrio`
   scheme.
2. Signing: a SwiftPM executable has no app target, so there is nothing to
   sign for local runs — just press **Run (⌘R)**. (If you later wrap this in
   an app project: Signing & Capabilities → check "Automatically manage
   signing" and pick your personal team; add the Camera capability or use
   the provided `MetaTrio.entitlements` if you enable App Sandbox.)
3. Caveat: when run unbundled from Xcode, the camera permission prompt is
   attributed to the hosting process and may not appear or may be denied
   outright. If the camera will not start under Xcode, switch to Path A —
   the bundled app is the supported route for camera work.

### Rebuild loop

Edit the Swift sources → re-run `./Scripts/make-app.sh` (debug builds take
seconds) → quit and re-open `MetaTrio.app`. Nothing else changes: settings
live in the window, the endpoint is editable at runtime.

## The endpoint

- The endpoint URL is editable in the app's Settings panel.
  Default: `http://localhost:8080/api/assess`.
- The server is Agent 2's lane and is **not** part of this folder. It holds
  the Meta API key server-side; the key never enters this app.
- Request: `POST {"product": "vigiles|ignis|sanitas", "timestamp":
  "<ISO-8601>", "image": "data:image/jpeg;base64,..."}`
- Response: the v2 assessment JSON above, or `{"error": "..."}`.
- Health: `GET` the same base with `/api/assess` swapped for
  `/api/health` returns `{ok, service, products, model: {configured,
  live_enabled}}` and never exposes the key. The Settings panel's
  "Check Backend Health" button reads exactly this route.
- Until that server runs, expect — and demo honestly — the
  "backend not connected" state with the real connection error in the
  timeline and the session log.

## What is verified vs unverified

Verified in the sandbox (no Mac available there):

- Source tree is complete and internally consistent, by inspection: every
  referenced type and file exists; behavior mirrors the tested web frontend
  (sampler non-overlap, error taxonomy `network/http/invalid`, session-log
  export shape, sampling disclosure wording).
- No syntax check of any kind was run: the sandbox has no `swift` or
  `swiftc` binary (`which swift swiftc` returns nothing). Zero compiler
  evidence exists for this code. That includes the scenario picker
  added in the latest Agent 1 change: it uses only long-standing
  SwiftUI Picker/tag bindings and the existing AppModel log path, and
  was checked by careful inspection, not by a build or by running it
  on a Mac.

Not verified anywhere yet:

- Compilation. SwiftUI/AVFoundation/AppKit files cannot be compiled in the
  Linux sandbox. First build happens on the Mac via the steps above; treat
  any first-build errors as the expected first iteration, not a surprise.
- Camera behavior on real hardware (permission prompt, preview, frame
  capture) — only exercisable on the Mac. The exact checklist is
  `../docs/HARDWARE_VERIFICATION.md`.
- Any live round trip — the local `/api/assess` server now exists
  (Agent 2's lane) and its held-state round trip is documented in
  `../server/README.md` (503 held message, web + native error paths),
  but no live Spark call has ever been completed by this team, and the
  native app itself has never run against that server on a Mac.
