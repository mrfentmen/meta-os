# Meta OS — art and look plan for the native desktop

Source of truth for colour and geometry is `face/face.css` (the reference
desktop the boss signed off). Everything below is derived from it, so the native
desktop and the reference cannot disagree by accident. If a value here and a
value in `face.css` differ, `face.css` wins and this file is a bug.

Read with `plan/DESKTOP_PORT.md`.

---

## 1. The token set (the only place colours and sizes are allowed to exist)

**These tables are now prose.** The single source is
`os-build/iso/payload-theme/tokens/meta.tokens.json`, which generates
`gtk/gtk.css`, `xfwm4/themerc`, `dock/dock.theme` and `panel/xfce4-panel.xml`
via `tokens/gen_theme.py`. `tokens/test_tokens.sh` (14 rows) proves the four
generated files still agree with it. If a value below and the JSON disagree, the
JSON wins — and this file is a bug. Values invented for the native side (not
present in `face.css`) are marked `DERIVED` in the JSON with their derivation.

The three that are `DERIVED`, so nobody hunts for them in `face.css`:
`accent_bright #9dc0f2` (accent mixed 45% toward white, for the specular),
`muted #8b93a7` (`--win-fg` at 62% over `--win-bg`, because GTK3 needs an
inactive-title colour where CSS uses opacity), and `urgent #e8553f` (plank's
urgent dot needs a hue the reference does not have).

From `face.css`, verbatim:

| Token | Dark | Light | Used by |
|---|---|---|---|
| bar background | `#000000` | `#ffffff` | top bar |
| bar foreground | `#ffffff` | `#000000` | top bar text |
| bar blue alt | `#0750bc` | — | "blue bar" mode |
| dock background | `rgba(20,22,28,.72)` | `rgba(255,255,255,.78)` | dock plate |
| dock foreground | `#ffffff` | `#000000` | dock labels |
| window background | `rgba(14,16,22,.92)` | `rgba(255,255,255,.94)` | window body |
| window foreground | `#e8ecf4` | `#101318` | window text |
| window titlebar | `rgba(255,255,255,.08)` | `rgba(0,0,0,.06)` | titlebar |
| accent | `#4f7ec2` | `#4f7ec2` | marks, buttons, focus |
| desktop background | `#04060c` | `#dfe7f2` | behind everything |
| hairline | `rgba(127,127,127,.30)` | same | borders |
| hairline strong | `rgba(127,127,127,.35)` | same | dock separators |

Geometry, also verbatim:

| Thing | Value |
|---|---|
| top bar height | 30 px, full width, content 14 px inset |
| bar mark | 17 px, accent, 700 weight, 7 px gap |
| bar app name | 13 px, 700 weight |
| bar right items | 12 px, opacity .85, 14 px apart |
| dock plate | 18 px radius, 8 px 10 px padding, 6 px gap, 10 px from bottom |
| dock item | 52 px wide |
| dock glyph | 40×40 px, 10 px radius, 21 px glyph |
| dock label | 9.5 px, opacity .8 |
| running dot | 4 px tall, opacity .9 when running |
| dock separator | 1 px wide, 4 px 3 px margin |
| window | 12 px radius, 520 px wide default, 1 px hairline border |
| titlebar | 8 px 12 px padding, title 13 px 700 |
| window button | 22 px circle, 6 px apart |
| window body | 14 px 16 px, 13.5 px text, 1.55 line height |
| login card | 300 px wide, 20 px radius, 28/26/18 px padding, blur 18 px |
| login avatar | 84 px circle, gradient `#0750bc → #4f7ec2`, 40 px "M" |
| login name | 20 px, 600 |
| login button | full width, 10 px radius, accent, 14 px 600 |

Motion, from the reference: hover lift `scale(1.18) translateY(-4px)` in 120 ms;
window shadow `0 22px 55px rgba(0,0,0,.45)`; bar shadow
`0 1px 12px rgba(0,0,0,.25)`; dock shadow `0 14px 40px rgba(0,0,0,.35)`.

**Blur is the one thing GTK cannot fake.** `backdrop-filter: blur()` has no
GTK3 equivalent at reasonable cost. So: the dock and windows keep their alpha
and their border and their shadow, but they do **not** blur what is behind them.
That is the single honest visual difference between the reference and the native
desktop, and it is written down here rather than discovered on stage.

---

## 2. Wallpaper

**Target:** 1920×1080, the ASCII ∞ ribbon from the logo studio, rotating in 60
frames at 30 fps (one turn per 2 s).

| Asset | Path | Spec |
|---|---|---|
| frame sequence | `iso/payload-theme/wallpapers/studio-loop/loop-00.jpg … loop-59.jpg` | 1920×1080, JPEG q≈82, ~200–420 KB each, 60 files |
| static fallback | `iso/payload-theme/wallpapers/studio-loop/loop-00.jpg` | used when the player cannot start |
| player | `iso/payload-theme/wallpapers/live/meta-live.py` | GTK3, one window, `WM_CLASS = metaos-live`, 30 fps, no frame blown up past the monitor |
| install | `/usr/share/metaos/studio-loop/` + `/usr/share/metaos/apps/meta-live.py` | written by `face/provision.sh` |

