# MetaOS 1.0 — 12-HOUR BUILD PLAN (crew of 8)

Boss: Mrfentmen. Goal: a bootable MetaOS 1.0 ISO — Meta splash, password
login, original Meta desktop (blue/white/black, mac-inspired, zero Apple
assets), working apps, your Python agent layer running at login.
Method: Xubuntu core remastered with Cubic. x86_64, tested in UTM/VM.
The bare-metal kernel continues as the 2.0 track, not the 12-hour base.

## Lanes (each commits to their own branch; Pax merges everything)

- **Rowan — kernel / 2.0 track (off the 12h critical path).** Keep the
  bare-metal kernel moving: K3 demand-paging fix, K4 talker/listener,
  KF framebuffer pieces. Nothing in the ISO waits on Rowan. Acceptance:
  gate.sh GREEN on his branches; no syscalls.rs changes without his
  named request (FROZEN holds).
- **Buffy — boot + installer.** Plymouth splash, Calamares preseeded with
  Meta branding, install-path testing in VM (clean install start to
  finish). Acceptance: ISO installs preseeded to a fresh disk and reboots
  into the login screen; proof = VM screendumps.
- **Hana — base + first boot.** Cubic project, package list, user
  accounts, first-boot setup, default files and file associations.
  Acceptance: base boots to login in under 60s in VM; first-boot creates
  the user and lands on the desktop.
- **OpenCode 1 (me) — login + desktop shell + theme.** LightDM/SDDM theme,
  lock screen, Xfce top bar + Plank dock + launcher in the Meta colorway,
  GTK recolor, Papirus recolor, wallpaper pack, font picks. Acceptance:
  login works with password; desktop loads with dock/bar/launcher;
  screenshot set committed per milestone.
- **Bond — core apps (code-only, his lane shape).** File manager,
  terminal, settings panel, Chromium default + Meta start page — working
  configs, no stubs. Acceptance: each app opens from the dock, does its
  job, closes clean; configs committed.
- **OpenCode 2 — agent layer packaging.** Python services (patrol, crew,
  queue, livecams) preinstalled and autostarted at login; Goose/Lobster
  runtimes shipped where the runner works; keep the cross-check habit
  (reproduce one proof per session, agree/disagree with evidence).
  Acceptance: fresh boot runs a patrol cycle with no hand-holding; crew
  assessment logged; spend tracked against the guardrail.
- **Milo — audit + acceptance gates.** Owns the proof discipline from the
  500s: claim audit per milestone, per-lane acceptance checks (every
  claim VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED), the
  original-asset audit (nothing Apple-adjacent ships). Acceptance: signed
  audit rows per milestone; anything unproven is named, never padded.
- **Pax — integration + release.** Merge order, conflict calls, ISO cuts
  at H+2/4/6/8/10/12, room-1 posts as things land, final boot-video
  proof, the go/no-go at H+12. Only Pax pushes main and posts anything.

## Timeline
H+0 brand kit locked (name, logo, hex values, wallpaper, password
policy). H+2 base boots with splash. H+4 login + desktop load. H+6 fully
themed. H+8 installer tested end to end. H+10 bugfix/polish. H+12 final
ISO + boot video. Lanes build in parallel from H+0; Milo gates each
milestone; Pax cuts and posts.

## Fences (absolute, all lanes)
- Original assets only. macOS behavior may inspire; Apple artwork, icons,
  layouts pixel-for-pixel, and fonts are forbidden. Milo rejects.
- No mock or placeholder presented as done. Every claim labeled.
- Simulated loopback dispatch only; never a real emergency service.
- kernel/src/syscalls.rs FROZEN.
- All merges through Pax. Nobody pushes main, nobody posts except Pax.

## What the old work becomes
Kernel (Rust) = 2.0 track. Python/Goose/Lobster services = preinstalled
agent layer (OpenCode 2's lane). Face/brand/web work = theme source
(OpenCode 1's lane). 500-task proof habit = Milo's gates. Nothing thrown
away; the 12-hour ISO is the assembly point.
