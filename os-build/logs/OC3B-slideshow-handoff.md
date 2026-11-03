# OC3B-269/270 — slideshow + branding handoff to the ISO lane

Handing over (reference-only, nothing authored here to copy): the
shipped `os-build/iso/calamares/` tree on main (branding.desc,
5 HTML slides + PNGs + CSS, settings.conf + modules). This lane
contributes the verification (35/35 checker run, audits above) and
two watch items (live-render sizes, HTML-vs-QML wiring choice).

Receiver checklist (ISO lane):
1. Name which branding dir the installer loads (meta vs metaos).
2. Screenshot the show at 1024x768 and 1920x1080 during a live
   install; post both with the build.
3. Keep the `slideshow:` key in branding.desc (FATAL if absent).

270 acceptance: PENDING — no response yet from the ISO lane. Same
pattern as the §1/§2 handoffs: pending is recorded, not assumed.
