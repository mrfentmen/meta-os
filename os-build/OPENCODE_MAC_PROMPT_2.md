# OPENCODE_MAC_PROMPT_2.md — Mac run round 2: native build, map, flagged path

**By the boss's direct order (Del / Mrfentmen, 2026-10-30).** You are
OpenCode on the boss's Mac. Round 1 (`OPENCODE_MAC_PROMPT.md`) is DONE:
gate 2 green (1412 Rust tests), B10/B15 merged, app suites green, and
one live patrol round trip VERIFIED (baseline result). This file is the
round-2 work order. Same working rules as round 1: work autonomously,
do not stop to ask questions, smallest reasonable decision + note it in
the report, two genuine failed attempts on a step means stop that step,
write the exact failure, and move on. Never present a mock, a stub, or
an expectation as a result.

## The API key — layout learned in round 1, read carefully

The key file is at **`~/Desktop/hackathon key.txt`**. It has 28 lines
and **the key is line 1 only**. Using the whole file fails with HTTP
401 — that already happened once; do not repeat it. Extract line 1,
trim whitespace, use it as `SPARK_API_KEY` in process env only.

Same hard rules as round 1: never print, echo, log, screenshot, or
commit the key; never write it into any file in the repo; before every
commit, `git status` and confirm the key file is not staged; destroy any
temp copy when you finish. If the file is missing, do the non-Spark
tasks and mark the Spark tasks BLOCKED in the report.

Budget: the repo guardrail enforces a $75 test cap (shared ledger,
runtime state, never commit it). Round 1 spent $0.005241 total. This
round has one bounded-spend task (task 5) with its own ceiling below.

## Tasks

### 1. Sync and settle the MapLibre question

`git pull` main (expect 0e2cea18 or later). Then check the vendored map
files **in your checkout**:

- `vendor/maplibre/maplibre-gl.js` should be about **803 KB**
- `vendor/maplibre/maplibre-gl.css` should be about **65 KB**

These sizes are verified against the repo blobs, which are
byte-identical to the official MapLibre GL JS v4.7.1 release. In round 1
your `/tmp/meta-os-mac` checkout somehow held a 59-line stub and a
0-byte CSS — that was a bad checkout, not the repo. If your checkout
shows stub-sized files again, delete the checkout, take a fresh clone,
and say in the report that you did. Do not edit the vendored files.

### 2. run-stack.sh, clean end-to-end start

The bash 3.2 crash is fixed on main (commit 9cd59e5a). From a clean
state (nothing on ports 8080/8787/8935), run `bash run-stack.sh` and
confirm all four services come up: Nuntius relay :8787, queue :8935,
resident agent, app :8080, and `GET /api/crew/status` responds. If the
script still fails on macOS, you are authorized to make the smallest
portability fix to `run-stack.sh` itself and push it — note the fix in
the report. (Round 1's manual bring-up does not count; this task is the
script itself, start to finish.)

### 3. Browser verification of the Command view

With the stack up, open the app in a real browser on this Mac and
verify, one by one:

- The 3D map renders: CARTO basemap visible, buildings extruded.
- The camera list loads through `/api/cameras` (the proxy added in
  2128ef8d) — the page must show the live list, NOT "Offline camera
  list". (The proxy endpoint itself was verified from this Mac in
  round 1; this task is the in-browser load.)
- Camera snapshots display on pins / in the camera wall.
- Clicking a building opens its popup; selecting a camera shows its
  ring and inspector.

If anything fails, capture the exact browser console errors and put
them in the report. Small frontend fixes are in scope if the cause is
clearly in this repo's code; no redesign, no restyling. Push any fix
with the failing-then-passing evidence described in the report.

### 4. Native app: fix the build

Round 1, fresh clone, `bash Scripts/make-app.sh` failed in
`swift build` with:

