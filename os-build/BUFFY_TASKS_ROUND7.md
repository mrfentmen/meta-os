# BUFFY — ROUND 7: THE GREAT BUILD-OUT (boss order 2026-11-02)

Supersedes Round 6 remainders; BF6-01 lives on as Section A.
Your lane stays `services/` + `os-build/layer1/`. ~250 tasks.
Freeze 05:12 applies to tonight's claims, not to this queue —
work it in order, slice + gate + merge as always. Status words
only: RUNS / TYPECHECKS / UNPROVEN, measured, never remembered.

## A. Close the 49 unproven limits (BF6-01, first)
A1–A25. One task per service that still holds unproven limits:
   write the missing drivers, one break-it test per limit,
   LIMITS.md updated per service as it closes. (25 tasks)
A26. The final count page: 75/75 or each leftover with its named
   reason. No silent leftovers.

## B. Deepen every existing service (25 services × 4 = 100)
For EACH of the 25 services, four tasks:
B-a. Failure-injection driver: kill/corrupt its inputs, record
   the service's behaviour against its contract.
B-b. Boundary sweep: every numeric limit at −1, exact, +1.
B-c. Restart semantics: state before/after a supervisor restart,
   proven by transcript.
B-d. Contract page refresh: inputs, outputs, limits, failure
   modes — matching the code as it stands, not as written before.
(100 tasks, reported per service as they close.)

## C. Face-era services (new; the desktop needs a back end)
Design + driver-proven Goose services, same discipline:
C1–C6. session service: login state, lock, idle/attract timing.
C7–C12. settings service: wallpaper, background colour, bar
   colour, mode, animation — get/set/persist/validate.
C13–C18. wallpaper service: the live-wallpaper registry, frame
   budget enforcement, pause-on-fullscreen state.
C19–C24. dock service: pinned apps, running state, launch
   requests and their results.
C25–C30. dashboard-feed service: CPU/memory/storage/network
   sampling with honest staleness labels.
C31–C36. updater-client service: pull check, apply, STOP file,
   result reporting (mirrors the image updater's contract).
C37–C42. board-client service: rooms, post, fetch, persistence
   contract for the board app.
C43–C48. notify service: receipts + updater + board events into
   one top-bar feed, dismissals logged.
(48 tasks)

## D. Supervisor and lifecycle, for real this time
D1. sys_spawn/sys_kill proposal P3: final text with Milo's C-lane
   as the consumer; what the kernel must provide, exactly.
D2. Load transcript ×3: 25 services under the supervisor driver,
   three runs, timings compared.
D3. Cascade failure drill: kill a dependency, record the tree.
D4. Restart budget: a service that crash-loops gets parked, and
   the park is visible in status. Driver + transcript.
D5. Order proof: BOOT_ORDER honoured under shuffled starts.

## E. Corpus integrity and records
E1. Whole-corpus typecheck re-run on current main; numbers in.
E2. Status-word sweep: 0 stale words across all records.
E3. DEMO_FACTS defence: every number with its command (BF5-09
   fires fully when Milo's claim audit lands — no chasing).
E4. SERVICES_FINAL v2 after Sections A–C land.
E5. Native test count reconciliation with Milo's D4 table.
E6. Dead-code census: files nothing references, listed, kept or
   cut with reasons — cuts need Pax's word per file.
E7. One README per service folder, three lines each: what, how
   to run its driver, what RUNS means for it. (25 tasks)

## F. Lobster host pack (BF6-04 carried)
F1. Caller skeleton for one service, end to end.
F2. Host requirements list (what a .lobster host must provide).
F3. Runbook: the exact commands, expected output, failure reads.
F4. Marked ready-to-run; no run claimed until a host exists.

Report per section to room 1. Milo gates, Pax merges.
