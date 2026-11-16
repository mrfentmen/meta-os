# ClearCam Pattern — Camera Layer for Imperium — Spec

Status: SPEC ONLY — nothing built. Written 2026-11-16 at Del's order.
System: Imperium / Meta Sentinel (Meta OS system one) — all three
services (Vigiles, Ignis, Medicus) sit on top of this layer.
Source stimulus: Instagram post by @githubprojects (Github Projects),
2026-11-11 — https://www.instagram.com/p/Dfmf7s6lDt0/
Upstream project: ClearCam, by Rory Clear —
https://github.com/roryclear/clearcam

## What ClearCam is (VERIFIED off its GitHub README, 2026-11-16)

ClearCam adds object detection, tracking, mobile notifications, AI
summaries, and search to any security camera. It is a self-hosted
NVR + inference stack, not a camera product:

- Ingest: any RTSP camera (repo topics: rtsp, cctv, nvr, selfhosted).
  A public test feed is linked in the README for people with no camera.
- Detection: YOLOv9-class detector, tinygrad backend (repo topics:
  yolov9, tinygrad; `detection/` and `models/` in the tree).
- Tracking: an OC-SORT tracker (`ocsort_tracker/` in the tree) — the
  same object keeps one track across frames instead of re-detecting
  as a new object every frame.
- Zones: an Edit Zone panel where a polygon is drawn over the camera
  view (README screenshot: green polygon over a roadway) — detection
  is judged inside the zones that matter, not the whole frame.
- Events, not streams: live views (cam1 / cam2 in the screenshots),
  event clips, and bounding-box detections (README screenshot: cars
  boxed on a street) are the stored, searchable record.