- `xcrun: error: unable to lookup item 'PlatformPath' from command line tools installation` (and the MacOSX.sdk path)
- `AssessmentView.swift:191,194: 'foregroundStyle' is only available in macOS 14.0 or newer`
- `CameraPreviewView.swift:18,27: method must be declared fileprivate because its result/parameter uses a private type`
- Cascading: `ContentView.swift:68: cannot find 'LogoColorPanel' in scope`
- Toolchain observed: Swift 5.10, CLT at /Library/Developer/CommandLineTools, macOS 27.0.1

Work in the separate native clone. Order matters:

1. **Toolchain first.** The xcrun errors point at a Command Line Tools
   install that cannot serve SDK lookups. Check `xcode-select -p`,
   whether a full Xcode app exists on this Mac, and whether
   `xcrun --find swift` / `xcrun --show-sdk-path` work. If fixing this
   needs a full Xcode install, a system settings change, or any GUI /
   admin step only the boss can do, STOP this task at that point and
   write exactly what the boss needs to do — do not fake a build.
2. **Then the code errors**, smallest changes: availability handling
   for `foregroundStyle` (annotate the views or adjust the deployment
   target in project config if that is clearly the project's intent —
   say which you did), the `fileprivate` declaration, and
   `LogoColorPanel` (first check whether it is pure cascade from the
   earlier errors; if it is genuinely missing, find where it belongs
   and restore the smallest definition consistent with the surrounding
   code).
3. Rebuild with `bash Scripts/make-app.sh`. If it builds, open
   MetaTrio.app, verify the camera loads, and run ONE live assessment
   round trip (key file rules above; one call).
4. Native code fixes ARE in scope this round: commit and push them to
   main under `native/`, with the build result stated in the commit
   message. Nothing outside `native/` for this task unless a fix
   genuinely requires it — if it does, say why in the report.

### 5. Exercise the flagged path — bounded spend

Round 1 proved the baseline path. This task tries to prove the rest of
the loop live: patrol → flag → review → orchestrator → investigation →
simulated dispatch.

- Run the patrol across a batch of live cameras. You may also feed
  stills from the repo's own `test-footage/` pack through the real
  assess path (real code end to end; stills are test inputs, and the
  report must say which inputs were used).
- **Spend ceiling for this task: $1.00 of Spark calls**, counted from
  the guardrail ledger before and after. Stop at the ceiling or when
  one flag completes the chain, whichever comes first.
- If a flag occurs, record the evidence chain: job ids, the review
  outcome, the orchestrator decision events, investigation findings on
  the incident record, and — if a response is prepared — the simulated
  dispatch receipt (`sim-` id). Dispatch goes ONLY to the loopback
  simulated endpoint. Never repoint it; never contact anything real.
- If no flag occurs within the ceiling, report exactly that:
  "flagged path not exercised live" with the number of assessments run
  and the spend. Do not force, stage, or fabricate a flag.

### 6. Report

Append an **"Addendum 2 — round 2"** section to `MAC_RUN_REPORT.md`,
commit, and push. Per task: VERIFIED (with the evidence), FAILED (exact
errors), or BLOCKED (exactly what the boss must do). Include: the
checkout file sizes from task 1, the run-stack result, the browser
results item by item, the native build result, the flagged-path
evidence chain or the honest no-flag result, every commit you pushed,
and the guardrail ledger total after this round. Close with an updated
"still unverified" list.

## Standing rules (unchanged from round 1)

- Push verified work straight to main. Never force-push.
- Never commit: the key file, any `.env`, the guardrail ledger,
  `server/queue/crew-data/`, or any secret of any kind.
- Never delete or rewrite the Python/Node fallback stack; the Rust
  code stays a faithful port, never a redesign.
- `TRIO_UPSTASH_HOST`: use only if the boss provides it; otherwise the
  labeled local SQLite fallback stands. Never invent a hostname.
- Medicus is EMS scene awareness only — no diagnosis, cause, severity,
  or treatment language. Observation language only in anything
  incident-shaped: no claims of criminal intent, guilt, or legal
  violations; no face recognition or identity tracking.
