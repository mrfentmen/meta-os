# Wake-up: the desktop is native now

Written overnight, 2026-11-03. Read this first; everything below was run, not
described.

## The one-line version

The image no longer boots into a browser. It boots into a **native desktop**:
XFCE's window manager, the Meta top bar, a plank dock with 19 app tiles, the
spinning ribbon behind them, and the eight local backends already up. Close
every window and you see the desktop — not Xubuntu.

Kiosk mode (the old fullscreen web shell) still exists and is now **opt-in**:
`touch /etc/metaos/kiosk` or `METAOS_KIOSK=1`.

## Proof, from a real boot

Boot: `bash os-build/tools/frames_boot.sh` (headless aarch64, snapshot=on,
killed at the end). Captures: `/tmp/metaos-frames9/frame-130.png`, and the
copy in this repo at `os-build/captures/native-desktop-2026-11-03.png`.

Seen on that capture:
- full-width top bar, **Meta OS** + mark on the left, clock on the right
- 19 dock tiles with the Meta icon set (blue glyphs, not blank squares)
- ribbon wallpaper filling 1920x1080 (the spinning background is the live
  window, still doing its job)
- no browser window, no kiosk

Ports, measured inside the guest 8 s after login (`/tmp/metaos-ports.log`,
from a snapshot=off boot, so it is still on the disk):

```
18900 200     18934 200
18931 404     18935 404    (404 = server alive, no route on "/")
18932 404     18936 404
18933 400     18940 404
```

Session log (`/tmp/metaos-session.log` on the disk):

```
meta-desktop: panel <- /etc/xdg/.../xfce4-panel.xml
meta-desktop: wm theme MetaOS, buttons left
meta-desktop: done: 19 dock items
face.target started
agent-login: started oc2-queue / oc2-trio / oc2-patrol.timer / oc2-health.timer / oc2-watchman
plank dock scheduled
native desktop mode (kiosk off)
```

So at login: backends up, agent relay up, panel themed, dock populated — in
that order, and the desktop is the thing you land on.

## What changed, file by file

| File | What it does now |
|---|---|
| `os-build/face/session.sh` | starts `face.target`, `metaosd`, the agent login hook, the live wallpaper and plank; kiosk only when asked; always ends in `exec startxfce4` |
| `os-build/face/meta-desktop.sh` | per-user desktop install: Meta panel, MetaOS wm theme with buttons **left**, GTK theme, plank settings, 19 `.desktop` + dock items. File-based, so it runs in a chroot too |
| `os-build/face/native/meta-notes.py` | GTK notes program, real `.md` files in `~/Notes`, delete goes to XDG Trash |
| `os-build/face/native/meta-monitor.py` | GTK system monitor: CPU, memory, disk, uptime, agent count from 18940. Reads `/proc`; says "unavailable" rather than inventing a number |
| `os-build/face/native/meta-agents.py` | GTK agent console: lists agents from 18940, submits through `meta-ask`, prints exactly what it printed |
| `os-build/iso/payload-theme/panel/xfce4-panel.xml` | top bar: `p=6`, `length=100` (percent), no `length-adjust`, expand=true separator, clock, tray |
| `os-build/face/provision.sh` | installs the three native programs to `/usr/local/bin`, the dock icons to `/usr/share/icons/metaos`, the panel channel to `/etc/xdg` + `/etc/skel`, `xfwm4/themerc` and `gtk.css` into `/usr/share/themes/MetaOS`, plank theme |
| `os-build/tools/frames_boot.sh` | headless boot with frames at 20/40/60/90/130 s; `SNAP=off` persists the guest's logs for reading afterwards |

## The bug that ate the evening, so it is not repeated

The top bar was a short strip in a corner for three boots. Two causes:

1. **`length-adjust` was invented.** XFCE has no such property in this config.
   With `length=100` and no `length-adjust`, the bar is 100% of the screen.
2. **The snap enum is not guessable.** `p=1` landed top-right, `p=8` bottom-left,
   and the value that means "top, full width" — `p=6` — came from the *Xubuntu
   panel that shipped on the image*, not from documentation.

Dock icons were blank white tiles because `.desktop` files used icon *names*
(`system-file-manager`) that the active theme doesn't carry. They now use
absolute paths into `/usr/share/icons/metaos/`.

A third one, found by the port probe: the new session never started
`face.target`, so every web tile would have opened a dead window. It starts
before plank now.

## Where each thing stands

| Item | State |
|---|---|
| Native desktop at login | **PROVEN** (boot capture) |
| Top bar full width, branded | **PROVEN** (boot capture) |
| Dock, 19 tiles, Meta icons | **PROVEN** (boot capture) |
| Backends up at login | **PROVEN** (port log) |
| Agent relay units started at login | **PROVEN** (session log) |
| Native programs (notes/monitor/agents) | **INSTALLED** — syntax-checked, launched from the dock; a real click-through has not been recorded |
| Science Lab / Imperium / Musica / Officina / Trio tiles | **PROVEN to answer 200** in-image; opening them inside a window is not yet captured |
| Login card like the mock | **NOT WORKING** — see below. Autologin is on and must stay on |
| Light bar / dock labels | **DECIDED AGAINST** — the bar is dark on purpose (the MetaOS GTK theme draws white text; on paper it would be invisible), and plank has no label option |

## The login screen: tested, and it is broken

The greeter config is Meta-branded already: `background=/usr/share/backgrounds/meta-ascii.png`,
`theme-name=MetaOS`, `default-user-image=/usr/share/backgrounds/meta-m.png`.
But autologin is what puts you on the desktop, so the greeter is never drawn.

I disabled autologin once (`99-verify-greeter.conf`) and booted to see it. The
result was **not** the login card: lightdm never started a greeter, and the
screen dropped to the text console, branded but wrong:

```
Meta OS 1.0 (Ribbon) metaos console
metaos login: _
```

The override was deleted afterwards and `autologin-user=ubuntu` is back in
both `10-metaos-live.conf` and `50-metaos.conf` (verified by grep after the
removal). **Do not turn autologin off for the demo** — you lose the desktop and
get a tty. Fixing the greeter means reading
`journalctl -u lightdm` on a boot where it fails; that was not done here.

## How to use it

```sh
# boot with a window (use this, not a 3-minute script)
qemu-system-aarch64 -M virt -cpu host -accel hvf -m 4096 -smp 4 \
  -kernel /tmp/meta-boot/vmlinuz -initrd /tmp/meta-boot/initrd.img \
  -append "root=/dev/vda rw console=ttyAMA0 console=tty0 plymouth.enable=0" \
  -drive file=/tmp/metaos.ext4,if=virtio,format=raw,snapshot=on \
  -device virtio-gpu-pci,xres=1920,yres=1080 \
  -device qemu-xhci -device usb-kbd -device usb-tablet \
  -netdev user,id=n0 -device virtio-net-pci,netdev=n0
```

- `snapshot=on` means nothing you do in the VM is kept. Drop it to keep changes.
- Back to the old kiosk: `touch /etc/metaos/kiosk` before boot.
- The diagnostic port probe runs when `/etc/metaos/probe` exists (it does now)
  and writes `/tmp/metaos-ports.log`.

## Honest scope

This is a Linux distribution with a Meta desktop: XFCE is the window manager,
plank is the dock, and the apps are real programs. It is not a new compositor
and it is not a rewritten Linux. What it is: the thing a judge can be shown —
boot, desktop, dock, terminal, agents — with nothing Ubuntu-shaped on screen.
