# Wi-Fi CSI Concealed-Object Sensing — Vigiles Sensor Layer Spec

Status: SPEC ONLY — nothing built. Written 2026-11-12 at Del's order.
System: Imperium / Vigiles (Meta OS system one).
Source stimulus: Instagram post by Ed Calderón (@manifestoradiopodcast),
2026-10-28, "WI-FI GUN DETECTORS?" — https://www.instagram.com/p/DfC43GGAGEt/

## What the research is

Researchers built an experimental setup that detects concealed handguns on
people moving indoors using standard Wi-Fi signals and machine learning —
no cameras, no physical checkpoints.

- A Wi-Fi transmitter and receiver bracket a walk-through area.
- As a person passes, their body and anything dense they carry disturb the
  radio field. The receivers record Channel State Information (CSI):
  per-subcarrier amplitude and phase.
- Dense objects produce distinct phase and amplitude signatures. A neural
  network classifies the CSI stream for a concealed-handgun signature.

Reported state of the art (from the post, UNVERIFIED beyond it):

- Early trials showed promise in controlled rooms.
- Accuracy drops significantly when judging weapon placement on the body.
- Everyday metal items frequently trigger false positives.
- The dataset and models are stated to be open-sourced for academic testing.

## Where it plugs into Meta OS

Meta Sentinel's sensing today is camera-first. CSI sensing is a second,
image-free perception channel. It belongs in Vigiles, beside the camera
adapters, for three reasons:

1. It sees where cameras cannot or should not be (occluded entries,
   camera-blind corridors, privacy-sensitive interiors).
2. It produces exactly the kind of weak, unconfirmed signal the Sentinel
   event pipeline is already built to carry and grade.
3. Its failure mode (false positives from ordinary metal) is the same
   shape as the look-alike problem Medicus already handles with an
   explicit look-alike eval class.

## Design

### New component: CSI adapter (Vigiles sensor layer)

- Input: a CSI feature stream from a transmitter/receiver pair
  (amplitude/phase per subcarrier, windowed over a person's transit).
- Processing: the open-source classifier from the cited research, run
  unchanged in v1. Clean-room rule applies as always: study the approach,
  reimplement behavior, never copy code or assets. If the upstream license
  permits direct use, that decision is Del's, recorded before any import.
- Output: one scene event in the existing Vigiles event shape.

### Event contract

The adapter emits a standard Sentinel scene event, e.g.:

- category: `person_transit_possible_concealed_dense_object`
- sensor: `wifi_csi` (never presented as vision)
- confidence: classifier score, passed through unmodified
- attributes: transit direction, window timestamps, receiver pair id

No new event types beyond this category. The rest of the pipeline
(triage, correlation, audit trail) treats it like any other sensor event.

### Hard rules (house doctrine, non-negotiable)

1. **Unconfirmed stays unconfirmed.** A CSI hit is a flag for a second
   look, never a finding. It may raise a review item; it may not raise a
   hard alert on its own.
2. **Corroboration before escalation.** Escalation requires a second,
   independent signal: a camera event, a second receiver pair, or a human
   reviewer. This is a direct consequence of the known false-positive rate
   on everyday metal.
3. **Simulated dispatch only.** Any dispatch path stays on the clearly
   labeled simulated endpoint. Never a real 911 or security service.
4. **No identity claims.** CSI carries no image and no identity. The
   adapter must not emit identity, intent, or guilt language — scene
   categories only, same as Medicus doctrine.
5. **Honest labeling.** Every surface that shows a CSI event labels the
   sensor as Wi-Fi sensing with its known limits, the same way Proof
   Gate labels its checker. No surface may present a CSI flag as a
   detection of a weapon; the category name says "possible."

### Eval: look-alike class (the whole game)

Following the Medicus pattern, the adapter ships with a look-alike eval
set it must be graded against before it is trusted at any threshold:

- keys in pocket
- phone in pocket
- belt buckle
- multi-tool / pocket knife (legal carry, common)
- laptop or tablet in a bag
- water bottle (metal)
- umbrella
- empty transit (negative control)
- multiple people in the field at once (contamination control)

Metrics reported per class, not one blended accuracy number: hit rate on
the target class, false-flag rate per look-alike class, and degradation
when the concealed object's placement changes (the research's known weak
point).

### Known limits (state them, don't discover them in production)

- Controlled-room results only so far; real venues are multipath chaos.
- Placement on the body degrades accuracy significantly.
- Everyday metal false positives are frequent, per the researchers
  themselves.
- Nothing here is verified by us: no dataset downloaded, no model run,
  no hardware tested. This spec is CODE-INSPECTED reasoning from one
  public post. Status of the underlying claim: UNVERIFIED.

## Build order (when Del says go)

1. Fetch and read the open-source dataset/models; verify the claim on
   their data before writing any adapter code.
2. Standalone CSI classifier harness with the look-alike eval set above.
3. Adapter emitting the event contract into the Vigiles pipeline,
   simulated endpoint only.
4. Correlation rule: CSI flag + second signal → review item. CSI flag
   alone → logged, graded, silent.

## Provenance

- Post: @manifestoradiopodcast (Ed Calderón), Instagram, 2026-10-28.
- Read by Pax via the Instagram connector 2026-11-12; caption is the only
  source so far. The research group, paper, and dataset link are NOT yet
  identified — step 1 of the build order starts there.
