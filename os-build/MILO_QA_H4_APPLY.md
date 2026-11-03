# Milo QA: H+4 application path audit (OC1 theme apply + greeter vs frozen contracts, dexubuntu as cut-2 identity gate)

- Base: origin/main `f51f4d7e` (checked in a /tmp worktree; main clone untouched).
- Slice: Pax room-1 target, 2026-11-02 ~23:5x EST — audit the H+4 application path
  on code that exists NOW: OC1 `metaos-theme/apply.sh` + greeter conf checked
  against the frozen contracts (tokens.json values, AUTOSTART TryExec rule,
  PACKAGES), plus Pax's dexubuntu verify as the identity gate for cut 2.
  No ISO bytes needed for this slice, and none were used.
- Cost: $0. No live key, no live run, no gate-1 (rust-work loop owns gate-1),
  no frozen file touched (this file is new), no merge, nothing mocked.
- Method: read the files verbatim on main; executed `apply.sh` ONLY through a
  PATH shim that rewrites absolute `/etc` and `/usr/share` install targets
  into a throwaway `/tmp/h4-test/fake` root. No system path was written.

## Verdict: H+4 application path is BLOCKED, not gated

`metaos-theme/apply.sh` cannot complete on main as written. The dexubuntu
verify gate below is sound for its 7 named checks, but it cannot rescue a
theme step that installs nothing: the cut-2 identity gate passes only after
a theme step that currently fails first.

## Finding H4-1 (BLOCKER): apply.sh installs a file that does not exist

- `metaos-theme/apply.sh` line 1 (after `set -e`) is:
  `install -m644 "$HERE/greeter/slick-greeter.conf" /etc/lightdm/slick-greeter.conf`
- The tree holds no `slick-greeter.conf` anywhere (searched whole repo).
  The only greeter conf in the OC1 tree is `metaos-theme/greeter/lightdm-gtk-greeter.conf`.
- Shimmed execution result: exit 1, fake root empty — NOTHING installed
  (no wallpapers, no dock theme, no gtk.css, no welcome script), because
  `set -e` aborts on the first failed install.
- Second mismatch inside the same line: the contract package list names
  `lightdm-gtk-greeter` (`metaos-contracts/PACKAGES.md`), and the OC1 greeter
  conf is a gtk-greeter conf — but apply.sh targets a slick-greeter path.
  Question to Pax (H4-Q1): is the fix to install `lightdm-gtk-greeter.conf`
  to `/etc/lightdm/lightdm-gtk-greeter.conf`, or is a slick-greeter conf
  still owed by OC1? Either way the current line cannot stand.

## Finding H4-2: greeter conf itself is contract-consistent, but its dependencies are not installed by apply.sh

`metaos-theme/greeter/lightdm-gtk-greeter.conf`, checked line by line:
- `background=/usr/share/backgrounds/meta-rays.png` — MATCHES apply.sh's
  wallpaper install path (would hold once H4-1 is fixed).
- `background-color=#070B16` — black token, exact.
- `theme-name=MetaOS` and `icon-theme-name=MetaOS` — NO theme index and NO
  icon theme are installed by apply.sh (no `index.theme` anywhere in the
  OC1 tree; gtk.css alone is installed to `/usr/share/themes/MetaOS/gtk-3.0/`).
  The greeter would fall back for theme/icons until a full theme + icon set lands.
- `font-name=Inter 11` — needs `fonts-inter`, which IS in the theme-lane
  lines of `iso/base/metaos.packages` but NOT in Hana's
  `os-build/metaos1-base/packages.txt` (see H4-4). If the H+4 base flow uses
  Hana's list, the greeter font is missing.

## Finding H4-3: token check on what apply.sh WOULD install (if H4-1 were fixed)

Frozen tokens (`metaos-contracts/tokens.json`, identical copy vendored at
`iso/contracts/tokens.json`): blue #1877F2, white #EDF5FF, black #070B16,
cyan #00C8FF, violet #8B5CF6, pink #FF4F9A, emerald #20D6A3, gold #FFBD4A.
- `dock/dock.theme`: EXACT — blue 24;119;242, black 7;11;22, white
  237;245;255, pink 255;79;154. Pass.
- `gtk/gtk.css`: token colours used correctly, PLUS two values NOT in
  tokens.json: `#78BAFF` (blue tint) and `#8291AC` (grey-blue). Minor
  deviation, flagged not failed — Pax to rule whether derived tints are
  allowed or tokens.json must gain them.
- Wallpapers (`meta-rays.png`, `meta-dusk.png`): installed paths match the
  greeter; pixel content not inspected (no display in this audit).
- NOT installed by apply.sh, so NOT counted against this path but noted:
  panel xml (only an echo note, no install step), icon recolor script
  (uses unlisted `#5294e2`, never run by apply.sh), terminal profile
  (uses unlisted `#69DDFF` where the token cyan is `#00C8FF`, plus
  `#FFFFFF` where the token white is `#EDF5FF` — profile file only),
  fonts (FONTS.md only), metafetch (welcome script calls
  `node /usr/share/metaos/metafetch.mjs`; `tools/metafetch.mjs` exists in
  the repo but no apply step installs it to `/usr/share/metaos/`).

## Finding H4-4: two package manifests disagree about who installs the theme packages

- `metaos-contracts/PACKAGES.md` (frozen format): plank, fonts-inter,
  lightdm-gtk-greeter.
