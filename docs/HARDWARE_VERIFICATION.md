# Real-hardware verification notes (Agent 1)

What still needs a pass on real hardware, and exactly how to run it.
Nothing here is verified yet — this checklist is the plan, not a result.
The sandbox has no camera, no Mac, and no phone, so every item below
is unproven until someone runs it on a real device and records the
outcome.

## Ground rules for every check

- Record: device, OS and browser (or app build), date, and what you saw.
  A screenshot or short screen recording beats a written "it worked".
- A check PASSES only when the UI shows what is really happening:
  live video when the camera runs, the honest error when it does not,
  and never a made-up assessment.
- If the backend is not running, the correct result is
  "Model backend not connected" with the real error in the timeline and
  the session log. That is a pass for the frontend, not a failure.
- Never point a camera at a real fire, a real emergency, or anyone
  without their consent. Use staged, consenting scenes only.

## 1. Web frontend on a phone (iPhone Safari first)

Setup: serve the repo root over HTTPS (or `localhost` on the phone via
USB), because browsers block camera access on plain HTTP pages served
over a network. Open `index.html`.

1. Page load: product switcher shows Vigiles / Ignis / Medicus, the
   Vigiles limitations notice is visible, and the layout fits a narrow
   screen (single column below the 720 px breakpoint, no sideways
   scrolling, buttons reachable with a thumb).
2. Camera start: tap Start camera. Safari asks for camera permission.
   Allow it: the video preview appears and the CAMERA LIVE indicator
   shows. Deny it once, reload, and confirm the UI shows the
   permission-denied state in plain words — not a blank panel.
3. Camera facing: while live, switch the facing selector to
   Rear-facing. The stream restarts on the rear camera (the view now
   shows what the back of the phone points at). Switch back to
   Front-facing and confirm the selfie view returns. On a device with
   only one camera, either choice still shows that camera — the facing
   is a preference, not a requirement, so no error may appear for
   lacking a second camera.
4. Product switch while live: switch to Ignis, then Medicus. The accent
   color changes (red, then green), the limitations notice changes
   to that product's text, and earlier history entries keep the product
   they were recorded under.
5. Sampling: start analysis with no backend running. Confirm the
   loading indicator appears while a request is outstanding, the
   sampler counters move (ticks / sent / skipped / failed), and each
   failure lands in the history styled as an error with the real
   message. No assessment card may appear.
6. Rotation: rotate the phone. The layout re-flows, the video keeps
   running, and no control disappears off screen.
7. Log export: after a few entries, tap Export log (JSON) and confirm
   the downloaded file opens and lists the entries with product,
   timestamp, latency, and outcome.

## 2. Web frontend on a Mac browser (Chrome and Safari)

1. Same steps as the phone check, on a laptop webcam: permission
   prompt, live preview, CAMERA LIVE indicator, honest states when
   permission is denied or the camera is busy in another app.
2. Wide layout: above 720 px the page shows its multi-column layout;
   resize the window across the breakpoint and confirm it switches
   cleanly between layouts with nothing cut off.
3. Sample interval: change the interval to 1 s and to 60 s and confirm
   the sampler follows the new value (visible in the counters).

## 2b. Still-image input (web, any device; native Mac panel mirrors it)

No camera needed, so this can be checked before the camera checks.
The native app has the same input as a Still image panel (Choose Image /
Assess this image / Clear, image-only picker, in-memory preview, sent
once under the selected product, cleared by Reset Session), so repeat
steps 1–4 below in the native app as well, with the picker in place of
the file input.

1. Choose a non-image file: the UI says it is not an image and the
   Assess button stays disabled.
2. Choose an image: a preview appears, the Assess button enables, and
   the note says the image is sent once under the selected product and
   is not stored.
3. With no backend running, tap Assess this image: the loading
   indicator shows while the request is outstanding, then the honest
   "Model backend not connected" error lands in the history and the
   session log, and no assessment card appears. The log entry carries
   the product selected at assess time and the scenario label, if one
   was chosen.
