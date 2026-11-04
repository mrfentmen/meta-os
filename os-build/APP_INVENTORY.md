# APP INVENTORY — what is an app here, what exists, and what is still loose

Written 2026-11-03 20:35 UTC by reading the repo **and** the booted image
(`/tmp/metaos.ext4`), not from earlier notes. Every row below was checked
against a file that exists. Where something is claimed working, the evidence is
named.

> **This is a snapshot, and six rows below are no longer true (2026-11-04).**
> The corrections, each checked against the tree that ships:
>
> | Row in this document | What is true now |
> |---|---|
> | §1 puts Aegis and Nuntius under "Engine, no UI" | Aegis has pages: `aegis-page/index.html` and `nervus/index.html`, both carrying the desk chat. Nuntius is the Board app (`board/board.mjs`, :18935), with a dock tile named Messages. |
> | §2 says 18934 serves `index.html` and `logo-studio.html` | Both are deleted. 18934 serves `surfaces.html`, `bus.html`, `labs/`, `design/`, `os/worlds/`, and the pages of `aegis-page/` and `nervus/`. |
> | §3's tile table lists 19 tiles including "Trio" and "Imperium" | 13 tiles ship in `payload-theme/apps/dock/`; `meta-desktop.sh:399-401` adds Vigiles, Ignis and Medicus, each opening `metaos-imperium.py --division vigiles\|ignis\|medicus`. The single Imperium tile is gone with the page. |
> | §4 lists Logo Studio and Agent Budget as built-but-unused pages | Both deleted 2026-11-04 by the boss's call: they were studio/demo bloat, not apps. |
> | §4 says `bus.html` is not on the image | It ships now, and it talks to the Board on :18935. The relay it used to need is deleted from the repo. |
> | §5 says the security app has "no page, no tile, no window" | False now: Aegis and Nervus are pages. They still have no dock tile, which is the open half of that row. |
>
> Everything else below (the native-vs-surface distinction, the 3D/software-render
> note, the engine inventory) still holds.

---

## 1. What counts as an "app" in Meta OS

There are three different things in this repo that people have been calling an
app. They are not the same, and confusing them is how "we have 20 apps" turns
into a dock with broken tiles.

| Kind | What it is | How the user opens it | Examples |
|---|---|---|---|
| **Native program** | An installed GTK/X11 binary. Real process, real window, no web page. | a `.desktop` on the dock | Terminal, Files, Editor, Calculator, Settings, Trash, Notes, Monitor, Agents, Trio, Imperium |
| **Surface** | An HTML page served on `127.0.0.1`, opened by `meta-app` in a GTK window with **no address bar, no tabs**. Looks like a program, is a page. | a dock tile → `meta-app --title X --url …` | Dashboard, Board, Calendar, Musica, Science, Custos, Officina, Web |
| **Engine** | Backend code and data with **no user interface at all**. Runs, produces JSONL receipts, nobody can open it. | nothing — this is the gap | **Aegis**, **Nuntius** |

`meta-app` is the thing that makes a surface stop looking like a browser. It is
`/usr/local/bin/meta-app` → `os-build/face/native/meta-app.py`.

---

## 2. Where every app actually lives

Backends, all on loopback, all started by `face.target` at login:

| Port | Service | Serves |
|---|---|---|
| 18900 | `face-http` | the 17 pages in `/opt/face/*.html` (shell, board, files, notes, calendar, editor, dashboard, settings, musica, agents, trash, calculator, search, start) |
| 18931 | `face-launcher` | launches allow-listed programs for the shell |
| 18932 | `face-facts` | machine facts for Monitor / metafetch |
| 18933 | `face-ptyd` | the terminal pty pool |
| 18934 | `face-site` | the product site: `index.html`, `surfaces.html`, `logo-studio.html`, `labs/`, `design/`, `os/worlds/` |
| 18935 | `face-board` | board data |
| 18936 | `face-files` | file manager operations |
| 18937 | `face-notesd` | notes + **calendar** + settings store |
| 18940 | `metaosd` | the agent relay (jobs, runs, status) |
| 8935 | `oc2-queue` | the agent job queue |

