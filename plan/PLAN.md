# PLAN — the one file that does not get lost

Written 2026-11-04. This is the master plan. New plans append here as `## Round N`
rather than starting a new file, so there is one place to look. Anything marked
**DONE** has been seen working; anything marked **TODO** has not.

---

## 0. Ground truth (read this before touching anything)

| Thing | State | Why it matters |
|---|---|---|
| Live tree | `/tmp/wt_land` on `main` @ `d0e1eb45`, **90 commits ahead of `origin/main`, not pushed** | This is the tree the image gets built from. |
| Desktop checkout | `/Users/test/Desktop/meta-os` parked on `agent-1`, 122 dirty files | **Not** the build tree. Stale by 265 lines on the wallpaper and desktop scripts. Do not "fix" things here and expect them on screen. |
| Disk image | `/tmp/metaos.ext4`, 16 GiB, mtime Nov 4 01:04 | Older than the tree. |
| Debrand agents | `agent-debrand-1..4` worktrees, running, no QEMU | Green-wallpaper removal lands on those branches. |

**Rule zero: the image is older than the tree, so every boot shows yesterday's
bugs.** The Trio page, the green flash and the tiny window were all "still
broken" on screen after they were fixed in git. Before any boot, any screenshot
or any video: `sh os-build/tools/sync_image.sh --dry-run`, then for real. If
`--dry-run` shows drift, a capture proves nothing.

---

## 1. The three things on screen right now (in this order)

### 1.1 Trio opens the wrong thing — TODO, root cause known

- **What should be on screen:** the Imperium console — MapLibre basemap, live
  NYCTMC camera list through the local proxy, division pins. That page is
  `imperium/index.html` (546 lines) and it is already in the tree, byte-identical
  to `os-build/iso/payload-apps/imperium/index.html`.
- **What is on screen:** the old flat page / the logo studio.
- **Why:** the hero page needs a same-origin backend. `GET /api/cameras` sends no
  CORS header, and the page's `../vendor` / `../js` paths only resolve when the
  document root is the site root. Opened as `file://` it silently degrades to
  "a web page with pins" — which is exactly what shipped.
- **Fix already in tree:** `os-build/iso/payload-theme/apps/metaos-imperium.py`
  starts `server/server.mjs` on 127.0.0.1:8080 with `METAOS_STATIC_ROOT=/opt/face-site`,
  then loads `http://127.0.0.1:8080/imperium/index.html`, and both dock tiles
  (`Trio`, `Imperium`) run it with a different `--title`.
- **Acceptance:** on the *synced* image, click Trio → window titled "Meta Trio —
  Dispatch", basemap drawn, ≥1 camera thumbnail, `curl -s 127.0.0.1:8080/api/cameras`
  non-empty in the guest. Same page for Imperium, different title. If the
  basemap is grey, the fix is in the page/proxy, not the launcher.

### 1.2 Green wallpaper, still — TODO, mostly in debrand lanes

- `/usr/share/xfce4/backdrops/greybird-wall-1920x1200.png` is Xubuntu's green-grey
  gradient and it is what xfdesktop paints whenever the configured backdrop has
  not resolved yet (fresh profile, settings picker, login race). This is the green.
- `/usr/share/desktop-base/` — ten Debian themes incl. `emerald` (bright green).
- `/etc/alternatives/text.plymouth → ubuntu-text.plymouth`, plus `emerald` plymouth.
- `warty-final-ubuntu.png` is Meta ink now but keeps the Ubuntu filename.
- **Acceptance:** fresh profile boot, `xfdesktop` restart, and Settings → Wallpaper
  all show only Meta art. No file under `/usr/share/{backgrounds,desktop-base,xfce4/backdrops}`
  that renders green. Grep gate in `verify_tree.sh` exits 0.

### 1.3 Window opens small, resize crunches the wallpaper — TODO, design chosen

- QEMU opens the guest at a default size; the demo needs it to open full-size, and
  resizing must not squash the backdrop into a corner.
- **Chosen approach:** `Try QMP display-update first` (set console width/height
  through the monitor) so the guest's virtio-gpu mode is 1920x1080 before X starts;
  fall back to `-device virtio-gpu-pci,xres=1920,yres=1080` plus `-display cocoa,zoom-to-fit=on`.
- Wallpaper side: `meta-live.py` now has `_fit_to_screen()` reading the monitor
  geometry and re-asserting it once a second (xfwm4 re-places DESKTOP windows when
  the panel starts or the mode changes). Needs a resize test, not a guess.
- **Acceptance:** boot at 1920x1080 with no manual resize; drag-resize the QEMU
  window through 3 sizes and back — wallpaper covers every time, spinner stays
  centred, never a letterboxed corner.

---

## 2. Desktop port — the "mac × Meta" native face

Reference implementation to match: `face/` (index.html + face.css + face.js +
logo-background.js) — the browser desktop the boss approved. The OS must look
like that without a browser.

| Phase | What | State |
|---|---|---|
| 2.1 | Window chrome: x black / – white / + blue, drawn by the WM, not the app | **DONE in theme** (`payload-theme/xfwm4/themerc`, `gtk.css`), needs on-image proof |
| 2.2 | Titlebar buttons on web-backed apps too (they draw their own headerbar) | **DONE in gtk.css** (`headerbar button.titlebutton.*`), unproven in a live window |
| 2.3 | UI button inventory — what still needs drawing | **TODO**, see §2b |
| 2.4 | Icon set: 3 candidate languages, pick one, then draw 27 | **TODO** — 3 samples first, boss picks, then the rest |
| 2.5 | Cursor: white arrow, black outline, blue accent | **TODO** |
| 2.6 | Spinner: 240 frames, centred, behind the desktop | **DONE** (240 jpg, 64 MB, 16 fps via `FrameRing` decode-ahead) — needs the seam/wrap check |
| 2.7 | Apps launch as native windows, never a browser tab | partly: `metaos-imperium.py` WebKit shell exists; the rest of the dock still mixes |
| 2.8 | Top bar + dock match the reference (28 px bar, 27 tiles, running dots) | **DONE in scripts**, unproven on the synced image |

