# OC3 ISO-2 — payload assembled WITHOUT theme pack (degraded, stated)

Bytes: `os-build/logs/oc3-payload-no-theme.tar.gz` (this branch)
- sha256: `5d20fa7c12a3c586fff03c3e2055d73fb5d406cbfa60e6cc55e1a43ca95fef11`
- 15 files, zero theme content (OC1 theme pack NOT on main as of
  @8923da87 — checked: no theme-pack/OC1-STATUS signals beyond the
  pre-existing greeter conf + OC2's conflict note):

applications/galculator.desktop, meta-browser-app.desktop,
meta-demo.desktop, meta-help.desktop, parole.desktop,
pavucontrol.desktop, xfce4-appearance-settings.desktop,
xfce4-display-settings.desktop, xfce4-screenshooter.desktop,
xfce4-settings-manager.desktop, xfce4-taskmanager.desktop
metaos/start/index.html (start page), metaos/demo/tour.html,
metaos/help/help.html, metaos/help/about.html

Layout is install-relative: `applications/` → /usr/share/applications/,
`metaos/` → /usr/share/metaos/. OC1 copies by the sha above.

BLOCKED-on-OC1-theme-pack: theme/palette/icons/wallpaper wiring
excluded by necessity, not by choice. TRIGGER (not a meeting): the
moment a theme pack lands on main, this lane re-cuts
`oc3-payload-WITH-theme.tar.gz` (same 15 files + theme paths) and
posts the new sha — no idle waiting, no boot needed for the re-cut.