---

## 3. The dock, tile by tile (19 tiles, from `os-build/face/meta-desktop.sh`)

| Tile | Opens | Kind | Backend | State |
|---|---|---|---|---|
| Terminal | `xfce4-terminal` | native | 18933 pty | installed |
| Files | `thunar` | native | 18936 | installed |
| Notes | `meta-notes` | native | 18937 | installed |
| Monitor | `meta-monitor` | native | 18932 | installed |
| Agents | `meta-agents` | native | 18940 | installed |
| Editor | `mousepad` | native | — | installed |
| Calculator | `mate-calc` | native | — | installed |
| Settings | `xfce4-settings-manager` | native | — | installed |
| Trash | `thunar trash:///` | native | — | installed |
| Trio | `metaos-imperium.py` | native | — | **proven** (police/fire/EMS console, WebKit2 2.52 verified) |
| Imperium | `metaos-imperium.py` | native | — | same program as Trio, second tile |
| Web | 18934 `/index.html` | surface | 18934 | installed |
| Dashboard | 18900 `/dashboard.html` | surface | 18900 | installed |
| Board | 18900 `/board.html` | surface | 18935 | **proven** — opened as a chromeless window, capture `os-build/captures/app-window-board-2026-11-03.png` |
| Calendar | 18900 `/calendar.html` | surface | 18937 | backend **proven**: `notesd --selftest` passes 11/11 inside the image |
| Musica | 18900 `/musica.html` | surface | 18934 (wav) | decode path verified (see §5) |
| Science | 18934 `/labs/molecules/index.html` | surface, **3D** | 18934 | page installed, three.js present; 3D path see §5 |
| Custos | 18934 `/design/meta-custos-watch.html` | surface | 18934 | installed |
| Officina | 18934 `/design/meta-officina-blueprint.html` | surface | 18934 | installed |

---

## 4. Built, installed, and **not on the dock**

These pages are already on the image (`/opt/face-site/`) and nothing opens them.
This is the cheapest wiring left in the whole project — a tile is four lines.

| App | Page on the image | What it is |
|---|---|---|
| **Boards** | `surfaces.html` | **The Imperium dispatch boards.** Nine city world packs (NYPD, FDNY, EMS, MTA, DEP, DOE, hospital, Custos, Officina) with `pack.json` + `runs` data. This is the biggest demo asset that has no tile. |
| **Logo Studio** | `logo-studio.html` | the ASCII Meta logo studio (the thing that made your wallpaper) |
| **Music 3D** | `labs/music3d/index.html` | the 3D note visualiser, three.js |
| **3D Notes** | `design/meta-musica-notes.html` | second 3D music scene |
| **Science (alt)** | `design/meta-scientia-molecules.html` | duplicate of the molecule viewer with more chrome |
| **Agent Budget** | `design/agent-budget-dashboard.html` | agent token-budget simulator — good judge material |

**Not even on the image:**
- `bus.html` — **this is the messaging system** ("muse-relay — live bus"). It is
  in the repo root and in `metaos-update.sh`'s copy list, but the image was
  built before it. So the messaging app does not exist inside the OS yet.
- `labs/science-lab-review/index.html` — the Science Lab reproduction cycle page.

---

## 5. The two engines with no app

### Aegis — the cyber-security application
`aegis/` is a real engine: `findings.mjs`, `kev.mjs` (Known Exploited
Vulnerabilities), `osint.mjs`, `confusables.mjs`, `liveness.mjs`,
`lifecycle.mjs`, `opsec.mjs`, `hosted.mjs`. It writes JSONL receipts to
`os-build/aegis/` (`runs.jsonl`, `findings.jsonl`, `findings-ledger.jsonl`,
`KEV.json`, `LIVENESS.json`, `HISTORY_SCAN.json`).

