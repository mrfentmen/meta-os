# OC2P greeter conflict — two confs, one install path

| Key | `iso/theme/lightdm/lightdm-gtk-greeter.conf` | `metaos-theme/greeter/lightdm-gtk-greeter.conf` |
|---|---|---|
| background | `/usr/share/metaos/theme/greeter-wallpaper.png` | `/usr/share/backgrounds/meta-rays.png` |
| theme-name | `MetaOS` (agree) | `MetaOS` (agree) |
| icon-theme-name | `Adwaita` | `MetaOS` |
| font-name | `Inter 10` | `Inter 11` |
| xft-* trio | present (antialias/hintslight/rgb) | absent |
| background-color/clock-format/indicators | absent | present |

Recommendation: OC1 ships `iso/theme/` — it is the tree
`iso/tools/check_iso_config.py` validates (greeter background + theme-name
checks, 101 passed today). OC2 makes no edit and papers over nothing; the
conflict is flagged here for OC1's T2 pick.
