# OC3B-007 — start page as Chromium homepage

Install: `OC3B-startpage.html` (this directory's sibling proof file)
ships to `/usr/share/metaos/start/index.html` on the image
(ISO lane owns the install path; acceptance note is OC3B-019/020).

Homepage pin, two layers (either suffices; both documented so a
missing layer is visible, not silent):
1. `--app=file:///usr/share/metaos/start/index.html` on the
   `meta-browser-app.desktop` Exec line (committed in oc3b-desktop/).
2. Chromium Preferences `homepage` + `homepage_is_newtabpage` set to
   the same file:// URL at first-run seed (ISO lane bakes the seed;
   OC3B-010 records the values).

OC3B-009: `Terminal=false` on the launcher (audited line, not assumed).