- Search: headline feature of the repo ("...and search to any
  security camera"). What the search UI actually queries is NOT
  stated in the README text read — UNVERIFIED, see Known limits.
- AI summaries: "AI Notification Summaries with Qwen3 VL" — a vision
  model writes the event summary that goes out with a notification.
- Notifications, bring-your-own: the notification URL is changeable
  in settings; Home Assistant, Pushover, n8n, or any program can
  receive them. A sample Pushover notification server ships in
  `utils/sample_server.py`.
- Apps: iOS and Android clients; the server runs from source with
  `python3 clearcam.py` and serves a web UI at localhost:8080.
  Requirements per README: Mac or Linux (Windows marked as needing
  an ffmpeg fix), ffmpeg, Python 3.11 or later.
- Premium (upstream's own paid tier, NOT part of this spec): remote
  live feeds, event notifications, remote event clips, end-to-end
  encryption on all data, via clearcam.org.

Repo facts at read time: public, GPL-3.0, created 2025-01-04,
1,656 commits, 13 releases, ~2,656 stars, 258 forks.

## Where it plugs into Meta OS

This is the opposite end of the sensor problem from the Wi-Fi CSI
spec (os-build/WIFI_CSI_VIGILES_SPEC.md). CSI is an image-free weak
signal looking for a camera to corroborate it. ClearCam is the
camera layer itself, done properly:

1. **It upgrades our live-camera input.** Today
   `server/queue/livecams.py` (os-build/LIVE_CAMS.md) polls JPEG
   stills from NYC DOT cameras and sends single frames to the
   assessment path. That proves the input path, but a still cannot
   track anything. The ClearCam pattern is continuous RTSP ingest:
   detect, track, zone-filter, and store events first; assess
   events second.
2. **It gives all three services one shared event source.**
   Vigiles, Ignis, and Medicus currently assess frames. Under this
   layer they assess the same structured camera events — a tracked
   person in a zone, a vehicle stopped in a zone, motion in a zone
   that should be empty — each under its own categories and language
   rules. No service gets its own camera stack.
3. **It is the missing event archive.** Detection + tracking + zones
   produce a searchable event record (camera, time, class, track,
   zone, clip). That is the archive the patrol, the evals, and human
   review all need; raw video retention alone is not searchable.
4. **Its notification shape matches our alert law.** A changeable
   outbound notification URL is exactly the seam where Sentinel's
   alert tiers attach: small = yellow quiet note, big = red full
   alarm, human review before anything escalates.

## Design

### New component: camera-layer adapter (Imperium sensor layer)

- Input: RTSP streams from cameras we have the right to use — our
  own cameras, staged setups, and public camera networks whose
  terms allow pulling the feed (NYC DOT per LIVE_CAMS.md;
  embed-only networks stay embed-only, never pulled).
- Processing, in order: decode (ffmpeg) → detect (object/person/
  vehicle classes) → track (persistent track IDs, OC-SORT pattern)
  → zone filter (per-camera polygons) → event cut (start/end,
  clip, peak frame) → event record.
- Output: scene events in the existing Sentinel event shape, one
  per tracked event, for the existing triage / assessment /
  correlation pipeline. The camera layer does not assess, triage,
  or alert on its own.

### Event contract

The adapter emits a standard Sentinel scene event, e.g.:

- category: assigned downstream by the assessing service, never by
  the camera layer — the layer emits the raw observation only
- sensor: `rtsp_camera`
- camera_id, zone_id (null when outside all zones)
- track_id: ephemeral, lives only for this event; it is an object
  track, never a person identity
- object_class: detector class as emitted (person, vehicle, object),
  passed through unmodified
- confidence: detector score, passed through unmodified
- trajectory: bounding boxes over time, window timestamps
- clip_ref: the stored event clip and peak frame, with hashes,
  same record discipline as livecam_records/

### AI summary field

Following the upstream pattern, an event may carry a vision-model
summary of its clip. In Sentinel that summary is product-bound:

- It describes visible scene conditions only.
- Under Medicus it obeys Medicus doctrine in full: no diagnosis, no
  cause, no severity, no treatment language.
- It never names or identifies a person. A track is not an identity.
- It is labeled as a model summary on every surface, same honest
  labeling rule as every other sensor.

### Search

The event store is indexed by camera, time, object class, zone,
and track, so review and evals query events instead of scrubbing
video. Natural-language search over events is NOT claimed here:
upstream advertises "search" without the README stating its form,
and our own natural-language query idea stays a separate, unbuilt
proposal until it is specced on its own.

### Notifications

Outbound notifications reuse the bring-your-own-URL pattern: one
configurable webhook from Sentinel's alert surface. Recipients are
the operator's own systems only. See hard rule 3.

## Hard rules (house doctrine, non-negotiable)

1. **GPL-3.0 — no copied code.** ClearCam is GPL-3.0. Clean-room
   rule applies as always: study the approach, reimplement the
   behavior, never copy code or assets into Meta OS. Running
   upstream ClearCam itself, as a separate GPL service, is a
   different option with its own license obligations — that
   decision is Del's, recorded before anything is installed or
   imported.
2. **A detection is not a finding.** A bounding box and a track are
   a sensor observation, unconfirmed, same status as a CSI flag.
   It may open a review item; assessment and human verification
   decide what it means. No surface may present a detection as an
   incident.
3. **Simulated dispatch only.** Notifications go to the operator's
   own webhook / Sentinel alert surface. Never a real 911, police,
   fire, EMS, or security service. The dispatch endpoint stays the
   clearly labeled simulated one, forever.
4. **No identity claims.** The tracker follows objects, not people.
   No face recognition is in the upstream README and none is added
   here. Track IDs are ephemeral and must not be linked across
   events, cameras, or days to build a history of a person.
5. **Footage discipline.** Prerecorded footage, staged scenes with
   consenting participants, our own cameras, and public feeds whose
   terms allow it — only. Event clips inherit the livecam record
   discipline: hash, fetch time, camera identity, honest labels.
6. **Honest labeling.** Every surface that shows a camera event
   labels it as machine detection with its confidence, and labels
   model summaries as model summaries. Detection state is shown as
   UNVERIFIED until the assessing service and a human have graded
   it.

## Eval: the failure classes are the whole game

The camera layer ships with an eval set it must be graded against
before any threshold is trusted, reported per class, never as one
blended accuracy number:

- parked vehicle vs stopped vehicle (zone dwell decides, not class)
- person standing vs person on ground (the Medicus look-alike shape:
  bench sleeper, sunbather, yoga, curb rest, CPR manikin)
- shadows and headlight sweep at night (false-object control)
- rain, camera shake, IR night mode (degradation classes)
- two objects crossing (track ID swap control)
- object entering/leaving a zone edge (zone boundary control)
- empty street / empty room (negative control)
- occlusion: object passes behind cover and returns (track
  continuity control)

Metrics per class: detection rate, false-event rate, track ID
stability, zone accuracy, and clip start/end accuracy.

## Known limits (state them, don't discover them in production)

- Nothing here is verified by us: ClearCam was not installed,
  no camera was run through it, no detector accuracy was measured.
  This spec is CODE-INSPECTED reasoning from the upstream README
  and one public post. Status of the fit: UNVERIFIED until step 1
  of the build order runs.
- The README does not state the detector's class list in full or
  any accuracy numbers. Do not quote any until we measure our own.
- The exact form of upstream "search" is not stated in the README
  text read. We spec our own index (above) and claim no more.
- Upstream Windows support is marked broken (ffmpeg fix needed);
  our target is Linux/Mac, same as the rest of the stack.
- Upstream Premium (remote access, E2E encryption) is their paid
  service. It is not a dependency of this spec and must not become
  one silently.

## Build order (when Del says go)

1. Read the upstream repo in full (code-inspected) and record the
   separate-service vs clean-room decision with Del, GPL first.
2. Standalone harness: RTSP ingest → detect → track → zones on the
   README's public test feed and our own staged footage; run the
   eval classes above and publish per-class numbers.
3. Adapter emitting the event contract into the Imperium pipeline,
   beside livecams.py, simulated endpoint only.
4. Event store + index (camera / time / class / zone / track) and
   the review surface that queries it.
5. Notification webhook onto Sentinel's alert tiers (small =
   yellow quiet note, big = red full alarm), operator systems only.
6. VLM summary pass over event clips, product language rules
   enforced, labeled as model output everywhere it appears.

## Provenance

- Post: @githubprojects (Github Projects), Instagram, 2026-11-11.
  Caption, in substance: add object detection, tracking, mobile
  notifications, and search to any security camera, with the
  ClearCam GitHub link. The post image is a screenshot of the
  ClearCam README (live cam1/cam2 views, boxed cars, Edit Zone
  polygon).
- Read by Pax via the Instagram connector 2026-11-16, and the
  ClearCam README read in full the same day. Every feature claim
  above traces to one of those two reads; anything the README did
  not state is marked UNVERIFIED in place.
