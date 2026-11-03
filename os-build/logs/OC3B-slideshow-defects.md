# OC3B-268 — slideshow defects (empty is a result; two watch items)

1. Live rendering at 1024x768 / 1920x1080 unobserved (see sizes
   note). Watch item, owner OC1. Not a static defect: CSS has no
   fixed-pixel traps.
2. HTML-vs-QML fork: two branding dirs ship (iso/.../meta/ show.qml
   vs os-build/.../metaos/ HTML). If the ISO lane wires the wrong
   one, slides silently differ. Watch item, owner ISO lane to name
   the loaded dir at build. This lane touches neither dir.

No static defects: 35/35 checker pass, copy substantive, branding
correct, licenses clear, reboot honestly stated.
