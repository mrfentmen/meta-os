# HANA — OS BUILD-OUT (boss order 2026-11-02 02:22 EST)

Your lane: everything the user sees and reads. Shell, apps
surface, the face's design system, site, demo. Work top-down;
DEMO_SCRIPT (H-FP1, due 03:00) still outranks everything here.
Freeze rules unchanged. Each task: done = artifact on your branch
+ one line to room 1.

## A. Demo (tonight, first)
A1 DEMO_SCRIPT.md by 03:00 (claim order, printable facts only).
A2 Shot list companion: every script beat → the exact screen/log.
A3 Fallback card: claim-order beats if a live step fails on camera.
A4 On-screen text set: every caption in the film, spelled, checked.
A5 Receipt close-up spec: which receipt fields the camera shows.
A6 Demo rehearsal notes after OpenCode's capture: what to re-shoot.

## B. Shell spec — close every gap
B1 clear paragraph (owed since RW4-2) into shell-spec.md.
B2 Boot-to-shell transcript spec: every line the console prints.
B3 status fields: spec each KEY, its source, its honest range.
B4 mem fields: same treatment. B5 ps fields: same.
B6 uptime edge cases: wrap, zero, pre-tick. B7 help surface final.
B8 Unknown-command behaviour spec. B9 Long-line behaviour spec.
B10 Keyboard map spec: backspace, shift, caps, symbols (RW4-1 R-2).
B11 Readkey behaviour spec (what the program prints, empty case).
B12 Attract entry/exit spec vs ATTRACT_SCREEN.md — reconcile.
B13 Error text canon: every kernel/shell message, one voice.
B14 Spec test per B-item in tests/os-shell-formats (extend 7/7).

## C. Face design system (feeds OpenCode's face build + Pax's page)
C1 Tokens: blues, whites, blacks — exact hex set, light + dark.
C2 Type scale for bar, dock labels, window titles, body.
C3 Window chrome spec: radius, shadow, title bar, buttons.
C4 Dock spec: size, spacing, magnification curve, label style.
C5 Top bar spec: zones, clock format, status icon set.
C6 Glass card spec (login): blur, border, shadow, avatar size.
C7 Icon style guide: stroke, weight, grid for all app icons.
C8 Icons drawn as specs for: Chrome, Terminal, Files, Dashboard,
   Editor, Notes, Calendar, Calculator, Settings, Trash.
C9 System marks check: the 8 approved marks at dock size, legible.
C10 Wallpaper picker spec: grid, live preview, apply behaviour.
C11 Settings layout spec: sections, order, control types.
C12 Boot screen spec: line order, progress bar behaviour.
C13 Login spec: states (idle, typing, wrong password, entering).
C14 Desktop menu spec (right-click): items, order, actions.
C15 Motion spec: window open/close/minimise timing + easing.
C16 Focus + keyboard spec for the whole face.
C17 Empty states: Files empty folder, Notes none, Trash empty,
   Board no rooms, Calendar no events — words + layout each.
C18 Error states: app failed to open, network down, updater
   failed — words + layout each.
C19 Light mode full pass: every screen re-checked in light.
C20 Dark mode full pass: every screen re-checked in dark.

## D. App surface specs (one per app; states + copy + keys)
D1 Terminal window spec. D2 Dashboard cards spec (4 cards).
D3 Files spec. D4 Editor spec. D5 Notes spec. D6 Calendar spec.
D7 Calculator spec. D8 Settings sections spec (6 sections).
D9 Trash spec. D10 Board window spec (rooms, post, scroll).
D11 Imperium home spec (3 services, entry states).
D12 Vigiles view spec. D13 Ignis view spec. D14 Medicus view spec.
D15 Science Lab view spec. D16 Musica view spec.
D17 Custos view spec. D18 Officina view spec.
D19 SIMULATED label placement canon across all system views.
D20 UNCONFIRMED / held states wording canon.

## E. Site (meta-os.pages.dev)
E1 Copy pass vs the claim sentence (HN4-3). E2 Face section: the
   approved mocks + the honest "building now" status line.
E3 Download section: image link + hash + JOIN steps in plain words.
E4 Proof section: boot logs + soak + gate, linked, dated.
E5 Systems section refresh: Imperium/Science/Musica/Custos/Officina.
E6 Kernel section: what the bare-metal core is, in plain words.
E7 FAQ: "is it a real OS", "what runs today", "what is simulated".
E8 Footer honesty line: built for the Meta hackathon, dates.
E9 Mobile pass: every section readable on a phone.
E10 Deploy check: Pax redeploys; you verify live bytes vs repo.

## F. Native tests + audit items (boss-decision packets)
F1 HN4-5 packet refresh: the 38 UPDATE patches as one review doc.
F2 The 18 CARVE-OUT cases: each with the reason it cannot update.
F3 Audit test (ui-fix-list): keep current vs latest main; report.
F4 21 stale bus/index tests: one-page decision packet for the boss.
F5 Native slim speed/pause panel: spec + decision packet.

## G. Words for the submission
G1 README top section rewrite draft (OS-first, claim sentence).
G2 Devpost description draft (printable facts only).
G3 "What we built" bullet set, each bullet traceable to a log.
G4 "What's simulated" bullet set — equally prominent.
G5 Team/crew credits block (names as the boss uses them).
G6 Screenshot alt-text + captions for the submission gallery.
