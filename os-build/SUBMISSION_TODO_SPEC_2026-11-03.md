# Meta OS hackathon submission — everything left to do

Deadline: **Wednesday, November 4, 2026, 9:00 PM ET.** Del is the sole
submitter. Repo: github.com/Mrfentmen/meta-os (public, created Oct 28,
inside the event window). Track: Indie, Push the Frontier.

## 0. The rule for "done"

Nothing counts as done until Del has seen it. That rule is why the demo
video is back on the open list below — a file Pax verified on disk is not
a finished demo until Del has watched it and approved it.

## 1. THE DEMO VIDEO — the main job tonight

### Where it actually stands

- An existing cut exists: `os-build/demo/demo-3min.mp4`.
  Pax-verified at the file level only: exactly 180.000 seconds,
  h264 1280x720, **no audio track (silent)**, sha256
  a29bc47dd56e9f583d8af231d8d3908f3a4c4d6218fb1b3492ce5381b3ae13f0.
- **Del has never seen it. Status: NOT DONE, NOT SUBMITTABLE.**
- Fresh-named viewing copy sent to Del 2026-11-03 (link in chat,
  expires Nov 5, 10:49 PM ET).

### Tonight's plan (Del's, set 2026-11-03 22:37)

**Step 1 — Del captures a clean video of the operating system itself.**
Introduce the OS on camera first; the rest of the demo gets built around
that footage over the next few hours.

Shot list for the capture:
1. Boot: power-on / QEMU start through the blue ASCII Meta ribbon.
2. Desktop: the kernel-drawn desktop with the Meta-blue dock and icons v2.
3. Shell window: the real shell answering commands inside the window
   (status, uptime, mem, ps).
4. A short pass over the face and the systems (Imperium, Science Lab,
   Officina) if the take stays clean.

Capture rules:
- 720p minimum, steady framing, full screen where possible.
- No notifications, no popups, nothing else on screen.
- No secrets on screen: no API keys, no vault screens, no personal tabs.
- One clean take per shot, plus one spare take of the boot.

**Step 2 — Build the full demo around that footage (Del + Pax).**

Hard cap: 3 minutes total. Target structure:

- 0:00–0:20 — Introduce Meta OS: an operating system and platform that
  boots on x86_64, with systems plugged into it.
- 0:20–0:50 — The OS itself: boot, desktop, dock, shell window (Step 1
  footage).
- 0:50–1:50 — Imperium: a camera frame goes through the pipeline —
  Spark patrols, SAM 3.1 segments the region, Wonder reviews, the judge
  decides, dispatch goes to the labelled SIMULATED endpoint and a
  receipt comes back. Source material: the 2026-11-03 live proof run
  (real model calls, receipts on disk). Those frames are staged eval
  frames and must be labelled as such. **No claim of a live-camera flag:
  it has never happened (67 live frames, zero flags).**
- 1:50–2:30 — The systems: Science Lab (Delaney equation reproduced;
  CURE-1103 candidate pool sealed; GEN-1103 — 11,586 novel candidate
  structures against Candida with synthesis plans, sealed at the wetlab
  gate, efficacy unproven) and Officina (a heatsink designed from rough
  words and proven at 0.8507 C/W in copper, blueprint rendered).
- 2:30–3:00 — Close: the platform line and the repo URL.

**Audio decision — Del's call before the build finishes.** The existing
cut is silent. Options: (a) Del records the voiceover tonight,
(b) captions and text cards with music, (c) silent with text cards.
The synthetic voice lane stays parked: no new takes without Del's word.

**Step 3 — Del watches the FULL final cut and approves it by name.**
No approval, no submission. Cuts are delivered as links under fresh
filenames only (never re-use a name — the app replays the cached first
cut under a repeated name).

**Step 4 — Final file locked.** Pax verifies the approved file:
duration, resolution, hash recorded; link confirmed playing end to end.

## 2. The submission checklist, item by item

Source: `os-build/SUBMISSION_CHECKLIST.md` in the repo (Del's actual
checklist). Status as of 2026-11-03 22:40:

