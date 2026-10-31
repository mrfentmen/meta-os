# MAC_RUN_REPORT.md — Mac gate 2, merges, live verification (Del order 2026-10-30)

Runner: OpenCode on the boss's Mac. Fresh worktree at main tip
c31b277 (`/tmp/meta-os-mac`). No force-pushes. Key file
(`hackathon key.txt`) searched in repo root, home, Desktop,
Documents, plus a shallow find — NOT FOUND. Per the work order, no
key was invented and no other key on the machine was used: live
Spark steps are BLOCKED below, everything else was run.

## 1. Gate 2 — Rust workspace

- `cargo build --workspace`: clean, 0 errors, on main tip and after
  every merge below.
- `cargo test --workspace` on main tip c31b277: **1379 passed, 0 failed**.
- The known `fake_redis` stack overflow did NOT reproduce here.
- B31 RED-vs-clean dispute, settled plainly: RED was real at
  commit 791fda8 (`E0119` conflicting `Default` + a
  `new()`/`Default` mutual recursion that stack-overflows). Both
  were fixed on `batch/B31` (commit 8a0f9b3: derive dropped,
  constructor inlined) and reached main through the finish merge.
  Main is green; the RED report described the pre-fix tip.

## 2. Merges (in doc order, tested after each, pushed green only)

- `batch/B10` (34c1991, intel union + T190 unblock): merged cleanly
  apart from the expected `intel/src/lib.rs` union (B09 wiring on
  this side, `b10_brief` on theirs — resolved by union, both
  `pub mod` lines kept). Post-merge: **1401 passed, 0 failed**.
- `batch/B15` (78915ed, dashboard contract T245 + crewboard T237):
  merged with no conflicts. Post-merge: **1412 passed, 0 failed**.
- Pushed to main as 75d37d3 (`c31b277..75d37d3`), workspace green
  at push time.

## 3. App test suites (as observed, not expected)

- `npm test`: **1967 passed, 0 failed** (1858 ms). Matches the
  expected count exactly.
- `python3 -m unittest discover -s tests/queue-python`: **90 passed,
  0 failed** — AFTER an environment fix (below). Without it the run
  is 19 tests / 3 import errors.
- Environment fix (no repo change): `trio_store.py` imports
  `dynamic_credentials` from `/opt/muse/skills/custom-connector-setup/bin`,
  which does not exist on this Mac. Ran the suite with
  `PYTHONPATH=/tmp/queue-shim` pointing at a shim module whose three
  functions raise a clear "connector toolchain absent" error unless
  mocked. All 90 tests pass against the local SQLite fallback or
  with mocked credentials; nothing touched credentials. The shim
  lives in /tmp and is not committed.

## 4. Stack up (manual bring-up; script bug noted)

- `bash run-stack.sh` dies on this Mac at the agent check:
  `run-stack.sh: line 87: PIDS: bad array subscript` — the script
  uses bash-4 negative indices (`${PIDS[-1]}`); macOS ships
  bash 3.2.57. Environment issue, not a repo regression. Repo left
  untouched; stack started with the script's own commands instead.
- Up and verified: relay :8787 (`Meta Nuntius relay listening`,
  memory store), queue :8935 (local SQLite FALLBACK, honestly
  labeled — `TRIO_UPSTASH_HOST` is absent on this Mac, no value
  invented), resident agent running (idle, no jobs without Spark),
  app :8080 (`{"ok":true,"service":"meta-trio-assess",...}`,
  `model.configured=false`).
- `GET /api/crew/status` responds:
  `available:false, reason:"no crew records yet"`,
  `simulated_dispatch:true`. No crew records exist because no
  patrol has run (blocked on the key — see §5).
- Command view loads ("Meta Imperium — Visual Event Assessment
  Prototype"). 3D map does NOT render: the page falls back to
  "schematic pin grid" because the vendored
  `vendor/maplibre/maplibre-gl.js` is a 59-line loader stub with
  no `Map` implementation (CSS file is 0 bytes). CARTO endpoints
  are reachable from this Mac (tile URL returns 200), so the only
  blocker is the stub vendor file. Recorded, not fixed (vendored
  file belongs to Pax's commit; replacing it is out of scope).
- NYC DOT cameras: the app shows "Offline camera list — built-in
  subset" because the live list fetch fails in the browser. Root
  cause measured: `https://webcams.nyctmc.org/api/cameras` answers
  200 to curl (and a real AXIS JPEG snapshot downloads in 0.23 s),
  but sends no `Access-Control-Allow-Origin` header, so browser
  cross-origin fetch is blocked. A same-origin proxy would fix it;
  that is a feature change, out of scope — recorded as found.

## 5. Live patrol round trip: BLOCKED, not run

No `hackathon key.txt` anywhere on this machine (searched repo
root, home, Desktop, Documents, plus shallow find). Per the work
order I did not invent a key and did not substitute any other key
found on this Mac. Consequences:
- No guarded Spark call was made. Guardrail ledger total for my
  runs: **$0.00** (ledger file `server/queue/spark_guardrail_state.json`
  holds 4 zero-token, zero-cost entries timestamped 2026-10-31T01:29Z
  from before this run; my runs added no spend and no entries — the
  file is runtime state, untracked, and I did not commit it).
- No dispatch was attempted, real or simulated.
- Step 4's queue/assess liveness was still proven without Spark:
  live Rust assess server + stub queue over real HTTP returned
  HTTP 200 for a valid queued answer and HTTP 502 (logged fallback)
  for an invalid one; held-model path returns 503. (Proven during
  the B05 gap closure on the finish branch.)

## 6. Native app: FAILED to build (exact errors, fresh clone)

Separate clone `/tmp/meta-os-native` (depth 1, untouched).
`bash Scripts/make-app.sh` fails in `swift build`:

- `xcrun: error: unable to lookup item 'PlatformPath' from command line tools installation` (also for SDK path `MacOSX.sdk`)
- `AssessmentView.swift:191,194: error: 'foregroundStyle' is only available in macOS 14.0 or newer`
- `CameraPreviewView.swift:18,27: error: method must be declared fileprivate because its result/parameter uses a private type`
- cascading: `ContentView.swift:68: error: cannot find 'LogoColorPanel' in scope`
- Toolchain: Apple Swift 5.10, CLT at `/Library/Developer/CommandLineTools`, macOS product 27.0.1.

Pre-existing code/toolchain mismatch on a pristine clone —
independent of the Rust merges (no `native/` file was touched by
any fleet branch). No fix attempted (out of scope; would be a
native-code change).

## Still unverified (nothing below is claimed)

- Live patrol round trip + LOOP FEED + crew-data records (needs key).
- Guarded-spend increment on a real call (needs key).
- Native camera load + native live assessment (needs a build that compiles).
- 3D CARTO map with extrusions (needs the real maplibre vendor build).
- DOT live list in-app (needs same-origin proxy or CORS-enabled API).
- Real Upstash path (needs TRIO_UPSTASH_HOST; all queue runs here were labeled local fallback).
- Gate-1 recheck of B12a (Milo) and boss Mac gate-2 for merged batches beyond the workspace-green shown here.
