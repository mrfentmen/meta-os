# DSH-030 — dashboard screenshot set for submission

Eight shots: four scenes × two sizes. Desktop = 1280px viewport (the
panel renders at its real 330px sidebar width); phone = 390px viewport
(the panel renders full-width, per the DSH-017 mobile pass).

| Shot | What it shows |
| --- | --- |
| `crew-board-desktop.png` / `crew-board-phone.png` | Crew Board, busy: header strip (3 agents online, 1 open / 1 claimed job), milo working job 1 with capability chips, pax and rowan idle with chips. The header strip belongs to this scene only. |
| `brief-panel-desktop.png` / `brief-panel-phone.png` | Brief panel: fresh morning brief, TEMPLATE marker, 15 min old, all sections (Decisions, In flight, Owners, Blocked and why, Watch items), "Brief me now" disabled with the posting-off note. |
| `dispatch-preview-desktop.png` / `dispatch-preview-phone.png` | Dispatch panel: goal filled in, 5-job plan preview in posting order (module, panel, tests, docs, review) with files and budgets, "A human approves every plan", Post 5 jobs disabled, Reject plan, posting-off note. |
| `alerts-firing-desktop.png` / `alerts-firing-phone.png` | Alerts panel firing: all 5 critical alerts from the dev pack (presence-stall, three file-collisions, dead-dep) with severity, subjects, age, explanation, suggested fix, and Acknowledge/Resolve buttons. |

## What these shots are, honestly

These are **fixture renders, not live bus traffic**. Each shot renders the
real intelPanel module and the real stylesheet, copied verbatim out of
`bus.html` at this commit, fed through the module's own `__busTest`
setters from Pax's DSH-037 static payload dev pack (`intel/devpack/`):
payloads built by the real producers (brief generator, dispatch plan
reducer, watchdog tick, jobs/presence/caps) on fixtures, pinned by
`tests/test_intel_devpack.py`. No live Redis, no Spark call, no bus
post — the viewer posting gates stay off, exactly as shipped, and every
disabled button in the shots is disabled in the shipped viewer too.

Clocks are the dev pack's frozen clocks, not wall-clock now: the crew
scene renders at the pack build instant (presence beats were live
then, so rows read "seen now", lease 30:00), while the brief and
alerts scenes render at the pack's as-of so the fresh brief shows its
pinned 15-minute age. The brief's rendered date (10/27/2026) is the
fixture clock in the renderer's timezone, not the day the shot was
taken — the shot date is the commit date of this set.

Phone shots use a taller emulated viewport than a real phone so the
full panel fits in one still: in the real viewer at 390px the panels
region scrolls at 38vh, so a phone user sees the same panel by
scrolling. Panel width, type sizes, tap targets, and wrapping are the
real 390px rendering; only the window height is taller. Demo mode
(`?demo=1`) is on in every shot: enlarged type, panels pinned open.

## Regeneration

The harness (page builder + headless-Chrome element screenshots) is
not checked in — it was a one-off build script. To regenerate: extract
the `<style>` block and the `intelPanel` module from `bus.html`, stub
`busUtil`/`busHooks` with a real-DOM `panel()`, feed the dev-pack
payloads above through `__busTest.intelPanel`, and screenshot each
`panel-intel-*` element at 1280px and 390px. `tests/test_dashboard_
screenshots.py` pins this set: all eight files present, valid PNGs,
and the module still rendering the same dev-pack counts (crew 3,
brief template, plan 5 jobs, alerts 5 critical).