### 2b. UI buttons still missing (draw before booting, they are cheap)

Traffic lights are done. The rest of the desktop has no button language yet:

1. Dock: running dot, badge count, progress bar, launch bounce — none drawn.
2. Top bar: NET / DARK chips → real toggles (wifi, theme, DND, agent power).
3. Search field (Super) with focus ring and empty state.
4. List rows: hover / selected / disabled, one row height token (34 px).
5. Sliders (volume, brightness) with knob and filled track.
6. Toggles: on/off/indeterminate in accent blue.
7. Toast + notification card (icon, title, body, action).
8. Dialog: primary / secondary / destructive.
9. Segmented control (the Trio division switcher).
10. Tab strip for windows that need tabs (editor, terminal).
11. Empty state (mark + one line + one action) — used by Aegis, Boards, Messages.
12. Loading: three-dot pulse and the ASCII spinner at 16 px.

All of these are token-driven: `os-build/iso/payload-theme/tokens/meta.tokens.json`
→ `gen_theme.py` → `preview_theme.py` sheet. Draw, preview as a PNG, get approval,
only then wire.

---

## 3. The video — yes, and here is exactly how

**Can I?** Yes. Not by screen-recording the Mac (that films a QEMU window with a
cursor and a menu bar in it). The honest way is to record the guest's own
framebuffer through the QEMU monitor: what you see is what the OS draws, at
1920x1080, with no host chrome.

### 3.1 Pipeline — tool written: `os-build/tools/record_demo.sh`

**Proof it works without a VM:** `sh os-build/tools/record_demo.sh --selftest` ran
60 synthetic frames through the real encoder → `duration=6.033333`, 181 frames at
`r_frame_rate=30/1`, `width=1920 height=1080`, exit 0. The no-boot guard also
refused a bare `--record` with exit 2 and left no QEMU process, as designed.
**Still unproven:** an actual take (needs one boot).

```
boot once  →  /tmp/rec/mon (unix socket)
            →  loop: send "screendump /tmp/rec/f-NNNNN.ppm", convert to jpg, rm ppm
            →  concat list with real per-frame timestamps
            →  ffmpeg -f concat -i list.txt -vf fps=30 -c:v libx264 -crf 18 -pix_fmt yuv420p
            →  captions burned with drawtext, title card, end card
```

- One boot for the whole take. QEMU stays up between shots; the driver moves the
  real pointer with QMP `input-send-event` (usb-tablet), so the cursor in the
  video is the guest's cursor, not the host's.
- Capture rate: `screendump` at 1080p costs ~60–100 ms, so ~8–12 fps is the
  ceiling. **Do not claim 30 fps capture.** Frame times are recorded and the
  concat file replays them at true duration; ffmpeg duplicates frames to 30 fps
  for a standard container. Motion is real-time, not sped up.
- Budget: a 4-minute take at ~10 fps ≈ 2,400 frames. Convert to jpg on the fly
  (~200 KB each) → ~500 MB in `/tmp`, deleted after the encode.

### 3.2 Shot list (target 3:30)

| # | Time | Shot | Proof it is real |
|---|---|---|---|
| 0 | 0:00–0:15 | Power on → plymouth (Meta mark, no Ubuntu text) → greeter | recorded from frame 0 of the boot |
| 1 | 0:15–0:35 | Login → desktop builds itself: bar, dock, spinner already turning | no host interaction |
| 2 | 0:35–0:55 | Hover the dock, the 27 tiles, running dots | pointer driven by QMP |
| 3 | 0:55–1:25 | **Trio**: basemap, live camera list, click a camera | live `/api/cameras`, not a still |
| 4 | 1:25–1:45 | Science lab 3D molecules turning (llvmpipe) | real WebGL, software render |
| 5 | 1:45–2:05 | Musica: a real note plays, 3D notes respond | audio path |
| 6 | 2:05–2:30 | Aegis dashboard reading real run records | real JSONL |
| 7 | 2:30–3:00 | **Agents**: type a job, submit, watch it accepted → run → receipt | the actual relay |
| 8 | 3:00–3:15 | Terminal: `metaos` blue prompt, `neofetch`-style identity | `/etc/os-release` |
| 9 | 3:15–3:30 | End card: Meta OS mark + one line | — |

Every shot must be reproducible from a script. If a shot needs hand-waving, it
does not go in the video.

### 3.3 Sound

Silent master + burned captions first (always deliverable). Optional voiceover
added afterwards with `-i voice.wav -shortest`; captions stay as a safety net.
No music unless it is ours.

---

## 4. Gates before the video is allowed to happen

1. `sync_image.sh --dry-run` shows zero drift.
2. `proof_boot.sh` PASS at 1920x1080 (not black, not single-colour).
3. `proof_session.sh` 9/9 rows in the guest.
4. Trio, Science, Musica, Aegis, Agents each opened once by hand and seen working.
5. `verify_tree.sh` exit 0.
6. No stock wallpaper reachable.

Anything that fails a gate gets written in the final message as a limitation, not
smoothed over.

---

## 5. Open questions for the boss

- **The repo to pull:** the URL was not in the message. Need it (and whether it
  goes alongside `meta-os` or replaces something).
- Video length: 3:30 as above, or a 60-second cut for the submission form?
- Voiceover: your voice, or captions only?