4. Tap Reset: the preview clears, the file choice clears, and the
   Assess button disables again.

## 3. Native macOS app (MetaTrio)

Requires a Mac with macOS 13+ and Xcode 15+. Build with the bundled-app
route — it is the only route that reliably gets camera permission:

```bash
cd native
./Scripts/make-app.sh
open MetaTrio.app
```

1. First build: record whether the build succeeds cleanly. Any first
   compiler error is an expected first iteration on real hardware, not
   a surprise — fix it, note it, rebuild.
2. First launch: if Gatekeeper objects, right-click the app and choose
   Open. Confirm the window shows the product switcher and the
   limitations notice.
3. Camera permission: start the camera. macOS asks for permission;
   allow it and confirm the live preview appears. Then deny it (System
   Settings → Privacy & Security → Camera, toggle off), restart the
   app, and confirm it reports permission denied honestly.
   Note the ad-hoc signing quirk: after a rebuild, macOS may treat the
   app as new and ask again, or show permission as off — toggle it
   back on in Privacy & Security.
4. Product switch, sampling, timeline, and log export: same checks as
   the web frontend, confirming the native app matches the web contract
   (per-product scenarios, sampling disclosure, failure entries in red,
   JSON export in the same shape).
5. Endpoint editing: change the endpoint in Settings to a dead address
   and confirm the app shows the real connection error, not a fake
   result.

## 4. Live backend round trip (server exists; Spark test phase LIVE since 2026-10-30)

Agent 2's `/api/assess` server exists (`server/server.mjs`). Live
model calls were held until Del green-lit the test phase, and that
green light has now come: 2026-10-30 00:23 EDT, Del via Pax on the
bus. The held-state round trip is verified: 2026-10-28, the server
answered `/api/health` with `live_enabled: false`, and a valid assess
request returned HTTP 503 with the real held message. The frontends
surface that message honestly and render no assessment. That record
stands as history; what follows is the current state.

