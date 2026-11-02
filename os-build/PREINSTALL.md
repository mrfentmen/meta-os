# PREINSTALL — what the Meta OS image ships with (Del's order 2026-11-02)

Design target for the starter-kit image face: **Mac polish + terminal
soul + the spinning ASCII ribbon loop, live.**

## The logo and the live background (Del's ruling 2026-11-02 00:00)

- **The Meta OS logo is the spinning ASCII infinity ribbon we already
  have** — the live loop rendered by `js/logo-background.js` (kernel
  frames in `kernel/src/logo_frames.rs` come from the same ribbon math).
  NOT the generated green M icon — that mark is dead, do not use it.
- The ribbon is **BLUE**. It is not a still picture: it is the **live
  spinning background** on the boot screen, the login screen, and the
  desktop wallpaper.
- **Modes:** dark mode = black bars, white accents. Light mode = white
  bars, black accents. The top bar can be **white, blue, or black**.
- **Settings let the user change it:** background color, or pick a
  different wallpaper. Wallpapers are **live and interactive**, and must
  look clean and professional.
- The other eight system marks from the logo board stand (Imperium
  shield, Vigiles badge, Ignis flame, Medicus cross, Science Lab flask,
  Musica note, Custos eye, Officina gear-and-wrench). Only the Meta OS
  M is replaced by the ribbon.

## The three screens

1. **Boot screen.** Black. The blue ASCII infinity ribbon spinning in
   the middle. Under it, a few short white boot lines and a thin blue
   progress bar. Nothing else.
2. **Login screen.** The blue ribbon spinning live in the background.
   In the middle, one clean glass card: round picture, name
   **Mrfentmen**, one password box, one sign-in button.
3. **Home screen (after login).** The ribbon keeps spinning as the
   wallpaper. Mac-style bar at the top, Mac-style dock at the bottom. A
   terminal window opens already knowing the machine's real state
   (uptime, memory, what's running). A dashboard window shows CPU /
   memory / storage / network in plain cards.

## On the dock (pre-installed, user-facing)

- **Google Chrome** — the browser.
- **Terminal** — the Meta OS shell.
- **Files** — file browser.
- **Dashboard** — machine state at a glance.
- **Code Editor** — for building inside the OS.
- **Notes**
- **Calendar**
- **Calculator**
- **Settings** — includes the background / wallpaper / bar-color choices.
- **Trash**

## The systems (pre-installed, each with its logo)

- **Imperium** (shield) — the watcher system.
  - **Vigiles** (badge) — police watch.
  - **Ignis** (flame) — fire watch.
  - **Medicus** (cross) — EMS scene watch.
- **Science Lab** (flask)
- **Musica** (music note)
- **Custos** (eye) — night watch for machines/internet.
- **Officina** (gear + wrench) — the invention workshop.

## Built in, under the hood

- The crew toolchain baked in (Del's order 2026-11-01): **Node, OpenCode,
  Freebuff, git**.
- The passive updater: the image git-pulls on its own.
- The board (in-OS messaging) once it is wired into the shell.

## Honest scope

This is the face of the starter-kit (Debian carrier) image. The
bare-metal kernel still wakes up as plain text first; this face is what
the image shows. The live ribbon renderer already exists on the website;
wiring it into the image's screens is OpenCode finish-list group C work
on the Mac, and the four image checks there (autologin, DHCP, dashboard
HTTP, updater pull) prove the pieces underneath.
