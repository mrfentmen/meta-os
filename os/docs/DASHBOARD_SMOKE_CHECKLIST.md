# Dashboard smoke checklist (DSH-029)

Run this list before **every** deploy of the viewer (DSH-027). It is
10 manual checks, in deploy order: the first two are cheap gates that
stop a bad build before anyone opens a browser, the rest are a
single pass over the live-shape viewer with fixture data (or the
live room when it is up). A check that fails stops the deploy: fix
it, re-run the whole list from check 1, and only then deploy.

Contract: `docs/DASHBOARD_SPEC.md`. Panel ids are the intelPanel
ids in `bus.html` / `index.html`; those two files are the same file
(DSH-026), so every check on one covers the other once check 1
passes.

## Check 1 — The two viewer files are identical

- How: `cmp bus.html index.html` (or `diff bus.html index.html`).
- Pass: no output, exit 0.
- Why: every dashboard change must reach both files; a drift here
  means half the audience sees the old build.

## Check 2 — The extracted intel script parses cleanly

- How: extract the intelPanel module (the code between the two
  `// === feature: intelPanel ===` markers) and run
  `node --check` on it; run the dashboard harness tests
  (`python3 -m unittest discover tests -p 'test_dashboard_*.py'`
  at minimum, full suite before a deploy).
- Pass: `node --check` clean, no new test failures against the
  baseline (see the spec §10 note for the known environmental
  failures — a third failure blocks the deploy).
- Why: a syntax break in the one static file breaks every panel at
  once, and the harness is the only pre-browser gate we have.

## Check 3 — All four intel panels render, plus the header strip

- How: open the viewer, connect, and confirm the panels aside shows
  Crew Board (`intel-crew`), Brief (`intel-brief`), Dispatch
  (`intel-dispatch`), and Alerts (`intel-alerts`), with the header
  strip (DSH-016) above them.
- Pass: all four panels present with content or their own empty
  state — never a blank aside, never a thrown panel. Header counts
  (agents online, jobs open/claimed/done today, critical alerts)
  match the fixture/room totals exactly.
- Why: a missing panel is the most common regression shape for a
  module edit, and the strip is the at-a-glance mission-control line.

## Check 4 — Crew Board: presence, jobs, and states agree

- How: with fixture crew data, confirm every fixture nick renders
  with status text, host from its nick claim, and a ticking
  last-seen age (DSH-003); an agent mid-job shows title, progress
  age, and a decreasing lease countdown (DSH-004); capability chips
  match the caps fixture exactly and stale agents render dimmed
  (DSH-005); idle, working, and blocked states are all visible
  where the fixture provides them (DSH-006).
- Pass: no nick missing, no age frozen, no chip invented, no state
  shown for the wrong reason (a blocked agent must be blocked by
  job/watchdog state, not by a missing record).
- Why: the crew board is the panel Del looks at first; a wrong
  state here misdirects the whole room.

## Check 5 — Brief: latest brief, history, and staleness read true

- How: confirm the latest brief renders all sections with
  `generated_at`, age, and a TEMPLATE marker when it is a fallback
  (DSH-007); open the history dropdown and confirm the last 7
  briefs with morning/onjoin/ondemand kind labels (DSH-008); a stale
  brief shows its age label, and long text collapses per section
  with Blocked open by default (DSH-031).
- Pass: sections, age, marker, and history all match the store
  records; nothing in the panel claims a fresh brief when the
  record is old.
- Why: a brief panel that hides staleness is worse than no brief
  panel — decisions get made on yesterday's picture.

## Check 6 — Dispatch: preview reads, approval never implies auto-post

- How: load the golden diamond plan preview and confirm jobs,
  files, dependency order, and budgets render readably (DSH-010);
  confirm the panel copy states a human approves every plan
  (DSP-040) and the approve button reads as a confirm step
  ("Post N jobs", native confirm) with posting gated behind the
  engine integration (DSH-011). The posted-plan tracker, where a
  plan was posted, lists real job ids with live status (DSH-012).
- Pass: preview matches the plan payload exactly; no copy, label,
  or button state suggests a plan posts itself. In the mock, approve
  posts nothing.
- Why: this is the safety-critical panel — an implied auto-post is
  a spec §0 violation, not a cosmetic bug.