**There is no page, no tile, no window.** A judge asking "show me the security
app" currently gets nothing. This is the single largest missing surface.

It is also the *easiest* to make visible, because the data is already JSON on
disk: one page that fetches `aegis/findings.jsonl` and `KEV.json` and renders
them, served by 18934, plus one tile. No new backend is required.

### Nuntius — the messaging system
`os-build/round13/nuntius/` contains **DOM fixtures only** (`empty-board.html`,
`long-thread.html`, `unicode.html`, `html-escaping.html`,
`malformed-record.html` + their `.json`). These are test cases for a message
board renderer, not an app. The actual live messaging UI is `bus.html` (§4),
which is not on the image.

So "we have a messaging system" is true at the data/relay level and false at the
"there is something to click" level.

---

## 6. 3D — how Science Lab and Musica 3D are handled

**The pages are real 3D already.** `labs/molecules/index.html` and
`labs/music3d/index.html` use three.js, vendored locally at
`vendor/three.min.js` (618 KB) — no CDN, works offline. Molecules has an honest
guard at line 230: it probes `getContext("webgl2") || getContext("webgl")` and
if there is no context it says so instead of showing a black rectangle.

**Why it might not draw in the VM, and the fix.** This host's QEMU offers only
`none`, `curses`, `cocoa`, `dbus` display backends — there is **no `gl=on` and
no GTK backend**, so hardware/virgl 3D cannot be enabled on this Mac at all.
The image, however, ships Mesa's software rasteriser
(`/usr/lib/aarch64-linux-gnu/dri/swrast_dri.so`, `kms_swrast_dri.so`,
`virtio_gpu_dri.so`, `libgl1-mesa-dri` installed). So the answer is **software
WebGL, not a rewrite**:

- `os-build/face/session.sh` now exports `LIBGL_ALWAYS_SOFTWARE=1`,
  `GALLIUM_DRIVER=llvmpipe`, `WEBKIT_DISABLE_DMABUF_RENDERER=1`.
- `meta-app.py` now sets `enable-webgl`, `enable-accelerated-2d-canvas` and
  `hardware-acceleration-policy=always` (each in its own try/except, so an older
  WebKitGTK still opens the window).

Software rendering is slow: expect a smooth molecule at a ~900 px window and a
choppy one at 1920×1080. For the demo, open Science in a smaller window or
reduce the atom count. Do not promise smooth 3D at full screen in a VM.

---

## 7. What is left to wire, in the order that pays off

1. **Copy `bus.html` + `labs/science-lab-review` onto the image**, add a
   **Messages** tile. (The messaging app then exists.)
2. **Add tiles** for Boards, Logo Studio, Music 3D, 3D Notes, Agent Budget.
   Five of these pages are already sitting on the image unused.
3. **Build the Aegis page** (findings + KEV + liveness from existing JSONL) and
   add an **Aegis** tile.
4. **Prove the 3D** by opening Science with software GL and capturing the canvas
   — not by reading the code.
5. **App icon in the title bar**: every `meta-app` window currently shows the
   generic window icon; pass the app's icon through to `Gtk.Window.set_icon_name`.
6. **Click every dock tile.** Only Board has been proven opened from a tile;
   the rest are proven as "the command line is the same", which is inference.
7. **Run the agent pipeline inside the guest** with the real key and record the
   score.
8. **"About this OS" panel** — version, build, what it is. Judges ask.

## 8. What is NOT true, and must not be claimed

- Not a rewritten Linux. The base is Debian/Xubuntu 24.04; the name, theme,
  session, services and apps are Meta's.
- Not a new kernel in the booted image — it boots Ubuntu's ARM64 kernel.
  `kernel/` (Rust) is a separate, real experiment that is not what runs.
- Aegis has no UI. Nuntius has no UI. Saying otherwise gets caught live.
- 3D is software-rendered here; it is not GPU accelerated.