**Fill, never fit.** Every wallpaper surface must COVER the screen. This was a
real, repeated failure: `Gtk.Image` draws a pixbuf at natural size, so a
1920×1080 frame on a 1600×900 screen was centred with black bars and the boss
reported "the wallpaper is small and stuck in the corner" three separate times.
`meta-live.py` `_cover()` now scales by `max(w/fw, h/fh)` and crops the centred
sub-pixbuf, which is proven by `wallpapers/live/test_cover.py` (9 rows, incl.
portrait and ultrawide; `left + right ≈ 255` on the ramp proves the crop is
centred). The browser canvas got the same treatment through `fillScale()` in
`face/logo-background.js` — `SCALE` is solved from the projection, not guessed;
see `plan/DESKTOP_PORT.md` §3 for the numbers.

Rules the player must keep:

1. It is a window, not a root pixmap. It must be `below`, skip the taskbar and
   skip paging, sized to the monitor's *current* size, and re-sized on
   `size-changed` — a wallpaper window pinned to a stale 640×360 is what made
   the art look cropped into a corner.
2. It must not fight the window manager: no focus, no decorations, no input.
3. If the frames are missing it draws the static fallback, and if that is
   missing it draws `#04060c` — never a stack trace on screen.
4. It must cost less than a few percent of a core. Frames are decoded once and
   cached; a 60-frame loop at 1080p re-decoded every turn is a money furnace.

Generation (deterministic, no network):

```sh
node os-build/iso/payload-theme/wallpapers/loop_from_studio.mjs     # capture frames from the studio
python3 os-build/iso/payload-theme/wallpapers/loop_frames_to_wallpaper.py  # re-encode to loop-NN.jpg
```

---

## 3. Login screen

Two layers, because the reference is a glass card floating on the ribbon and a
greeter cannot do everything:

| Layer | What it is | Where |
|---|---|---|
| backdrop | `meta-rays.png` (1920×1080, radial blue field) + a dimmed copy of frame 00 of the loop | `/usr/share/backgrounds/` |
| mark | `meta-m.png` (512×512, the M on the blue circle) | `/usr/share/unity-greeter/logo.png` and `/usr/share/backgrounds/meta-m.png` |
| credentials UI | the greeter's own, in Meta colours | `com.canonical.unity-greeter` gsettings override |

The glass card, the 84 px avatar and the blurred panel are **stretch, not
requirement**: they need a GTK greeter with a CSS theme, which is a separate
piece of work with its own risk (the current image uses the webkit greeter,
which ignores CSS). Plan: ship the ray backdrop + mark + Meta colours now, and
treat "glass card on the real greeter" as an upgrade with a fallback that is
still correct.

Non-negotiables, because these were real failures:

- The login screen must be **compiled into the schema cache**, not just written
  as an override file (see `metaos-schemas.service`).
- It must never fall back to Ubuntu's emerald art. If the Meta asset is missing,
  the fallback is `#04060c`, never the stock image.
- No hostname, no Ubuntu logo, no "Ubuntu" string anywhere on it.

---

## 4. Dock icons

27 tiles today, but the reference shows 16. **Do not draw 27 until the tile list
is decided** (that is a product question, not an art question).

| Property | Value |
|---|---|
| size | 128×128 PNG, drawn at 40 px |
| background | 10 px-radius rounded square, same 3 blues as the accent ramp |
| glyph | single ASCII/line glyph, 2 px stroke, centred, drawn on a 16 px grid |
| colours | `#062258`, `#0750bc`, `#4f7ec2` (same ramp as the studio) |
| format | PNG with alpha, sRGB, no metadata |
| naming | `<app>.png`, lowercase, hyphens, matching `add_app` ids |
| licence | drawn here with PIL, deterministic, no third-party art |

Fallback rule that already exists and must stay: a tile whose icon is missing
logs a named warning instead of drawing a blank square.

---

## 5. Type

The reference uses `-apple-system, "Segoe UI", Roboto, Helvetica, Arial`. None of
those exist in this image. The native stack must be a font that **is** installed:

1. `Inter` if the build installs it (preferred: matches the reference's
   proportions),
2. else `DejaVu Sans` (always present on this base),
3. never a name that is only a hope — a missing font is a silent fallback and
   looks like a layout bug.

Monospace: `DejaVu Sans Mono`, **not** `Ubuntu Mono`. The reference terminal look
is dark background + light text at 12.5 px, which this reproduces exactly.

---

## 6. What "done" means for the art

A person puts the reference screenshot and a screenshot of the real desktop side
by side and cannot name a difference except **blur behind panels**, plus:

- bar: same height, same ∞ mark on the left, same clock in the middle, same two
  indicators on the right;
- dock: same three groups, same 10 px float, same labels under the icons, same
  running dot;
- windows: same radius, same hairline, same titlebar tint, same round buttons on
  the right;
- wallpaper: same ribbon, same palette, moving;
- login: Meta mark and Meta rays, no Ubuntu anywhere.

Everything in this file is measured from `face/face.css`. If the port uses a
number that is not in this file, the number is wrong until this file says it.
