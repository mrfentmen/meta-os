# Wallpaper boot check — every file, on a real screen

The wallpapers are generated, not photographed, and this machine has no
display. So the files are checked here (size, colour type, provenance) and
then looked at once, on the 32GB MacBook. This page is that second half.

It started as five files: the GRUB backdrop, the greeter, and the desktop at
1080p, 1440p and 1366. The pack has since grown to ten — a 4K desktop, a
greeter per desktop size, and an `greeter-active.png` the login screen points
at. Every file gets a row below, and every screen gets a check.

**A check passes only with a screenshot on disk and the resolution line that
produced it.** A tick without a file name is not a pass. Anything the VM
cannot offer — a 4K panel, for instance — is `BLOCKED`, never `PASS`.

## What ships

| File | Pixels | Where it is seen |
|---|---|---|
| `meta-wallpaper.png` | 1920×1080 | desktop, default |
| `meta-wallpaper-2560x1440.png` | 2560×1440 | desktop |
| `meta-wallpaper-3840x2160.png` | 3840×2160 | desktop, 4K |
| `meta-wallpaper-1366x768.png` | 1366×768 | desktop, small panel |
| `greeter-wallpaper.png` | 1920×1080 | login screen, default |
| `greeter-wallpaper-2560x1440.png` | 2560×1440 | login screen |
| `greeter-wallpaper-3840x2160.png` | 3840×2160 | login screen, 4K |
| `greeter-wallpaper-1366x768.png` | 1366×768 | login screen, small panel |
| `greeter-active.png` | a copy | what LightDM actually draws |
| `meta-grub.png` | 1920×1080 | GRUB, before anything else |

## Before the first boot

On the build machine, at the commit being tested:

```sh
python3 iso/tools/make_wallpaper.py --check      # every file, one command
```

Expected, one line per file and then the total:

```
wallpaper: theme/wallpaper/meta-wallpaper.png is current (1920x1080)
...
wallpaper pack: 10 file(s) current
```

Exit 1 names the stale or missing file. Do not boot a tree that fails this:
the screens will not tell you which file was wrong, only that something is.

In the VM, before capturing:

```sh
iso/tools/apply.sh --root / --verify             # 14 passed, 1 skipped
sha256sum /usr/share/metaos/theme/*.png          # keep this line with the shots
```

## 1. GRUB — `meta-grub.png`

Boot the ISO. When the menu appears, capture before the timeout.

- Expect: MetaOS in the menu, ring small and high, field at about a third
  brightness, lower two thirds quiet enough to read.
- Evidence: `screenshots/iso/H2-grub.png`
- Fail if: stock GRUB colours, a ring cut off at an edge, or the menu text
  sitting on the bright part of the field.

## 2. Greeter — four resolutions

LightDM runs `meta-greeter-setup.sh` before it draws. That script reads the
kernel's preferred mode and copies the matching file to `greeter-active.png`.
Set the VM display, log out (or boot), and capture at the login screen.

| VM display | Expect the active file to be | Evidence |
|---|---|---|
| 1920×1080 | `greeter-wallpaper.png` | `screenshots/iso/H4-greeter-1920x1080.png` |
| 2560×1440 | `greeter-wallpaper-2560x1440.png` | `screenshots/iso/H4-greeter-2560x1440.png` |
| 3840×2160 | `greeter-wallpaper-3840x2160.png` | `screenshots/iso/H4-greeter-3840x2160.png` |
| 1366×768 | `greeter-wallpaper-1366x768.png` | `screenshots/iso/H4-greeter-1366x768.png` |

Prove which file was chosen, do not infer it from the picture:

```sh
grep '^background=' /etc/lightdm/lightdm-gtk-greeter.conf
sha256sum /usr/share/metaos/theme/greeter-active.png \
          /usr/share/metaos/theme/greeter-wallpaper*.png
```

The hash of `greeter-active.png` must equal one of the pack, and the size must
be the one in the table above. The greeter log line says it outright:

```sh
grep 'greeter:' /var/log/lightdm/lightdm.log | tail -1
```

- Fail if: the hash matches the 1080p file on a 1440p or 4K screen, the ring
  is soft, or there are bands at the edges.
- A VM that cannot offer 3840×2160 makes that row `BLOCKED` with the reason,
  not skipped silently.

## 3. Desktop — four resolutions

Log in, set the display, then let the backdrop settle. The picker runs once
per login, so change resolution and log out/in rather than resizing live.

| VM display | Expect the backdrop to be | Evidence |
|---|---|---|
| 1920×1080 | `meta-wallpaper.png` | `screenshots/iso/H6-desktop-1920x1080.png` |
| 2560×1440 | `meta-wallpaper-2560x1440.png` | `screenshots/iso/H6-desktop-2560x1440.png` |
| 3840×2160 | `meta-wallpaper-3840x2160.png` | `screenshots/iso/H6-desktop-3840x2160.png` |
| 1366×768 | `meta-wallpaper-1366x768.png` | `screenshots/iso/H6-desktop-1366x768.png` |

Proof, in the session:

```sh
xrandr --current | grep ' connected'
xfconf-query -c xfce4-desktop -l | grep last-image
xfconf-query -c xfce4-desktop -p <the property above> -v
sha256sum /usr/share/metaos/theme/meta-wallpaper*.png
```

The property's value must be the file named in the table, not the 1080p
default.

- Fail if: the value is the default on a screen that has its own file, the
  ring is soft, or the panel and dock sit on a visible seam between two
  brightness steps.

## 4. The dock and panel, in the same shot

Not a wallpaper check, but the same capture proves them: five dock items,
one top bar, contract colours. If the bar is stock grey, the desktop shell
did not load — say so in the results table rather than blaming the image.

## Results

Copy this into the cut record and fill every row. `BLOCKED` needs a reason;
`PASS` needs a file name.

| # | Screen | Resolution | Expected file | Verdict | Evidence / reason |
|---|---|---|---|---|---|
| 1 | GRUB | 1920×1080 | `meta-grub.png` | | |
| 2 | Greeter | 1920×1080 | `greeter-wallpaper.png` | | |
| 3 | Greeter | 2560×1440 | `greeter-wallpaper-2560x1440.png` | | |
| 4 | Greeter | 3840×2160 | `greeter-wallpaper-3840x2160.png` | | |
| 5 | Greeter | 1366×768 | `greeter-wallpaper-1366x768.png` | | |
| 6 | Desktop | 1920×1080 | `meta-wallpaper.png` | | |
| 7 | Desktop | 2560×1440 | `meta-wallpaper-2560x1440.png` | | |
| 8 | Desktop | 3840×2160 | `meta-wallpaper-3840x2160.png` | | |
| 9 | Desktop | 1366×768 | `meta-wallpaper-1366x768.png` | | |

## What a pass here does not prove

- **Colour accuracy.** A screenshot goes through the VM's framebuffer and a
  PNG encoder. It shows the shape is right and the file is the right one; it
  does not measure `#1877F2` on the glass.
- **Scaling.** These checks prove the exact file is used at its own size. If
  someone plugs in a panel with a size the pack does not carry, the fallback
  is 1080p and will be soft — that is expected, not a failure, and should be
  written down as the fallback case.
- **The installed system.** A live session proves the lane; an installed disk
  proves Calamares carried it. The H+8 rows in
  `screenshots/iso/PROOF_PLAN.md` cover that, and this page does not replace
  them.
