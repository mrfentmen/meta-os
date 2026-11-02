# UI control sweep — HN-020 (branch hana/ui-wave-2)

Re-run of the audit's control inventory against the fixed build.
Every control is marked WORKS or REMOVED with evidence.

## Method note — read this first

Pax's `UI_AUDIT.md` is NOT on this VM, so the audit's 79-control
count cannot be re-verified 1:1. This inventory is built from the
live UI itself: every static control enumerated from `index.html`
(button / input / select tags), every dynamic control from the JS
that creates it, every disclosure from its `<summary>`, and every
link from its `href` target. Wiring evidence is the listener or
read site in `js/` for that control. A control counts as WORKS
when its listener, read site, or native behavior exists in this
build — not when it merely renders.

## Counts

- 51 static controls: 35 buttons + 14 inputs + 2 selects — all WORKS.
- 6 dynamic control templates (rendered per item) — all WORKS.
- 27 native disclosures — all WORKS (native `<details>` behavior).
- 2 studio links (same target) — WORKS.
- 8 audit items REMOVED: absent from this repo's UI; they live
  only in `meta-os/bus.html` (see below).
- Dead count in this repo's live UI: 0.

## Static buttons (35) — all WORKS

Command view (`js/command-map.js` listeners unless noted):

| Control | Evidence |
| --- | --- |
| btn-view-command, btn-view-console | view-switch listeners |
| cmd-ai-focus | click listener, AI Focus (HN-005) |
| cmd-layer-fires, cmd-layer-radar | layer toggle listeners |
| cmd-watch-toggle, cmd-assess-now, cmd-sample-toggle, cmd-mark-reviewed | inspector listeners |
| cmd-pin-card-watch, cmd-pin-card-focus, cmd-pin-card-close | pin-card listeners |
| cmd-search-open, cmd-help-open, cmd-help-close | search/help listeners (HN-015) |
| cmd-product-chip ×3 (vigiles/ignis/medicus) | data-cmd-product group listener |
| cmd-mode-btn ×3 (city/tactical/incident) | data-cmd-mode group listener |

Console view (`js/app.js` listeners unless noted):

| Control | Evidence |
| --- | --- |
| btn-camera-start, btn-camera-stop | camera listeners |
| btn-analysis-start, btn-analysis-stop | analysis listeners |
| btn-reset | reset listener |
| btn-image-assess, btn-image-clear | still-image listeners |
| btn-video-assess, btn-video-clear | video listeners |
| btn-backend-check | backend health listener (reads endpoint input) |
| btn-export-log, btn-clear-log | log listeners |
| btn-contact-add | contacts listener (reads name/role/org) |
| logo-pause | `js/logo-animation.js` pause listener |

## Static inputs (14) — all WORKS

| Control | Evidence |
| --- | --- |
| cmd-search | input listener, filters camera list |
| cmd-ksearch | input + Enter listeners, search overlay |
| camera-facing (select) | change listener, restarts stream |
| scenario-select (select) | populated + read on submit |
| scenario-label | read on submit (overrides select) |
| endpoint | read on backend check |
| interval-seconds | read by sampler |
| image-input, video-input | change listeners, file inputs |
| logo-speed | `js/logo-animation.js` slider listener |
| contact-name, contact-role, contact-org | read by contacts add |
| product radio ×3 (vigiles/ignis/medicus) | change listeners, product switch |

## Dynamic control templates (6) — all WORKS

| Template | Evidence |
| --- | --- |
| Camera rows (`cmd-cam-row`, one per listed camera) | `renderList`, click selects camera |
| Alert rows (`cmd-alert` + `cmd-alert-track`, one per queue entry; `cmd-alert-handoff` when a handoff exists) | `renderAlerts`, click selects + marks seen |
| Search results (`cmd-kresult`, one per match) | `renderKResults`, click runs the result action |
| Wall tiles (`cmd-tile`, one per watched camera) | `renderWall`, click selects camera |
| Map markers (one per camera, role=button) | `createMarkerElement`, click opens pin card |
| MapLibre navigation control | library control inside the map container |

## Disclosures (27) — all WORKS (native behavior)

21 Ignis panels carry an "About this panel" disclosure each, plus:
About camera facing, About the logo, About this input ×2 (still
image, prerecorded video), About & limitations (product panel),
Full session statistics (session log). Native `<details>` needs
no JS; each opens and closes.

## Links (2) — WORKS

Both `.logo-studio-link` anchors point at
`design/meta-ascii-logo-studio.html`, which exists in this repo.

## REMOVED — audit items absent from this repo's UI (8)

These were audited on the old Python-era dashboard
`meta-os/bus.html`, not on this app. Grep-verified absent here
(no such id, label, or panel in `index.html` / `js/`):

| Audit item | Why removed here |
| --- | --- |
| Brief me now (BRIEF_ME_NOW_ENABLED=false) | Absent here = legit per the task rule. On bus.html it is held by the GOV-002 brief hold — needs the boss's call, not a flip. |
| Post N jobs #intel-post (DISPATCH_POST_ENABLED=false) | Absent here. On bus.html the decided disposition is REMOVE-as-a-posting-button per DSH-038, but its pinned test asserts disabled — needs a lane that updates spec + tests. |
| Alert Acknowledge (ALERT_WRITE_ENABLED=false) | Absent here. On bus.html gated by spec §0 until the boss's viewer-posting decision. |
| Alert Resolve (ALERT_WRITE_ENABLED=false) | Same as Acknowledge. |
| #intel-plan (hollow) | No plan panel exists here to connect or scope out. |
| Intel Alerts panel (harness-fed) | No intel Alerts panel exists here; the console's `cmd-alerts` is the incident queue, a different surface. |
| Credential-form first screen | No credential form exists here; first screen is the command map view. |
| muse-relay title/branding | Branding here is already Meta Imperium (HN-006); the muse-relay title lives on bus.html. |

## What this sweep does NOT claim

- It does not reproduce Pax's 79 count: without `UI_AUDIT.md`
  on this VM, the mapping from his 79 to these 94 live items
  cannot be checked line by line.
- Mobile 390 px and real-device behavior are rule-verified
  (HN-016), not device-proven; that check stays owed at gate.
- The 8 REMOVED items still need the boss's lane call for the
  `meta-os/bus.html` surface (HN-001…004, HN-008…010 territory).
