# OC3B-029/030 — file manager theming + Ubuntu-branding audit

Theming is config-wired, verified statically: xsettings sets
Net/ThemeName=MetaOS and Net/IconThemeName=MetaOS
(iso/theme/xfce4/xfconf/.../xsettings.xml on main), and the MetaOS
icon theme carries folder, folder-open, and user-home glyphs. So the
file manager renders Meta chrome and Meta folder art by config, not
by launch flags — CODE-INSPECTED, pixel confirmation is OC1's boot
screenshot.

OC3B-030 string audit (UI-visible strings only — what a user can
see, not dev docs). Scanned: OC2 + ISO-lane .desktop
Name/GenericName/Comment lines, theme gtk.css + index.theme files.
Result: zero "Ubuntu"/vendor words in any of them. Out of scope by
design: dev documentation legitimately names the Xubuntu 24.04.5 base
(READMEs, check scripts, lane notes) — docs are not pixels, and
scrubbing provenance notes would destroy evidence, not branding.
Xubuntu base strings inside the OS image itself are OC1's screenshot
audit, named not assumed.
