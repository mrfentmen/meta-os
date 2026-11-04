# Meta OS — porting the reference desktop into the real session

The target is `face/index.html` (the browser desktop the boss approved) rebuilt
out of the things an Xubuntu 24.04 session actually has: a window manager, a
panel, a dock, a wallpaper window, and GTK widgets. No browser, no kiosk page,
no screenshots of a mock.

Read with `plan/ART_PLAN.md` (what it should look like) and
`plan/DEMO.md` (how to prove it on stage).

---

## 0. The rule that makes this portable

One token file, four generated surfaces:

```
os-build/iso/payload-theme/tokens/meta.tokens.json     ← edit only this
        │
        ├── gtk/gtk.css            → /usr/share/themes/MetaOS/gtk-3.0/gtk.css
        ├── xfwm4/themerc          → /usr/share/themes/MetaOS/xfwm4/themerc
        ├── dock/dock.theme        → /usr/share/plank/themes/MetaOS/dock.theme
        └── panel/xfce4-panel.xml  → /etc/skel + /etc/xdg xfce4-panel.xml
```

```sh
python3 os-build/iso/payload-theme/tokens/gen_theme.py          # write all four
python3 os-build/iso/payload-theme/tokens/gen_theme.py --check  # drift check
sh      os-build/iso/payload-theme/tokens/test_tokens.sh        # 14 contracts
```

Why this exists: the image had a `#1877F2` bar in one file and a `#4f7ec2`
accent in another, because the same palette was hand-typed in four places. A
generated surface cannot disagree with itself. `test_tokens.sh` fails if a
generated file is hand-edited, if the plank alpha drifts off `0.72 × 255`, if
the panel XML stops parsing, or if the clock stops sitting between its two
separators.

---

## 1. What the desktop is made of

| Layer | Real component | Reference equivalent | Port status |
|---|---|---|---|
| session | `os-build/face/session.sh` → `startxfce4` | the page's `<body>` | exists, unchanged |
| window manager | xfwm4 + `themes/MetaOS/xfwm4/themerc` | `.window` chrome, round buttons | **generated** |
| panel (top bar) | xfce4-panel + generated XML | `#topbar` | **generated** |
| dock | plank + `themes/MetaOS/dock.theme` | `#dock` | **generated** |
| wallpaper | `meta-live.py` (frames) or static PNG | `#logo-background` canvas | **cover-scaled, proven** |
| app chrome | GTK3 + `gtk.css` | `.win-body`, buttons, entries | **generated** |
| login | lightdm greeter + `meta-m.png` | `.glass-card` | not started |

---

## 2. Phase table

| # | Phase | Files | Verify | State |
|---|---|---|---|---|
| P1 | tokens + generator | `payload-theme/tokens/*` | `--check` passes, `test_tokens.sh` 14/14 | **done** |
| P2 | window chrome | `xfwm4/themerc` | button layout `O\|SHMC`, flat title tint, accent on focus | **done (generated)** |
| P3 | top bar | `panel/xfce4-panel.xml` | 30 px, six plugins, clock centred by two expanding separators | **done (generated)** |
| P4 | dock plate | `dock/dock.theme` | r;;g;;b;;a in range, alpha == 0.72×255 | **done (generated)** |
| P5 | widget theme | `gtk/gtk.css` | names `'Inter'`, accent token, balanced blocks, no brand string | **done (generated)** |
| P6 | wallpaper fills the screen | `wallpapers/live/meta-live.py` `_cover()` | `test_cover.py` 9/9, incl. portrait + ultrawide | **done** |
| P7 | wallpaper fills the *browser* canvas | `face/logo-background.js` `fillScale()` | render at 1600×900, ribbon reaches all four edges | **done** |
| P8 | greeter becomes the glass card | `greeter/*` + a GTK3 greeter + `gtk.css` | see §4 | **not started** |
| P9 | Meta menu instead of xfce's app menu | a plugin or a launcher script | no stock menu icon, no Xubuntu entry | **not started** |
| P10 | window buttons drawn as the reference's circles | `xfwm4/*.svg` + `*.png` (30 files) | layout `\|HMC`, 18 token rows, 30 images land in a fake root | **done** |

P1–P7 and P10 are the skin. P8–P9 are the rest of the port, and the part people
notice without being told to look.

---

## 3. The two canvas fixes, with numbers

**VM wallpaper (`meta-live.py`).** `Gtk.Image` draws a pixbuf at natural size,
so a 1920×1080 frame on a 1600×900 screen was centred with black bars — the
"small and stuck in the corner" report. `_cover()` now scales by
`max(screen_w/frame_w, screen_h/frame_h)` and takes the centred sub-pixbuf, so
the result is exactly the screen. Measured with `test_cover.py` (PIL stands in
for GdkPixbuf; the arithmetic is the same code):

