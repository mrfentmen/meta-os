# OC3B-252/258/259/260/265/266 — slides assessment + wiring + licenses

252 extensions: none made. The five slides read complete and
specific (no thin/generic copy found to extend); extending for its
own sake would add words, not information. Recorded as a deliberate
no-op with the reason, not skipped work.

258 image-list form: the show payload is HTML slides + drawn PNGs
(productLogo/productIcon/productWelcome), wired per
slideshow.css/show.qml in the shipped tree. No separate image-list
manifest exists; the file set IS the list (verified present above).

259/260 HTML-vs-QML wiring + owner: TWO branding dirs ship on main
(`iso/calamares/branding/meta/` with show.qml, and
`os-build/iso/calamares/branding/metaos/` with the HTML slides).
Which one the installer actually loads is an ISO-lane wiring
decision, explicitly theirs (OC3 owns neither dir). Recorded here
so the fork doesn't silently pick one at build time.

265/266 imagery licenses: productLogo/Icon/Welcome are drawn by
`assets/make_assets.py` per the branding.desc header (ring mark +
5x7 block wordmark, original work, no third-party assets). No
licensed imagery in the show path. Attested from the build
sources, not from pixels I can't render here.
