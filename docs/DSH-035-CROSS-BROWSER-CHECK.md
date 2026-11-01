# DSH-035 cross-browser check — 2026-10-27

Task: dashboard in Chrome + Safari (iOS), all four panels.
Acceptance: check results logged; any Safari-only bug filed as its own
task before demo freeze.

## Method

Headless render of the repo's `bus.html` (this commit) with the
DSH-037 dev-pack fixtures fed through the `__busTest.intelPanel`
hook (same fixture set as the DSH-030 screenshot pins: crew 3 /
brief morning-template / plan-ready / 5 alerts). Four runs:

| Engine | Viewport | Result |
|---|---|---|
| Chromium (Playwright, cached build) | 1280x900 | PASS |
| Chromium (Playwright, cached build) | 390x844 (phone) | PASS |
| WebKit (Playwright, Safari engine) | 1280x900 | PASS |
| WebKit (Playwright, Safari engine) | 390x844 (phone) | PASS |

Each run asserted: zero uncaught page errors (see the one
WebKit note below), crew nicks / brief kind / plan job titles /
alert kinds all present in the rendered panels, snapshot counts
(crew 3, jobs 3, caps 3, brief morning, plan-ready, alerts 5,
header agents-online 3 / critical-alerts 5), and no horizontal
overflow (`scrollWidth <= innerWidth`) at both widths.

## Caveat, stated plainly

No physical iOS device or macOS Safari was available on this VM,
so the Safari leg ran Playwright's WebKit build (the Safari
engine) on Linux, not Safari on iOS. That covers engine-level
rendering differences (layout, JS, CSS) but not iOS-specific
behavior (viewport chrome, touch, PWA install). A final check on
the actual demo device remains open for INT-030 (verify demo mode
on Dale's presentation machine/browser).

## Verdict

No Safari-only bug found; nothing to file before demo freeze.

## One observation (not a Safari-only bug, not filed as one)

WebKit's console reported one error in all WebKit runs:
`Not allowed to load local resource: file:///manifest.webmanifest`.
Cause: `bus.html` links `/manifest.webmanifest`, but no such
file exists in the repo, and the check loaded the page via
`file://`. It is engine-independent (a 404 on any host, not a
Safari quirk) and outside this check's scope; a follow-up task
may either ship a manifest or drop the link. Panels were
unaffected in both engines.

## Evidence

Screenshots and the raw results JSON from this run live in the
goal workspace's `hidden_files/dsh035/` (four PNGs, one per
engine x viewport, plus `dsh035-results.json`); they are run
evidence, not submission assets, so they are not committed to
the repo. The check driver (`/tmp/dsh035/check.js`) is
throwaway; the durable pin is `tests/test_dashboard_cross_browser.py`,
which asserts this log names all four runs with PASS verdicts
and records the no-Safari-only-bug verdict.
