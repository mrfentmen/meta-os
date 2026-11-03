# OC3B-086/087/088 — settings launcher, handoff, ops

086: no new entry — ISO-lane `meta-settings.desktop`
(Exec=xfce4-settings-manager, Terminal=false) already covers it.
Mirror note for its owner: no TryExec line; suggest adding
`TryExec=xfce4-settings-manager`. Not edited here.
087 handoff: nothing new handed over (entry + xfconf ship with their
lanes); this lane contributes the inventory, the wallpaper-pin
analysis, and the a11y gap note. OC1 boot screenshots close the loop.
088 ops: open Settings from the menu. Appearance changes theme and
wallpaper now. Display arranges monitors; the arrangement applies
immediately. Network and Users may ask for the administrator
password — that is the machine's owner password, set at install,
and nothing here stores or bypasses it.
