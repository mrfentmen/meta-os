# Icon accents — the dock follows the wallpaper

The dock has 27 tiles. Every tile is drawn once, in eight accents, at build
time. At runtime nothing renders: the desktop reads which wallpaper is set and
points a per-user theme directory at the matching set.

```
gen-icon-accents.py      build time, needs Pillow   -> icons/accents/<set>/
meta-icon-accent         runtime, needs no Pillow   -> ~/.local/share/icons/metaos
metaos-icon-accent.desktop  autostart: runs `watch`
```

## The sets

| set | accent | wallpaper that selects it |
|---|---|---|
| `blue-B` | Meta blue, solid plate (default) | `meta-ascii.png`, `meta-wallpaper.png`, anything unlisted |
| `blue-A` | Meta blue, monoline plate | pinned only |
| `blue-C` | Meta blue, dot matrix | pinned only |
| `ice-B` | cyan | `meta-rays.png` |
| `amber-B` | amber | `meta-dawn.png` |
| `violet-B` | violet | `meta-dusk.png` |
| `teal-B` | teal (cooled, never Ubuntu green) | pinned only |
| `mono-B` | no hue, paper glyph on ink | pinned only |

`accents.conf` is the manifest: `default=`, `wallpaper=set` rows, and one
`set=name|label` row per set for a picker to list.

## How the switch works

The system theme stays `/usr/share/icons/metaos`, and every launcher keeps
`Icon=<name>`. The runtime writes `~/.local/share/icons/metaos/index.theme`
whose `Name=` is still `metaos`, containing symlinks into
`/usr/share/icons/metaos-accents/<set>/`. XDG searches the home directory
first, so that directory **shadows** the system one for this user only. The
theme name never changes, nothing re-points a launcher, and no root write is
needed — which matters because this runs at login and again on every wallpaper
change.

Then `gtk-update-icon-cache` and `xfconf-query -c xsettings -p
/Net/IconThemeName -s metaos`.

## Following a change live

`meta-icon-accent watch` runs `xfconf-query -c xfce4-desktop -m` and rebuilds on
a `last-image` change, debounced 0.4 s (dragging a wallpaper picker emits a
burst). It logs every decision to `~/.cache/metaos/icons.log`.

## When the wallpaper is not in the manifest

Two honest paths, in this order:

1. If `python3` + Pillow exist on the box, sample the art's average hue and pick
   the nearest accent set. The log says `sampled its hue`.
2. Otherwise install the manifest default and log
   `not in the manifest and this machine cannot sample it`. It never pretends a
   match happened.

## Commands

```sh
meta-icon-accent apply [WALLPAPER]   # pick and install now
meta-icon-accent watch               # follow xfce4-desktop until killed
meta-icon-accent set blue-A          # pin a set, ignore the wallpaper
meta-icon-accent follow on|off       # wallpaper drives the accent or not
meta-icon-accent list                # sets on this machine
meta-icon-accent current             # what is installed
```

## Proof

`sh test-icon-accent.sh` — 19 assertions, no VM, no X server. It stubs
`xfconf-query` with the three call shapes the script uses, then checks the link
targets, the theme name, the cache refresh, the xfconf set call, the pin/override
paths, the watch path, the two fallbacks, and that a missing set is refused
without breaking the installed theme.

```
19 passed, 0 failed
```

`apply.sh` gates on the sets: fewer than 8 and it refuses to install a half
theme (`apply-GATE-FAIL: want at least 8 icon accent sets`).

Visual proof of the whole idea: `accents/icon-accents.png` — the same 27 tiles
over four real wallpapers.

## Adding an accent

Add a row to `SETS` in `gen-icon-accents.py`, run it with `--sync-default` if the
default set changed, then map a wallpaper to the new set in `WALLPAPERS`. The
runtime reads `set.conf` from each directory, so no shell code changes.
