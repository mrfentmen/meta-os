# UI fix report — HN-025 (branch hana/ui-wave-2)

One page: what was dead, what each fix does, what remains gated
and why. Detail lives in `docs/UI_CONTROL_SWEEP.md` (HN-020) and
`docs/UI_SCREENSHOT_PACK.md` (HN-021).

## What was dead

First, the audit surface itself: Pax's audit (dead buttons,
hollow plan panel, harness Alerts, credential-form first screen,
muse-relay title) describes the old Python-era dashboard
`meta-os/bus.html`, NOT this app — no bus.html, no #intel-post /
#intel-plan here. That surface was not touched; it needs its own
lane call with del's decisions (see gated items). What WAS dead
or missing in this app, found by this wave:

- No live incident line above the loop feed (HN-011).
- Audit panels with undesigned or missing empty states (HN-012).
- Async panels with no loading state past 300 ms (HN-013).
- Loop-feed failures with no retry and no real error class (HN-014).
- Keyboard features invisible — no visible controls, no help (HN-015).
- No 390 px pass: wall, targets, and side scroll unruled (HN-016).
- Wall auto-cycling and (verified) ASCII spin un-gated for
  reduced motion (HN-017).
- Text pairs short of WCAG AA (HN-018).
- Focus traps: search close stranded focus, pin card never took
  focus, help never returned it (HN-019).
- No control inventory with evidence (HN-020).
- No screenshot record of the changed surfaces (HN-021).
- Demo mode inert: no `?demo=1` handling anywhere (HN-022).
- Reload lost the incident view; nothing restored it (HN-023).
- Timestamps named no zone; the clock said only "LOCAL" (HN-024).

## What each fix does

- **HN-011** Live ribbon above the loop feed, from the same crew
  payload the feed renders — newest incident, tier-colored, never
  a placeholder. Tests incl. a staged-record proof.
- **HN-012** Designed empty states for all six audit panels, with
  a shared `.empty-state` marker. Two sentences deliberately
  untouched (history, latest assessment) — pinned by tests for
  native parity.
- **HN-013** Loading states past 300 ms on the two on-load polling
  panels (cameras, loop feed); fires/assessment already surface
  in-flight states.
- **HN-014** Loop-feed error row with Retry and the real error
  class (network/http/invalid/unknown), proven by a live kill test
  (server closed mid-session, fetch rejects, maps to network).
- **HN-015** Visible Search + Keyboard-shortcuts buttons and a
  help overlay listing the view's only three shortcuts.
- **HN-016** 390 px pass by rule: wall stacks, 44 px targets, no
  side scroll (480 px breakpoint). No browser runs in the
  sandbox — a real-device check is still owed (see gated).
- **HN-017** Reduced motion stops wall auto-cycling; ASCII spin
  was already gated and is now pinned by test. Live-data polling
  intentionally not gated.
- **HN-018** Contrast measured for every text pair; short text
  colors fixed to lighter same-hue variants. Brand hexes and
  gradients untouched (pinned by tests).
- **HN-019** Keyboard walk follows visual order; search, help,
  and pin card take focus on open and return it on close; no
  positive tabindex anywhere.
- **HN-020** Control sweep from the live UI: 59 static + 6 dynamic
  templates + 27 disclosures + 2 links, all WORKS, dead count 0;
  8 audit-only items REMOVED with reasons. Pax's `UI_AUDIT.md`
  is not on this VM, so the audit's 79 count is not re-verified
  1:1 — stated plainly in the sweep.
- **HN-021** Screenshot pack filed as blocked-with-plan: no
  headless browser in the sandbox, so no captures exist and none
  are claimed; shot list for all 6 surfaces + a Mac capture
  script are filed for the gate run.
- **HN-022** `?demo=1` shows a persistent sticky demo-data banner
  in both views; only the exact flag counts.
- **HN-023** Reload restores the incident view from records: the
  saved pointer is validated against the loaded cameras and the
  fresh crew incidents, crew record wins, unknown camera restores
  nothing.
- **HN-024** Every timestamp names its zone (EST/EDT/…); the
  console clock's bare "LOCAL" is replaced by the real zone,
  recomputed each tick across DST.
- **HN-025** This report.

## What remains gated and why

- **Merge to main** — needs the boss's word. This branch is
  unmerged by design; nothing here ships until he says so.
- **HN-001…004, HN-008…010 (repo question)** — those controls
  live only in `meta-os/bus.html`. Two are held by standing
  decisions (GOV-002 brief hold; viewer-posting decision) and
  pinned tests assert the disabled states. Needs del's lane call.
- **Ignis gradient brand call** — the badge/primary gradient's
  light end (#e54848) with white text measures 3.93, short of AA,
  and no single text color passes both gradient ends. The
  gradient is pinned by tests; changing it is a brand decision,
  not a silent edit.
- **Real-device 390 px check (HN-016)** — rule-verified only;
  a phone render is owed at gate.
- **Screenshot captures (HN-021)** — shot list + script filed;
  captures themselves need a Mac run with Chrome.
- **Milo gate-1** — invited after push; the branch is unpushed
  until the full suite runs green (see below).