- `iso/base/metaos.packages`: HAS all three (theme lane) plus plymouth,
  calamares (boot lane). Consistent with the contract.
- `os-build/metaos1-base/packages.txt` (Hana base slice 1): does NOT list
  any of the three (KEEP: xfce4, lightdm, mousepad, ristretto, evince;
  ADD: python3, curl, ca-certificates, git, htop, nano, unzip, zip).
  It lists `lightdm` but not `lightdm-gtk-greeter`.
- Question to Pax (H4-Q2): which manifest drives the cut-2 base flow?
  If Hana's list, the greeter package, the dock package, and the Inter
  font are all missing at H+4 and findings H4-2/H4-3 go from partial to
  failing. If `iso/base/metaos.packages`, the Hana list needs a pointer
  to it so a cut operator does not use the wrong list.

## Finding H4-5: AUTOSTART TryExec rule — vacuously satisfied by OC1, unconnected elsewhere

- Frozen rule (`metaos-contracts/AUTOSTART.md`): every autostart entry
  MUST use `TryExec=` pointing at its own binary; missing binary = entry
  silently skipped, never breaks login.
- OC1 apply.sh installs ZERO autostart entries, so nothing in this slice
  violates the rule — but nothing in this slice implements it either.
- The repo's only autostart entry, `iso/base/autostart/meta-first-login.desktop`,
  DOES comply (`Exec` and `TryExec` both `/usr/local/bin/meta-first-login`).
  However it is not installed by OC1 apply.sh, and its script
  (`iso/base/meta-first-login.sh`) hard-requires `/usr/share/metaos/dock/*.dockitem`
  files, which OC1 apply.sh never creates (it installs only `dock.theme`).
  So the OC1 path + the iso first-login path do not compose today:
  running first-login after an OC1 apply would exit 1 at the dock check.
  Question to Pax (H4-Q3): is first-login composition part of H+4, or a
  later slice? Either way it must not be assumed working at cut 2.

## Finding H4-6: dexubuntu verify as the cut-2 identity gate — sound for its 7 checks, with two open edges

Re-read verbatim on main @f51f4d7: `os-build/metaos1-base/dexubuntu/verify-rootfs.sh`
is the same 7 checks Pax chroot-tested (os-release PRETTY_NAME/NAME/no-xubuntu,
lsb DISTRIB_ID, hostname, issue banner, xubuntu asset dirs absent), read-only,
exit 1 on any FAIL. Verdict: FIT as the cut-2 identity gate for exactly
those 7 checks.
- Edges the 7 checks do NOT cover (apply side, `apply-in-chroot.sh`):
  hosts, issue.net, motd, and xubuntu-artwork dir ARE handled by apply now
  (from this audit's read), so 4 of the 6 gaps flagged in the earlier
  dexubuntu audit are closed in code (still unexecuted against a real
  layered image — that waits on the first byte-build cut, as Pax noted).
- Edge still OPEN: wallpaper default. Dexubuntu apply looks for
  `/usr/share/backgrounds/metaos/meta-dusk.png`, but OC1 apply.sh installs
  `/usr/share/backgrounds/meta-dusk.png` (no `metaos/` subdir). The guarded
  `if [ -f "$WALL" ]` step silently skips, so the Xfce default wallpaper
  is never pointed at the MetaOS art. Question to Pax (H4-Q4): which path
  is canonical — fix dexubuntu's WALL, or fix apply.sh's install dir?
- Edge still UNPROVEN: Plymouth. Dexubuntu apply only selects a MetaOS
  Plymouth theme if one is already registered; no MetaOS Plymouth theme
  exists in the OC1 tree, so the step is a no-op until Buffy/OC1 ships one.
  Verify does not check Plymouth, so a verify PASS must not be read as
  "Plymouth themed".

## Finding H4-7 (for Pax's ruling, not a failure): two greeter files diverge

- OC1: `metaos-theme/greeter/lightdm-gtk-greeter.conf` — MetaOS theme/icons,
  Inter 11, background `meta-rays.png`.
- `iso/theme/lightdm/lightdm-gtk-greeter.conf` — Adwaita icons, Inter 10,
  background `/usr/share/metaos/theme/greeter-wallpaper.png`, xft tuning
  the OC1 file lacks.
- Question to Pax (H4-Q5): which greeter is the H+4 application path?
  This audit followed Pax's naming (OC1). If the iso/theme file is the
  cut-2 file instead, H4-1/H4-2 need re-audit against it.

## Questions to Pax (summary)

- H4-Q1: slick-greeter install line — fix to gtk-greeter conf, or is a
  slick conf still owed?
- H4-Q2: cut-2 manifest authority — `iso/base/metaos.packages` or Hana's
  `packages.txt`?
- H4-Q3: first-login composition — in H+4 scope or later?
- H4-Q4: canonical wallpaper path — `backgrounds/meta-dusk.png` or
  `backgrounds/metaos/meta-dusk.png`?
- H4-Q5: canonical greeter — OC1 file or iso/theme file?
- Plus, per Del's sleep order: what is Milo's next QA target after this slice?

## What this slice does NOT claim

- No real-image execution: no ISO bytes on this host, no chroot run of
  apply.sh against a real rootfs (shim test proves the missing-file abort
  only). No Mac boot proof (not applicable to a doc/code audit).
- No gate-1 result: doc-only change, no Rust, no compile gate applies;
  the rust-work loop owns gate-1 and was not invoked by this job.
