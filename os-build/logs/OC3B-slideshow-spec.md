# OC3B-257/258 — slideshow spec vs Calamares wiring (static record)

257: Calamares branding contract (from shipped tree, CODE-INSPECTED):
branding.desc declares componentName metaos, slideshow as a plain
image sequence (one frame ~2s during exec), paths relative to the
component dir (upstream initSlideshowSettings resolves via
componentDir.absoluteFilePath). branding.desc itself warns MISSING
`slideshow:` key is FATAL (upstream throws, Branding bails exit 1),
so the key must stay. settings.conf + modules/*.conf
(finished, partition, users, welcome) present in os-build/iso/calamares/.

258: image-list form is what ships. Payload = HTML slides (5x
slide-0N-*.html) + drawn PNGs (productLogo/productIcon/
productWelcome + slide-01..03.png) + slideshow.css + stylesheet.qss,
verified present in os-build/iso/calamares/branding/metaos/ on main.
No separate image-list manifest exists; the file set IS the list.
HTML-vs-QML fork (iso/calamares/branding/meta/ show.qml vs
os-build html slides): which the installer loads is the ISO lane's
wiring decision, theirs not mine (see OC3B-slideshow-wiring.md).
