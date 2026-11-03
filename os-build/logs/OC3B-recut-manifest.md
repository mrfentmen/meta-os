# OC3 ISO-4 — WITH-theme re-cut manifest (DRAFT, pre-staged, no idle)

Trigger (unchanged): OC1 declares the theme pack complete on main.
Nothing below freezes until that declaration — theme is still
moving (e.g. `3a582033` greeter autologin + stock icons landed
after the last check). Pre-staging the method now so trigger-to-
post is minutes, not a session.

Base (FROZEN, on main via OC2 landing `6a75361d`):
- `oc3-payload-no-theme.tar.gz` sha256
  `5d20fa7c12a3c586fff03c3e2055d73fb5d406cbfa60e6cc55e1a43ca95fef11`
  (15 files, install-relative — see OC3B-payload-no-theme.md).

Theme input set (DRAFT candidates, re-frozen at trigger; 180 files
across three trees at last survey):
- `metaos-theme/` (source of truth: gtk/css, icons, xfconf, panel,
  terminal profile, welcome app, wallpapers incl. studio-loop)
- `iso/theme/` (install-side: wallpaper PNGs + MANIFEST.json,
  greeter conf, xfce4 xfconf channels, lightdm theme)
- `os-build/iso/payload-theme/` (payload mirror: apps, dock, fonts,
  greeter, panel, wallpapers incl. live loop mp4)
Survey method: `git archive origin/main <three trees> | tar -t`
(180 paths). At trigger: re-survey, sha256 every file, record the
frozen set + tip sha in the WITH-theme proof file.

Re-cut assembly (mechanical, no decisions):
1. Unpack base tarball + frozen theme set into the same staging.
2. Proposed payload slots (OC1/ISO confirms install paths at pull):
   theme gtk/css → /usr/share/themes/MetaOS/,
   icons → /usr/share/icons/MetaOS/,
   wallpapers → /usr/share/backgrounds/metaos/ (+ live loop),
   xfconf → /etc/xdg/xfce4/, greeter conf → /etc/lightdm/.
3. Tar `oc3-payload-WITH-theme.tar.gz`, post sha256 + file list,
   keep the no-theme tarball untouched (fallback if theme regresses).

Out of scope for this lane: judging theme completeness or aesthetics
(OC1/theme lane), installing anything (ISO lane), booting anything
(OC1). This file is method + candidate set, not a frozen claim.
