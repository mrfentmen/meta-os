# OC3B-085/091 — branding audit + accessibility note

085 string audit (UI-visible scope, same rule as files-theme):
settings .desktop Name/GenericName/Comment lines + xsettings theme
names + xfce4-desktop.xml comments — zero Ubuntu/vendor words.
Dev-doc mentions of Xubuntu out of scope (docs are not pixels).

091 a11y: NO accessibility config ships in any lane (no a11y xfconf
keys on main; panel has no a11y plugin pinned). Upstream Xfce/AT-SPI
defaults apply untouched. Recorded as an honest gap, not a silent
default: if the demo needs a shown a11y path, somebody must name the
feature (owner: theme lane) and OC1 screenshots it. Not invented here.
