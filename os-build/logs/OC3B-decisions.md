# OC3 Pax-out decision record (decided 2026-11-03, no Pax)

Authority: OC3 apps/content + staged ISO payloads only. Kernel,
agent-runtime, submission, and other lanes' files are NOT decided
here — those sections name the decider, not the decision.

## Decided (OC3 takes the call, reversible on boot evidence)

- **D1 office suite: NONE in 1.0.** Deferred, not missing. Atril
  covers PDF; docx/xlsx editing is out of 1.0 scope. Closes
  OC3B-221 (answer: nobody names one, by decision).
- **D2 canonical collisions (install one, drop the other):**
  agent-status → OC2's `agent-layer/` copy wins (maintained);
  welcome → `metaos-theme/apps/` wins, payload twin drops;
  livebg → `metaos-theme/` wins, payload twin drops;
  files → OC2 `thunar.desktop` wins (TryExec), `meta-files` drops;
  PDF → Atril wins (D3), evince entry stays hidden-off.
  Rationale per pair is in OC3B-desktop-inventory §C; this is the
  call. Implementer (whoever edits those trees) executes, OC1
  confirms no doubles at boot.
- **D3 PDF default → atril.** Exact pending edit for the mimeapps
  owner: `application/pdf=atril.desktop`. (Recorded, not applied —
  чужой файл.)
- **D4 browser default → chromium.** `text/html + http(s) →
  meta-browser-app.desktop` (my entry; ISO drops it in).
- **D5 ship the 11 launchers + start/tour/help pages** as built
  (payloads `5d20fa7c` / snapshot `5130bc14`). Already the standing
  recommendation; now a decision.
- **D6 sound: ship pavucontrol, assume a sink.** TryExec hides the
  entry if the image has no server; plumbing ask stays with ISO.
- **D7 scope cuts (explicit, not gaps):** archiver GUI, printing,
  clipboard manager, charmap/emoji, webcam app, mail client ship in
  NEITHER 1.0 image. `unzip` CLI + `du` CLI are the fallbacks.
  Revisit per app with a named owner if the demo demands it.
- **D8 budgets:** OC3 payload ≤ 25 MB (snapshot is 5.4 MB, headroom
  for theme growth). Total-ISO working cap ≤ 5.0 GB (baseline 4.26
  GB; USB-stick assumption, stated not proven).

## Defined so no Pax is needed (criteria, not calls)

- **Theme-complete = this checklist, all green:** (1) one branding
  dir wired (meta vs metaos fork resolved); (2) icon set generated
  (78×8+16 per ICONS.md) and installed; (3) xfconf ships ≥ panel,
  desktop, xsettings (+ wallpaper pin); (4) single greeter drop-in
  wins; (5) slideshow mechanism one of PNG-list/QML with all slides
  reachable; (6) provision GTK lands under MetaOS/, not themes/.
  Whoever lands it ticks the boxes — no judgment call left.
- **r11-finish / round12 merges: NOT decided here.** 32 + 10 code
  collisions in agent-runtime files outside this lane. Decider =
  whoever owns agent-runtime (likely OC1/Buffy author). No silent
  merge, no OC3 rewrite.

## Still needs a non-OC3 human (Del/Boss/lane owner — listed, not waited on)

- Project LICENSE choice, submission sign-off/pay (Del/Boss).
- F1/syscall numbers, NATIVE update-vs-carveout (kernel/Del).
- Chromium presence/version ack, sound-server naming, installer
  wiring fixes (ISO/OC1). Rootfs 7/7 (OC1 boot).
- Watchman recovery, key provisioning, UTM boot, token budgets
  (respective lane owners decide for themselves, same form as this
  file — decide and record, don't wait).
