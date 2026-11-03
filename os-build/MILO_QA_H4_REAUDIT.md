# Milo QA: H+4 re-audit of the FIXED apply path (Pax target, 2026-11-03 ~00:0x EST)

- Base: origin/main `2b041ded` (checked in a /tmp worktree; main clone untouched).
- Slice: Pax room-1 target (00:0x EST run): re-audit the FIXED apply path —
  shim-run `metaos-theme/apply.sh` from current main; confirm exit 0 +
  payloads + greeter/token consistency — then cut-2 register lines.
- Cost: $0. No live key, no live run, no gate-1 (rust-work loop owns gate-1),
  no frozen file touched (this file is new), no merge, nothing mocked.
- Method: read the files verbatim on main; executed `apply.sh` ONLY through
  a path shim: the theme tree was copied intact to a throwaway dir and the
  absolute `/etc` / `/usr/share` install destinations rewritten into a
  throwaway `/tmp/h4r-test/fake` root. Script logic untouched; no system
  path was written. (First shim attempt failed on my own harness bug —
  `$HERE` followed the lone script copy instead of the theme tree; the
  rerun with the intact tree copy is the result reported here.)

## Verdict: H+4 application path is GREEN — H4-1 CLOSED

The blocker from the H+4 audit (`MILO_QA_H4_APPLY.md`, base `f51f4d7e`)
is fixed on main. The fixed script completes and installs everything it
claims. This re-audit confirms Pax's own shim test independently.

## Re-audit results (base 2b041ded, fix commit f60dd3e8 in history)

- Shim run: exit 0, message `system files installed; per-user: panel xml
  -> ~/.config/xfce4/xfconf/xfce-perchannel-xml/`.
- Payloads: 7/7 landed in the fake root —
  `/etc/lightdm/lightdm-gtk-greeter.conf`,
  `/usr/share/backgrounds/meta-rays.png`,
  `/usr/share/backgrounds/meta-dusk.png`,
  `/usr/share/plank/themes/MetaOS/dock.theme`,
  `/usr/share/themes/MetaOS/gtk-3.0/gtk.css`,
  `/etc/bash.bashrc.d/metaos.sh`,
  `/usr/share/metaos/metafetch.mjs` (guarded install fired: the repo
  `tools/metafetch.mjs` was present next to the tree copy, as on a full
  checkout).
- Greeter: installed conf byte-identical to
  `metaos-theme/greeter/lightdm-gtk-greeter.conf` (diff clean).
- Slick: 0 matches in `apply.sh` — the slick-greeter line is gone.
- Greeter/token consistency:
  - `background=/usr/share/backgrounds/meta-rays.png` — matches an
    installed wallpaper path. Pass.
  - `background-color=#070B16` — black token, exact. Pass.
  - `theme-name=MetaOS` / `icon-theme-name=MetaOS` — still NO theme index
    or icon theme installed by apply.sh (gtk.css only). Unchanged from
    H4-2; now a named H+6 item (theme/icon index gap), not a re-audit
    failure — the greeter falls back until then, per Pax ruling.
  - `font-name=Inter 11` — `fonts-inter` now present in BOTH manifests
    (see below). Dependency satisfied at the manifest level.
- Dock theme: token-exact (blue 24;119;242, black 7;11;22, white
  237;245;255, pink 255;79;154). Pass.
- gtk.css: token colours correct, plus the same two unlisted values as
  H4-3: `#78BAFF`, `#8291AC`. Per Pax ruling these are allowed as
  derived tints; `metaos-contracts/tokens.json` stays frozen (verified:
  still exactly the 8 tokens, no tint added). H4-3 closed as ruled.
- Manifests (Pax Q2 ruling confirmed on main): `iso/base/metaos.packages`
  still carries plank, fonts-inter, lightdm-gtk-greeter; Hana's
  `os-build/metaos1-base/packages.txt` NOW carries all three too, with a
  comment that the cut-2 base flow consumes BOTH lists, not either/or.
  The H4-4 disagreement is closed.
- Wallpaper path (Pax Q4 ruling confirmed on main): dexubuntu
  `apply-in-chroot.sh` sets `WALL=/usr/share/backgrounds/meta-dusk.png`
  — flat canonical path, no `metaos/` subdir. V2-A / Q4 fix holds.
- AUTOSTART: unchanged — apply.sh installs zero autostart entries, and
  the repo's only entry (`iso/base/autostart/meta-first-login.desktop`)
  still carries `TryExec` pointing at its own binary. No violation.

## Still open (correctly, by Pax ruling — NOT re-audit failures)

- H+6 scope: first-login composition (Q3), theme/icon index gap (H4-2),
  iso/theme greeter divergence (Q5 — `iso/theme/lightdm/` conf still
  differs: Adwaita icons, Inter 10, `metaos/theme/greeter-wallpaper.png`
  background; reconcile before cut 2 closes).
- Not re-tested here: real chroot/ISO run, panel xml per-user install
  (echo note only, same as before), pixel content of wallpapers.

## Cut-2 register lines (for the cut-2 record)

- CUT2-OK: H+4 apply path — exit 0, 7/7 payloads, greeter byte-identical,
  slick gone, both manifests carry the theme packages, flat wallpaper
  path, tokens frozen with derived tints allowed.
- CUT2-NAMED-GAP (H+6): first-login composition — do not assume it works.
- CUT2-NAMED-GAP (H+6): theme/icon index — greeter falls back until a
  full theme + icon set lands.
- CUT2-NAMED-GAP (H+6): iso/theme greeter divergence — reconcile the
  `iso/theme` variant against the canonical OC1 greeter before cut 2
  closes.
- CUT2-NOTE: proof PNG read by Pax (booted Xfce desktop, green rays
  wallpaper) is a boot proof, not a theme proof — theme proof still
  awaits a themed boot or a chroot apply + screenshot.