Update 2026-10-30 (Hana, from Pax's official bus post): the Spark
test phase is LIVE, on a $75 test budget. Del puts SPARK_API_KEY in
the server env on the Mac himself — never on the bus, never
committed. The OS-queue round trip already has live proof from Pax:
a steam frame through the queue service and resident agent, validated
before any result write, idempotent with no re-bill. What is still
unproven is a live assessment driven from the web console or the
native app UI on real hardware — checks 1–3 below stay to run with a
live backend, on the Mac that holds the key. The sandbox still makes
no live calls: no key here. Until a live backend is pointed at,
repeat checks 1–3 against the held server only to confirm the
honest-error path. With a live backend, repeat checks 1–3 with the
endpoint pointed at it, for one product at a time:

1. A real frame returns a valid v2 assessment: it renders with product,
   category, observations, evidence, confidence (or "not reported"),
   uncertainty list, and human-review flag.
2. A deliberately malformed reply (wrong product, bad timestamp,
   confidence outside 0–1) is rejected whole, with the specific problems
   listed, and nothing renders as a detection.
3. The client-measured round-trip latency appears separately from the
   server-reported `processing.latency_ms`; the two are never mixed.

## 5. Logo panel (web and native, no camera needed)

The console's Logo panel (Del direction, Oct 30) needs no camera, so
these checks can run before the camera checks. They cover the web
panel and the native Mac panel together: same six presets, same
custom picker, same Reset, same speed slider, same pause button,
same storage keys (`meta-trio-logo-color`, `meta-trio-logo-speed`,
`meta-trio-logo-paused`).

Web console (phone or Mac browser):

1. Presets: tap each of the six swatches in turn — Meta blue, Cyan,
   Violet, Pink, Emerald, Gold. The spinning loop behind the panels
   re-tints live to that color, and the chosen swatch shows its ring.
2. Custom picker: pick a color that is not a preset. The loop
   re-tints, and the value line shows the hex in capitals.
3. Reset: tap Reset to product color. The loop returns to the
   selected product's tint (Vigiles blue, Ignis red, Medicus green),
   and the value line reads "Logo color: product color".
4. Speed: drag the slider to 0% — the loop stands still. Drag it to
   100% — the loop runs clearly faster than at 25%. The value line
   shows the percent.
5. Pause: tap Pause logo — the loop holds its last frame. Tap Resume
   logo — the loop continues from that frame, not from the start.
6. Persistence: reload the page. The saved color, speed, and pause
   state come back before the first frame — no flash of the product
   tint or the usual drift first.
7. Reduced motion: with Reduce Motion on, the loop renders one still
   frame.
8. Studio link: tap "Open the full logo studio" in the Logo panel.
   The large animated logo studio page opens.
9. Studio persistence: in the console pick a color, a speed, and
   Pause, then open the full studio — it opens in that color, at
   that speed, paused. Change the color or speed in the studio,
   reload the console — the studio's choices come back in the
   panel. With nothing saved, the studio keeps its own defaults
   (Meta blue, 30%, playing).
10. Studio back link: in the full studio, tap Back to console
    under the studio title — the console opens in the same tab,
    with the saved color, speed, and pause state still applied.
    (The shipped root studio, logo-studio.html, has no back link;
    it is the verbatim v2 file and is not the studio the console
    links to.)
11. Studio Reset: in the full studio pick a color that is not
    Meta blue and drag the speed off 30%, then tap Reset. The
    logo returns to Meta blue at 30%, playing, with its rotation
    re-homed. Reload the studio — it still shows Meta blue at
    30%, playing, not the pre-Reset choices. Reload the console
    — its Logo panel reads "Logo color: product color" again,
    because the two pages share the saved keys.
12. Studio reduced motion: with Reduce Motion on, open the
    full studio — the large logo renders one still frame, like
    the console loop in check 7, not a spinning loop. Drag it
    — it turns by hand and holds the new angle. Pick a color
    — the still frame re-tints. The top status reads STILL
    FRAME, not LIVE RENDER, and its dot carries no glow.
    (The shipped root studio, logo-studio.html, is the verbatim
    v2 file and is not the studio the console links to.)

Native Mac app (MetaTrio):

1. Run the same preset, picker, Reset, speed, and pause steps in the
   Logo panel. Quit and relaunch the app: the choices come back,
   exactly like the web reload check.
2. Hover a swatch: its name appears. With VoiceOver on, the chosen
   preset is announced as selected, and the pause button announces
   Paused or Playing.
3. With Reduce Motion on, the loop renders one still frame.
4. The note under the panel says the large logo stays in the web
   studio. There is no studio link to tap in the native app — confirm
   the note reads that way, and do not expect a link.

## Results log

When a check is run, append the outcome here (date, device, result,
and any fix that followed). Until then, this file's status is:

- Web on phone: NOT RUN
- Web on Mac browser: NOT RUN (page load and module execution only,
  in headless Chromium in the sandbox)
- Still-image input: NOT RUN in a real browser or in the native app
  (web unit tests cover file validation and reading; element ids and
  module syntax were checked in the sandbox, but the file-picker and
  tap path needs a real browser, and the native panel has not been
  compiled — no Swift toolchain in the sandbox)
- Native app build and camera: NOT RUN (no Swift toolchain in the
  sandbox; source reviewed by inspection only)
- Live backend round trip: TEST PHASE LIVE since 2026-10-30 00:23 EDT
  (Del's green light via Pax, $75 budget, key on the Mac only);
  queue round trip proven live by Pax; a live assessment driven
  from the web or native UI is still NOT RUN. Held-state round trip
  VERIFIED 2026-10-28 (`/api/health` reports `live_enabled: false`,
  assess returns HTTP 503 with the real held message, frontends show
  it and render no assessment)
- Logo panel (web and native): NOT RUN on real hardware (checks
  added 2026-10-30; web unit tests cover the color, speed, and pause
  logic, native Swift reviewed by inspection only, no Swift toolchain
  in the sandbox)
