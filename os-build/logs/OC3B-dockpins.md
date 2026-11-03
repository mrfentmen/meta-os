# OC3B-213/214 — dock pin set (proposed; approval: OC1/theme lane)

No canonical pin list exists in-tree (`dock.theme` is Plank COLORS,
not pins). This file PROPOSES; OC1/theme lane disposes at first boot.
Pins reference launchers that exist on main or in this lane — nothing
invented.

Proposed pins, in order: Files (Thunar, OC2) · Web (Chromium, ISO lane)
· Terminal (xfce4-terminal, ISO lane) · Settings (ISO lane) ·
Media Player (Parole, THIS lane) · Agent Status (OC2).

OC3B-214 check as far as static analysis goes: every pinned name above
resolves to a committed .desktop (six OC2, three ISO-lane, one this
lane, one OC1 wallpaper excluded — wallpaper is not pinnable).
Launches-at-click and icon rendering are OC1 boot checks, named here
so they are not silently assumed.
