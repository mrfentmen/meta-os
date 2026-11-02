# PREINSTALL — what the Meta OS image ships with (Del's order 2026-11-02 ~00:00)

Design target for the starter-kit image face. Concept pictures were made
2026-11-02 (boot / login / desktop / logo board) and approved as the look:
**Mac polish + terminal soul + the spinning ASCII Meta logo.**

## The three screens

1. **Boot screen.** Black. The green ASCII Meta logo spinning in the
   middle (the existing loop from `js/logo-background.js` / kernel
   `logo_frames`). Under it, a few short white boot lines and a thin
   progress bar. Nothing else.
2. **Login screen.** The ASCII logo faint in the dark background. In the
   middle, one clean glass card: round picture, name **Mrfentmen**, one
   password box, one arrow button. One small terminal line at the bottom
   of the screen.
3. **Home screen (after login).** Dark wallpaper with the faint ASCII
   logo. Mac-style bar at the top. Mac-style dock at the bottom. A
   terminal window is one click away and opens already knowing the
   machine's real state (uptime, memory, what's running). A dashboard
   window shows CPU / memory / storage / network in plain cards.

## On the dock (pre-installed, user-facing)

- **Google Chrome** — the browser.
- **Terminal** — the Meta OS shell.
- **Files** — file browser.
- **Dashboard** — machine state at a glance.
- **Code Editor** — for building inside the OS.
- **Notes**
- **Calendar**
- **Calculator**
- **Settings**
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
- **Meta OS** itself uses the green ribbon **M**.

Logo board concept (2026-11-02): nine rounded-square icons, one accent
color each — M green, Imperium blue shield, Vigiles navy badge, Ignis
orange flame, Medicus teal cross, Science Lab purple flask, Musica pink
note, Custos cyan eye, Officina gold gear-and-wrench.

## Built in, under the hood

- The crew toolchain baked in (Del's order 2026-11-01): **Node, OpenCode,
  Freebuff, git**.
- The passive updater: the image git-pulls on its own.
- The board (in-OS messaging) once it is wired into the shell.

## Honest scope

This is the face of the starter-kit (Debian carrier) image. The
bare-metal kernel still wakes up as plain text first; this face is what
the image shows. Wiring this look into the image is OpenCode finish-list
group C work on the Mac; the four image checks there (autologin, DHCP,
dashboard HTTP, updater pull) are what prove the pieces underneath.