- [x] **Repo public and fresh** — DONE, verified: public, created
  Oct 28, 2026.
- [ ] **3-minute demo video** — OPEN. Section 1 above.
- [ ] **Meta models named** — FACTS READY, one decision open.
  Proven live in the pipeline on 2026-11-03: Muse Spark 1.3 (patrol and
  investigation), SAM 3.1 (segmentation — boxed the fire frame; the
  other two frames returned no segment and the error was recorded, not
  hidden), Muse Wonder 1.0 (review). Decision for Del: the Wonder
  image fix sits on Pax's local branch `pax/wonder-responses`
  (unmerged, branches-only rule). If the form says the shipped code
  reads review images with Wonder, that branch has to land first via
  Del or the OpenCode lanes — otherwise the wording must say the
  pipeline was proven live with the fix pending merge. Pick one before
  the forms are filled.
- [ ] **Library attributions** — OPEN, Pax's job. Compile the full list
  of anything not built inside the event window. Known so far:
  rust-osdev bootloader 0.9.35 (named in kernel/src/main.rs header),
  QEMU/SeaBIOS (in boot logs). Full sweep of external code, assets and
  data in the repo still to do. Deliverable: an attributions file on a
  branch, plus the form field if the form asks.
- [ ] **One project only** — SETTLED by Del's rule: everything lives
  inside mrfentmen/meta-os, no separate entries. Confirm once more at
  submit time.
- [ ] **Claim audit** — OPEN, Pax's job, finished before the forms.
  Every claim in the video, the forms and the README must map to a log,
  a test run, or a receipt. The one claim sentence, verbatim:
  "Meta OS boots on x86_64 in QEMU, drops to ring 3, runs three
  userspace programs, isolates a fault to one task, and gives you a
  shell that reports the machine's real state — reproduced from a clean
  checkout by one command, every claim backed by a committed boot log."
  Known limits that stay OUT of the submission: no live-camera flag
  claim; no efficacy claim for the Science Lab generated compounds
  (model scores only); the home-boot ISO report is Del-reported and
  unverified by Pax — no ISO claims until the ISO lands on GitHub and
  Pax verifies its hash and contents.
- [ ] **No secrets in the repo** — re-run the scan at submit time
  (Pax, in the Nov 4 final sweep). Prior merges each carried a 0-hit
  scan.

## 3. Del-only steps (nobody else can do these)

1. Capture the OS footage (Section 1, Step 1) — tonight.
2. Audio decision and the Wonder wording/landing decision (Section 1
   and Section 2).
3. Watch and approve the final demo cut.
4. Final state snapshot with Milo (submission-day snapshot).
5. Fill and submit the hackathon forms on his own accounts.
6. Post the X post on his own account.

Pax preps everything for steps 5–6 as paste-ready text so the wrist
does no typing beyond taps.

## 4. Pax-side work queue (no Del input needed)

- Compile the library attributions list (Section 2).
- Form copy pack: project description, the Meta-model-use paragraph,
  the technical-depth paragraph — every claim pre-audited against
  Section 2's limits, ready to paste.
- Final verification sweep on Nov 4: test suites re-run on main
  (agents 254/254, queue 637, science-lab 374, officina 126 — the
  current verified baselines), secret scan re-run, README and site
  wording check, final video link check.
- Update `os-build/SUBMISSION_CHECKLIST.md` ticks on a branch so the
  file matches reality.

## 5. NOT blocking the submission — do not chase these tonight

- KF-10 desktop Mac screendump (strengthens proof; Mac step, Del's
  timing).
- The syscall-6 call and Buffy's five held kernel files.
- Milo's gate decision on Hana's 16 eval slices.
- City-pack declaration reconciliation.
- The ISO landing on GitHub.
- Landing the scheduler/worker branch stack.

## 6. Timeline

- **Tonight (Nov 3):** OS footage captured → demo built out around it →
  Del watches and approves the final cut.
- **Tomorrow (Nov 4), afternoon:** Pax final sweep + form copy pack
  ready → snapshot with Milo → Del submits forms and posts, well
  before the 9:00 PM ET deadline.
