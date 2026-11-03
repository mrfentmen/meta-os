# Release boxes — what closes each one (Bond, 2026-11-03)

Read from `os-build/METAOS_1.0_RELEASE_CHECKLIST.md`. 19 boxes open, 5 closed.
Every open box, and the one thing that would close it.

| Line | Box | Closes on | Who |
|---|---|---|---|
| 24 | brand kit committed | the committed files, checked by OC1 | OC1 |
| 25 | Milo asset audit row | one audit line | Milo |
| 40 | boot to login under 60s + screendumps | a boot on the 32GB MacBook | build host |
| 61 | LightDM theme + password login | a boot that shows the greeter and logs in | build host |
| 83 | Xfce bar + Plank dock | a boot that shows the themed desktop | build host |
| 94 | login-to-desktop screenshot set | the same boot, captured | build host |
| 150 | GTK/Papirus/wallpaper/fonts | OC1's recolor run on the build host | OC1 |
| 151 | core apps open from the dock | a click-through on the booted image | build host |
| 154 | ISO cut 3 | a cut record | Pax |
| 158 | Calamares preseeded | code is in the tree; the box needs an install run | build host |
| 159 | clean install to a fresh disk | a full install, start to finish | build host |
| 161 | agent layer autostarts | one fresh boot, units running, no hand-holding | build host |
| 164 | ISO cut 4 | a cut record | Pax |
| 168 | every blocked item fixed or carried | a named list in the final notes | Pax + lanes |
| 170 | ISO cut 5 | a cut record | Pax |
| 174 | final ISO cut | a cut from the merged tree | Pax |
| 175 | boot-video proof | one recorded boot | build host |
| 176 | Milo claim audit | one audit pass over the shipped claims | Milo |
| 178 | Pax go/no-go | the post in room 1 | Pax |

## Totals

| Kind | Boxes |
|---|---|
| needs a boot on the 32GB MacBook | 9 |
| needs Pax to cut and record | 4 |
| needs a signature (Milo, OC1, Pax) | 4 |
| needs a records pass | 1 |
| needs an OC1 build-host run | 1 |

## The short version

No code written on this 8GB machine closes any of these 19. Nine are one boot
night away; four are Pax cutting; four are a signature. That is the whole
remaining surface of 1.0.