```
shipped 1920x1080 → 1920x1080   R   0/255  G   0/255   (no-op, zero cost)
taller  1920x1080 → 1920x1200   R  13/242  G   0/255   (crop top/bottom)
ultrawide 1920x1080 → 3840x1080 R   0/255  G  64/191   (crop top/bottom)
portrait 1920x1080 → 800x1280   R  83/172  G   0/255   (crop left/right)
```

`left R + right R ≈ 255` on every row is the proof the crop is centred, not
off by a few pixels. The no-op row is the one that matters for cost: in the
shipped configuration the frames are already 1920×1080, so nothing is rescaled
and the wallpaper costs a blit.

**Browser canvas (`logo-background.js`).** The old `SCALE = 0.9` fitted the
whole loop inside the viewport with margin, which is why the reference desktop's
wallpaper looked like a small logo in the middle. `fillScale()` now solves for
the scale that reaches the canvas edge, from the same geometry the projection
uses:

```
xCells = x * SCALE * (1/depth) * WIDTH  * X_PROJECTION
yCells = y * SCALE * (1/depth) * HEIGHT * Y_PROJECTION
SCALE  = BLEED / (2 * extent * (1/CAMERA_DISTANCE) * PROJECTION)
```

with `BLEED = 1.12` so no straight edge of the loop is ever on screen. At
1600×900 that gives `SCALE = 1.583` (was 0.9), horizontal coverage 112% of the
viewport. The vertical coverage comes out near 2.1×, and that is arithmetic,
not a bug: a roughly circular loop in a 16:9 frame cannot fill the width without
losing the top and bottom of the loop. The approved desktop shows the same crop.

---

## 3b. Why windows had no × or – or + at all

Three separate causes, all fixed, and they had to be fixed together or the
buttons still would not appear:

1. **No button art.** `themes/MetaOS/xfwm4/` shipped `themerc` and nothing else.
   xfwm4 resolves a button by name and state and draws *nothing* when a lookup
   fails. 15 SVGs + 15 PNGs are now generated from the tokens.
   SVG because it stays crisp; **PNG as well** because SVG needs the rsvg
   GdkPixbuf loader, and an image without it would bring the empty titlebar
   straight back.
2. **Two sources disagreed.** `meta-desktop.sh` wrote `button_layout=CM|` into
   xfconf at every login — close and maximise on the LEFT, no minimise — while
   themerc said `O|SHMC`. xfconf wins over themerc, so the theme was ignored.
   Layout is now `|HMC` in both, generated from one token, and the login script
   reads themerc instead of hard-coding a string.
3. **CSD windows had no buttons either.** GTK apps that draw their own titlebar
   take the layout from `Gtk/DecorationLayout`, which was unset. It is now
   `icon:minimize,maximize,close` in xsettings.

And the reason none of this could have reached the image even if it were right:
`apply.sh`'s preflight gated the icon count at exactly 20 while the tree holds
26, so every install aborted with `want 20 icons, found 26`. The gate was
"refusing to install a half theme" on a complete one. It is a floor (`-ge 20`)
now, in `apply.sh` and in `theme_proof.sh`'s matching row.

Proof: `apply.sh /tmp/proofroot` prints `15 svg + 15 png window-button images`
and leaves them in `/tmp/proofroot/usr/share/themes/MetaOS/xfwm4/`, with
`button_layout=|HMC` in both themerc and the xfconf channel. It then stops on
the font gate, which is correct for a root that has no fonts.

---

## 4. P8, the greeter, in enough detail to start

The reference login is a 300 px glass card with an 84 px avatar. The image's
current greeter is unity-greeter (webkit), which ignores GTK CSS. Two routes:

1. **lightdm-gtk-greeter** + `gtk.css` + `greeter/lightdm-gtk-greeter.conf`
   (`font-name=Inter 11` is already asserted by `theme_proof.sh`). The card is
   then a GTK CSS class, and the 18 px backdrop blur is dropped — the same
   honest difference as everywhere else.
2. **keep unity-greeter**, ship `meta-rays.png` + `meta-m.png` + Meta colours,
   and accept a centred logo and a plain entry field.

Route 1 is the real port. It needs: the greeter package present on the ISO,
`background=` pointing at the rays, `theme-name=MetaOS`, `icon-theme-name=metaos`,
and `theme_proof.sh` taught that `MetaOS` is the greeter theme too. It also must
not regress autologin (`50-metaos.conf` is the live path; the greeter only shows
when autologin is off).

---

## 5. What "ported" means

A judge sits at the real machine and cannot see a browser: same 30 px bar,
same centre clock, same floating dock at 10 px with 40 px glyphs and labels,
same 12 px window radius and hairline, same ribbon filling the wallpaper, same
blue `#4f7ec2` on every control they touch. The only difference they are told
about is the missing backdrop blur behind panels.

Anything in that list that is true in `face/index.html` and false on the machine
is a bug in this document, not a difference of opinion.
