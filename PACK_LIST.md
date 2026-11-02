# PACK LIST — pack packages; study the rest, build our own
# (boss order 02:28, corrected 02:30 EST)

The boss's doctrine, in his terms: boot, log in, run programs
with everything there. Two different things, kept straight:

1. **Packages are packages.** Chrome in the image is an
   installed app, the same as on any computer. Installing a
   package is not borrowing code and needs no apology.
2. **What we build, we build ours.** For the system itself —
   7 layers, 3 languages (Rust, Goose, Lobster) — we do not copy
   anyone's code. We STUDY how existing systems solve the
   problem, reverse engineer the approach, and write our own
   implementation in our stack. That is the method for the
   kernel face, the services, all of it.

## Pack into the carrier image (existing apps, themed)
- Browser: Chrome where the Mac build allows, else Chromium.
- Terminal: the distro's real terminal (GNOME Terminal / xfce4).
- Files: the distro's real file manager (Nautilus / Thunar).
- Code Editor: VS Code OSS build or a gedit-class editor — pick
  by image weight, record the pick.
- Notes, Calendar, Calculator: the distro's existing apps,
  themed to the face tokens (Hana's C-section).
- Media: image viewer + video player from the distro.
- Settings plumbing: the distro's network/sound/display panels
  reachable from our Settings window.
- Drivers/firmware: the distro's wifi + graphics firmware set.

## Study-and-build list (reverse engineer the approach, write ours)
- Framebuffer boot + pixel drawing (kernel face, Rowan): study
  how the bootloader hands over a framebuffer and how small
  Rust kernels draw; write ours in kernel/.
- Font + text rendering: study bitmap font approaches; ours.
- PS/2 mouse: study the packet protocol; ours.
- Window/compositor behaviour: study classic WMs; ours.
- Ribbon: already ours (js/logo-background.js) — port the math.
- THIRD_PARTY.md shrinks to the truth: only genuine imported
  dependencies (crates and the like) get listed, because those
  are actually in the tree. Packages installed in the image are
  listed as PACKAGES with versions — a manifest, not a credit
  ledger for code we did not take.

## Proof rule (unchanged)
Every packed app gets a launch proof in the face STATUS.md
table (OpenCode face list, task 37) — packed and proven, or
listed as not-yet.

Owner: OpenCode (image lane), Hana (theming tokens), Pax
(manifest upkeep on each merge).
