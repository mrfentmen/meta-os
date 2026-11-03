# Wake-up — apps are windows, and Ubuntu is out of the user

Written 2026-11-03 evening. Everything below was run; where a thing was not run,
it says so in the last section.

## The four things you asked for

**1. Trio opens the police/fire/EMS console, not the logo studio.**
Trio and Imperium are one program (Vigiles · Ignis · Medicus) and both tiles now
open `metaos-imperium.py`. Two things had to be fixed to make that real:

- the console itself was never copied into this image (`/usr/share/metaos/imperium`
  did not exist), so the tile had nothing to load;
- WebKit's Python binding was missing, so the shell would have import-failed even
  with the files there. `gir1.2-webkit2-4.1` is now installed and verified in the
  guest: `WebKit2 OK 2 52`.

**2. The terminal says `metaos` in blue.**
`/etc/skel/.bashrc` and `/home/meta/.bashrc` now end with a Meta prompt. The
appended block runs last, so it wins over Ubuntu's green `\u@\h`.
Also found: `/etc/bash.bashrc.d/metaos.sh` had never executed, because Ubuntu's
`/etc/bash.bashrc` has no drop-in loop. The loop is there now, so the
spinning-logo hook works for the first time.

**3. No more localhost anywhere.**
`meta-app` replaces Epiphany for all eight surface tiles: one GTK window per app,
the app's name in the title bar, no address bar, no tabs, and a Meta-styled "this
app is not answering" page instead of a browser error. Proven with a real boot
and a screenshot of Board open as a window:
`os-build/captures/app-window-board-2026-11-03.png`.

**4. Ubuntu's name is off the user.**
`rename_user.sh` renames the account to `meta` (uid unchanged, so file ownership
survives), moves the home, rewrites the account databases, both autologin files,
casper's USERNAME and every `/home/ubuntu` path. Before the change `--check`
failed five assertions; after, all six PASS, and `grep -r /home/ubuntu` over
`etc`, `opt/face`, `usr/share/metaos` and the user's config returns **zero
files**. The image booted to the desktop afterwards — a missing account would
have stopped at the greeter.

## Proof table

| Claim | How it was checked |
|---|---|
| Identity is Meta | `debrand.sh --check` → 14 PASS |
| No `ubuntu` account or home | `rename_user.sh --check` → 6 PASS, 0 leftover paths |
| Board opens as a window, no URL | boot + screenshot, `captures/app-window-board-2026-11-03.png` |
| WebKit binding present in guest | `chroot … python3 -c "…WebKit2…"` → `WebKit2 OK 2 52` |
| Meta prompt in effect | `grep '^PS1=' /home/meta/.bashrc` |
| Agent loop still works | eval re-run after all changes → 8/8 + relay |
| Science Lab eval in main | merge `d90c9d77`, `registry.json` parses, 24 agents |

## What is still Ubuntu, honestly

- **apt, package names, `ID_LIKE=debian`** — deliberate. That is compatibility,
  not branding. Rewriting it breaks updates.
- **XFCE binaries and their stock wallpapers** (`greybird.svg`, `xfce-shapes.svg`)
  still contain the string. Assigned to Pax.
- **`/usr/share/plymouth/themes/ubuntu-text/`** still ships. The active theme is
  `metaos`; the dead one is a `ls` away. Assigned to Pax.
- **No bootloader.** This image boots by direct kernel load, so there is no GRUB
  menu to brand. An installed system would have one.
- **Musica has no audio path.** No GStreamer in the image at all. Assigned to Milo.
- **Calendar has no backend.** Its tile opens a page that says so. Assigned to Milo.

## What I could not verify

- **Clicking a tile by hand.** I proved `meta-app` works by launching Board from a
  temporary autostart (since removed) and screenshotting it. I did not click the
  dock tile itself — QEMU keyboard injection did not reach XFCE's menu. The tile
  and the autostart run the same command line, but that is inference, not a click.
- **The Imperium console rendering.** The shell and the WebKit binding are both
  verified; the console window itself was not opened and screenshotted.
- **Clean logout/login.** Only autologin was exercised.

## Where the next work is

- `plan/AGENT_PROMPTS_R3.md` — four heavy, non-overlapping prompts (Pax: identity
  leftovers; Milo: native apps, audio, calendar, Aegis; Hana: land the fifteen
  merges and build one scoreboard; Rowan: installer, ISO, demo beats).
- `os-build/lanes/MERGE_PLAN.md` — exact merge order and the conflict procedure.
- `os-build/HACKATHON.md` — demo order, the claims with receipts, and the six
  claims **not** to make.
