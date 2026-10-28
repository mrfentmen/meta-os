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

1. Page load: product switcher shows Vigiles / Ignis / Sanitas, the
   Vigiles limitations notice is visible, and the layout fits a narrow
   screen (single column below the 720 px breakpoint, no sideways
   scrolling, buttons reachable with a thumb).
2. Camera start: tap Start camera. Safari asks for camera permission.
   Allow it: the video preview appears and the CAMERA LIVE indicator
   shows. Deny it once, reload, and confirm the UI shows the
   permission-denied state in plain words — not a blank panel.
3. Product switch while live: switch to Ignis, then Sanitas. The accent
   color changes (orange, then green), the limitations notice changes
   to that product's text, and earlier history entries keep the product
   they were recorded under.
4. Sampling: start analysis with no backend running. Confirm the
   loading indicator appears while a request is outstanding, the
   sampler counters move (ticks / sent / skipped / failed), and each
   failure lands in the history styled as an error with the real
   message. No assessment card may appear.
5. Rotation: rotate the phone. The layout re-flows, the video keeps
   running, and no control disappears off screen.
6. Log export: after a few entries, tap Export log (JSON) and confirm
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

## 4. Live backend round trip (blocked until Agent 2 lands)

Once Agent 2's `/api/assess` server exists, repeat checks 1–3 with the
endpoint pointed at it, for one product at a time:

1. A real frame returns a valid v2 assessment: it renders with product,
   category, observations, evidence, confidence (or "not reported"),
   uncertainty list, and human-review flag.
2. A deliberately malformed reply (wrong product, bad timestamp,
   confidence outside 0–1) is rejected whole, with the specific problems
   listed, and nothing renders as a detection.
3. The client-measured round-trip latency appears separately from the
   server-reported `processing.latency_ms`; the two are never mixed.

## Results log

When a check is run, append the outcome here (date, device, result,
and any fix that followed). Until then, this file's status is:

- Web on phone: NOT RUN
- Web on Mac browser: NOT RUN (page load and module execution only,
  in headless Chromium in the sandbox)
- Native app build and camera: NOT RUN (no Swift toolchain in the
  sandbox; source reviewed by inspection only)
- Live backend round trip: BLOCKED (no `/api/assess` server yet)