## Check 7 — Alerts: severity, lifecycle, and the quiet state

- How: confirm the feed renders all fixture alerts newest first
  with severity as color **and** text label plus kind, subjects,
  age, explanation, and suggested fix (DSH-013, DSH-019);
  acknowledge and resolve a fixture alert and confirm it
  re-renders in its new state, with live writes still gated off
  per spec §0 until Del's gate flips (DSH-014); with no open alerts
  confirm the empty state reads "All quiet — watchdog alive, last
  tick HH:MM:SS", and with a stale beat confirm the red
  "watchdog silent" state instead (DSH-015).
- Pass: severity is never color alone; lifecycle transitions stick
  in the render; the quiet state names a real last tick, and the
  silent state is unmistakable.
- Why: an alert panel that cries wolf, or stays quiet when the
  watchdog died, fails its entire purpose.

## Check 8 — Demo mode and deep links behave

- How: open `?demo=1` and confirm enlarged type, token/setup chrome
  hidden, and all four panels pinned open, while a normal URL is
  unchanged (DSH-028). Then open `#intel/brief/<id>` and
  `#intel/alert/<id>` and confirm each scrolls to and highlights
  its item, including a brief Watch item landing on its alert card
  (DSH-022).
- Pass: demo on/off is exact (`?demo=10` is not demo mode); both
  hash routes land on the right card and nowhere else.
- Why: demo mode is the presentation surface and deep links are how
  a brief hands the reader to an alert — both are judged live.

## Check 9 — Phone width and accessibility hold up

- How: narrow the viewer to 390px and confirm panels stack with no
  horizontal scroll, the dispatch box stays usable one-handed, and
  tap targets are >= 40px (DSH-017); confirm every alert still
  carries its text severity label at this width and buttons are
  labeled (DSH-019); confirm all new UI uses only the fixed
  GitHub-dark palette (DSH-018).
- Pass: no horizontal scroll, no tap target under 40px, no severity
  carried by color alone, no off-palette hex in new CSS.
- Why: the demo may be presented from a phone, and a panel that
  only works on a desktop is a panel that fails at demo time.

## Check 10 — Failures stay local, reads stay read-only, no new timers

- How: with one data source killed (or a rejected token), confirm
  only its panel degrades with a plain message while the other
  panels keep their last good render (DSH-021); with a read-only
  token pasted, confirm all panels still render and writes degrade
  to disabled buttons with an explanation (DSH-033); confirm the
  intel module adds no interval or timeout of its own — polling
  still rides the core 2s cycle (DSH-020). A quick automated proxy:
  the intelPanel module contains no `setInterval`/`setTimeout`.
- Pass: no panel throws, no panel's failure takes another panel
  down, no write path fires from viewer code, no new timer.
- Why: a dashboard that falls over as a unit, or that writes to
  the bus from a viewer's click, is a liability in the live room.

## Run procedure

1. Run checks 1–2 from the repo root (no browser needed).
2. Run checks 3–10 in the viewer, in order, against fixture data
   first; repeat against the live room when it is available.
3. Log the run below: date, commit, each check's pass/fail, and
   the deploy it gated (or "no deploy" when the deploy step itself
   is blocked — the checklist run still stands as the pre-deploy
   gate for that commit).
4. Any fail: stop, fix, re-run from check 1. Never deploy past a
   failed check, and never log a check as passed that was not run.

## Run log

- 2026-10-27 (pre-deploy run, commit 73d60e9 + this checklist):
  checks 1–2 automated (cmp clean; node --check clean; dashboard
  harness + full suite run, see the DSH-029 commit message for the
  suite tally); checks 3–10 verified against the shipped code and
  harness fixtures — panel ids, crew/brief/dispatch/alert renders,
  demo mode, deep links, mobile CSS, error isolation, and the
  no-new-timer rule are all covered by the dashboard harness tests
  named in the spec. Browser-viewport steps (390px scroll, tap
  targets, hash scroll) were NOT run in a live browser on this run:
  this VM run has no browser viewport check, so those sub-steps are
  recorded as harness-covered, not browser-verified. Deploy step:
  NOT RUN — DSH-027 remains blocked (no deploy route from this VM),
  so this run gates the commit, not a live deploy.
