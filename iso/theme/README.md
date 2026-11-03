# Theme lane

One palette, three files, two generators. Nothing in this directory is drawn
by hand.

## What is generated

| File | Generator | What it is |
|---|---|---|
| `wallpaper/meta-wallpaper.png` | `iso/tools/make_wallpaper.py` | 1920x1080 RGBA. Contract black falling to near-black, one blue ring at 30% of the height, soft glow |
| `gtk/metaos.css` | `iso/tools/tokens_to_gtk.py` | `@define-color meta_*` for every token, plus the window, button, entry, menu and selection rules |

Both read `iso/contracts/tokens.json` — the contract vendored from
`opencode1/metaos-1.0`, pinned by sha256 in `iso/contracts/PIN.md`. The
wallpaper takes `black` and `blue`; the stylesheet takes all eight colours.

`xfce4-desktop.xml` is hand-written and is the only file here that is: it is
the Xfce channel that points the desktop backdrop at the installed wallpaper.

## Why generated

The splash, the start page and the desktop must not drift apart. A hand-edited
hex in a stylesheet is a colour that no longer matches the contract, and no one
notices until the screen is up. Generating both from one file makes drift
impossible, and gives the checker something exact to compare against: it asks
each generator `--check` and fails if the committed bytes differ.

## Regenerate

```
python3 iso/tools/make_wallpaper.py
python3 iso/tools/tokens_to_gtk.py
```

## Where it lands

`iso/tools/apply.sh` installs the wallpaper and the stylesheet to
`/usr/share/metaos/theme/`, and the channel to
`/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml`.

Two honest limits:

- Xfce keys the backdrop by monitor name. The shipped channel uses
  `monitor0`/`workspace0`; on hardware with a different name Xfce creates its
  own key on first login and the default may not apply. Seeing this work needs
  a screen.
- The stylesheet is installed, not activated. Selecting the GTK theme and
  telling Xfce to use it belongs to the shell lane.

**Status: CODE-INSPECTED.** The PNG header is decoded and its dimensions and
colour type are checked; the pixels have never been seen on a display.

## Check it

```
python3 iso/tools/make_wallpaper.py --check
python3 iso/tools/tokens_to_gtk.py --check
python3 iso/tools/check_iso_config.py       # the theme: lines
```
