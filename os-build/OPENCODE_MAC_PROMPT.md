# OPENCODE_MAC_PROMPT.md — Mac run: gate 2, merges, live verification

**By the boss's direct order (Del / Mrfentmen, 2026-10-30).** You are
OpenCode running on the boss's Mac. This file is your complete work order
for this run. Work autonomously until it is done or blocked. Do not stop
to ask questions: make the smallest reasonable decision, note it in the
final report, and keep going. If one step fails twice with genuine
attempts, stop that step, write the exact failure in the report, and move
to the next step. Never loop on a broken approach.

This file covers the Mac run only. `OPENCODE_PROMPT.md` (the B27/B31
fleet takeover) is a separate order and still stands; this file does not
cancel it.

Context: this repo is the hackathon submission (Meta Global AI Developer
Hackathon, submission due Wed Nov 4, 9:00 PM ET). Meta OS is the
platform; Meta Imperium is the flagship system on it (divisions: Vigiles,
Ignis, Medicus). The Python/Node stack in this repo is the working demo
stack. `crates/` is the Rust port of the OS, verified so far only at
gate 1 (a crew VM). Your Mac is gate 2 — the final compile authority.

## The API key — read this first

There is a file on this Mac named **`hackathon key.txt`**. It contains
the Meta Model API (Muse Spark) key. Find it: check the repo root, the
home directory, `~/Desktop`, and `~/Documents`. Read it, trim whitespace,
and use the value as the `SPARK_API_KEY` environment variable for the
stack runs below.

Hard rules for the key:

- NEVER print it, echo it, log it, screenshot it, or write it into any
  file, commit, report, or message. Refer to it only as "the key file".
- NEVER commit it. Before every commit, run `git status` and confirm
  `hackathon key.txt` is not staged and not listed as an untracked file
  that could be added by `git add -A` / `git add .` — add files by name,
  never with a blanket add.
- If the key file sits inside the repo folder, add the exact line
  `hackathon key.txt` to `.gitignore` early in this run and include that
  `.gitignore` change in your first commit.
- If you cannot find the key file: do all the work that does not need
  Spark (steps 1–3 and 6), mark the live Spark steps BLOCKED in the
  report with "key file not found", and finish. Do not invent a key and
  do not use any other key you might find on this machine.

## Budget

Spark spend is capped: a guardrail in this repo enforces a **$75 test
cap** (shared ledger `server/queue/spark_guardrail_state.json`, enforced
by both `server/queue/spark_guardrail.py` and `server/budget.mjs`). The
ledger file is runtime state — never commit it. If the guardrail refuses
a call, stop spending, say so in the report, and finish the non-spend
work. Keep the live verification in step 5 minimal: one full round trip
proven is enough; do not run the patrol for hours.

`TRIO_UPSTASH_HOST`: use it if it is already present in the environment
or in existing local config on this Mac. If it is absent, run anyway —
the queue falls back to local SQLite — and label every affected result
"local fallback, not Upstash" in the report. Never invent a hostname.

## Work order

### 0. Sync

`git pull` main. Expected tip is e8b83dfe or later (the orchestrator +
supervisor + P0 commit). If the pull conflicts or fails, stop and put
the exact error in the report.

### 1. Gate 2 — the Rust workspace

Run `cargo build --workspace`, then `cargo test --workspace`. Fix
compile and test failures with the smallest change that works. The Rust
code is a port: the Python/Node originals are the spec — port behavior,
never redesign, and leave the originals untouched.

Known item: `parity-tests` has a known `fake_redis` `lrem_semantics`
stack overflow. If it reproduces, fix the harness so the test runs
(e.g. run that case on a thread with a larger stack) **without changing
what the test asserts**; if you cannot, document the exact failure.

Your workspace run also settles an open dispute: B31's parity harness
was reported RED (E0119) on its branch and clean on the integration
branch. Report plainly which state is real on main.

### 2. Merge the two gate-1-green branches

Two branches hold slices that passed gate 1 but are NOT in main yet.
Merge them one at a time, in this order:

1. `batch/B10` (tip 34c1991) — intel union; gate 1: `cargo test -p intel`
   108 passed, 0 failed.
2. `batch/B15` (tip 78915ed) — dashboard; gate 1: 82 tests passed.

After each merge, run `cargo test --workspace`. Push main only when the
workspace is green, apart from a documented known failure from step 1.
If a merge produces failures you cannot fix after two genuine attempts,
leave that branch unmerged, do not force anything, and put the exact
failure in the report.

### 3. App test suites

Run the repo's JS suite (`npm test` — expect roughly 1967 passing) and
the Python queue suite (expect 90 passing). Report the exact counts you
observed, not the expected ones. Fix environment problems (missing deps,
wrong runtime) yourself; fix code only if a failure is a real regression
from steps 1–2.

### 4. Bring the stack up

Export `SPARK_API_KEY` (from the key file) and `TRIO_UPSTASH_HOST` if
available, then run `bash run-stack.sh` (the script has no executable
bit; invoke it through bash). Verify:

- The app answers on port 8080.
- The Command view loads and the 3D map actually renders (CARTO tiles +
  extruded buildings visible) — you are on a normal network, so this
  must really load, not the offline degradation.
- NYC DOT camera snapshots load in the app.
- `GET /api/crew/status` responds.

### 5. Live patrol round trip — the critical verification

With the stack up, start the patrol and prove ONE full live round trip:

1. A real camera snapshot is fetched.
2. It goes through the queue as a `trio-assessment` job.
3. A guarded Spark call answers (guardrail ledger increments by a small
   amount; confirm the ledger total afterwards).
4. The answer passes validation and comes back.
5. Patrol / review / orchestrator events appear in the LOOP FEED and in
   the records under `server/queue/crew-data/`.

If a dispatch happens, it must go ONLY to the loopback simulated
endpoint (`/dispatch-simulated`) and return a `sim-` receipt. **Never
repoint dispatch at any real endpoint, and never contact any real
emergency service — no configuration change may change this.** Once one
round trip is proven, stop the patrol.

### 6. Native app

In a SEPARATE clone of the repo: `cd native && bash Scripts/make-app.sh`,
then open the built MetaTrio.app. Verify the camera loads and one live
assessment round trip works. If it fails, capture the exact error text
for the report.

### 7. Report

Write `MAC_RUN_REPORT.md` in the repo root, commit it, and push. Cover:

- Gate 2: build result and exact test counts; which B31 state was real.
- B10 / B15 merges: merged or not, and the post-merge test counts.
- JS and Python suite counts as observed.
- Stack + live patrol: VERIFIED, or exactly what failed and where.
- Native app: VERIFIED, or the exact error.
- Guardrail ledger: total spend observed after your runs.
- A final "still unverified" list — anything you did not actually prove.

Label claims honestly: VERIFIED only for what you ran and saw.
CODE-INSPECTED for what you only read. Never present a mock, a stub, or
an expectation as a result.

## Standing rules

- Push verified work straight to main. Never force-push.
- Never commit: the key file, any `.env`, the guardrail ledger,
  `server/queue/crew-data/`, or any secret of any kind.
- Never delete or rewrite the Python/Node fallback stack.
- Medicus is EMS scene awareness only — no diagnosis, cause, severity,
  or treatment language anywhere you write.
- Observation language only in anything incident-shaped: no claims of
  criminal intent, guilt, or legal violations; no face recognition or
  identity tracking.
