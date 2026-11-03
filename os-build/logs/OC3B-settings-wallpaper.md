# OC3B-078/079 — wallpaper sticks + theme keys (config-verified)

078: `iso/theme/xfce4-desktop.xml` pins
`last-image=/usr/share/metaos/theme/meta-wallpaper.png`,
`image-style=5` (zoomed fill). A pinned last-image survives logout
and reboot by construction — the "sticks" mechanism IS this file.
Observed-confirmation is still OC1's screenshot, but there is no
code path here that could unstick it short of the file missing on
the image (installer owns that copy; acceptance note pending as in
§1 OC3B-019 pattern).

Theme keys (xsettings.xml on main): Net/ThemeName=MetaOS,
Net/IconThemeName=MetaOS, FontName=Inter 10, animations on.
Clock: panel carries a clock plugin (theme panel xml). Format string
is user preference, not lane policy. Users screen, network screen,
display screen: launched from the same manager; per-screen behavior
is OC1 screenshot territory (079/082/083/084), named not claimed.
