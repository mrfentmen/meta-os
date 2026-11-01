# Addendum to round 2: the demo recorder (boss order 2026-11-01)

The new demo film is 3 minutes: Meta OS first, then the systems, one
by one. The boss wants the in-OS footage recorded with the tool that
smooths the mouse cursor and zooms on clicks, so the video looks
produced instead of captured raw.

The tool is OpenScreen (verified by Pax on GitHub, 2026-11-01):
- Repo: github.com/siddharthvaddem/openscreen
- "Create stunning demos for free. Open-source, no subscriptions, no
  watermarks, and free for commercial use. An alternative to Screen
  Studio." MIT license. About 40,000 stars. Last push 2026-10-17.
- It smooths the cursor, auto-zooms where you click, and edits on a
  timeline. Latest release v1.5.0 (2026-06-06).
- The boss's Mac is ARM (M3). The right download is the release asset
  Openscreen-Mac-arm64-.dmg, about 302 MB.

## Tasks (in order)

- REC-1 Download that exact .dmg from the v1.5.0 release, check the
  size matches (about 302 MB), install OpenScreen into /Applications,
  and record the version that launches.
- REC-2 Launch it once. If macOS asks for Screen Recording
  permission, stop and report that plainly: the boss grants that one
  himself, like the camera prompt. Do not work around it.
- REC-3 Test take: record 10 seconds of the desktop with deliberate
  cursor moves and two clicks. Export the MP4, ffprobe it, pull one
  frame and view it. The smoothed cursor and a click zoom must be
  visible in the export, or the test fails and gets reported as
  failed.
- REC-4 Re-record the two hero app clips with OpenScreen (the app
  home screen and the camera wall from Section F), moving the cursor
  and clicking as a presenter would, so the zoom has something to
  follow. Fresh unique file names, into oc-proofs/footage/, named as
  openscreen takes so nobody mixes them with the plain takes.
  Frame-check each one.
- REC-5 The OS segment: with the UTM machine from Section E running,
  record ONE take with OpenScreen from the host: boot, then a tour
  inside Meta OS, opening the systems one by one (Imperium console,
  then each system surface that exists). This is the demo's "inside
  the OS" footage. About 60 to 90 seconds of raw take is plenty; the
  film cuts it down. No staged incident, no camera permission work
  inside the guest.
- REC-6 Write oc-proofs/DEMO_RECORDER_REPORT.md: install result,
  permission status, the test take result, and every clip name with
  its frame-check result. Time cap: if OpenScreen will not install
  or will not run on this Mac, stop after 30 minutes of trying,
  report the exact failure, keep the plain Section F footage as the
  fallback, and name Recordly (also open source) as the next
  candidate for the boss to call. Do not burn the round on it.
