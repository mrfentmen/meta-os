# MetaOS plymouth splash — install notes

Theme dir `metaos-theme/splash/` is a **script-plugin** plymouth theme.
Descriptor header is `[Plymouth Theme]` (space, no dash), matching the
upstream `.plymouth` layout and the script-module options
`ImageDir` / `ScriptFile` under `[script]`.

## Files

| file | role |
|---|---|
| `metaos.plymouth` | descriptor: `Name=MetaOS`, `ModuleName=script`, absolute `ImageDir` + `ScriptFile` |
| `metaos.script` | script-plugin program; references `background.png`, `meta-m.png`, `progress.png` (all in this dir) |
| `background.png` | 1920x1080 splash backdrop — `wallpapers/meta-rays.png` downscaled (LANCZOS), same pixels |
| `meta-m.png` | 512px transparent original M mark (white stems + `#1877F2` chevron), PIL-drawn |
| `progress.png` | 560x28 Meta-blue bar (`#1877F2` + `#78BAFF` edge, same tokens as `gtk/gtk.css`) |
| `generate-splash.py` | provenance: regenerates all three PNGs (PIL only, no external art) |

Regenerate: `python3 metaos-theme/splash/generate-splash.py`

## Install (root, on the target or Cubic chroot)

```sh
sudo mkdir -p /usr/share/plymouth/themes/metaos
sudo install -m644 metaos-theme/splash/metaos.plymouth \
  metaos-theme/splash/metaos.script metaos-theme/splash/background.png \
  metaos-theme/splash/meta-m.png metaos-theme/splash/progress.png \
  /usr/share/plymouth/themes/metaos/
sudo update-alternatives --install \
  /usr/share/plymouth/themes/default.plymouth default.plymouth \
  /usr/share/plymouth/themes/metaos/metaos.plymouth 100
sudo update-alternatives --set default.plymouth \
  /usr/share/plymouth/themes/metaos/metaos.plymouth
sudo update-initramfs -u
```

`metaos-theme/apply.sh` performs the file installs plus the guarded
`update-alternatives` / `update-initramfs` activation when both tools exist.

## Verify (no boot needed)

```sh
update-alternatives --query default.plymouth          # must point at .../metaos/metaos.plymouth
plymouth-set-default-theme --list 2>/dev/null | grep -x metaos
lsinitramfs /boot/initrd.img-$(uname -r) | grep 'plymouth/themes/metaos/'
```

## Needs a live boot (NOT validated in this lane)

Live-boot screenshot of the splash on bare metal or VM — named, not faked:
`screenshots/theme/H12-splash-boot.png` (progress bar visible mid-boot).
No QEMU/VM boots are run from this lane; first live-boot confirmation is pending.

## Ribbon animation (lane D)

`frames/` holds the 32-frame spinning ribbon (480x272 PNGs downscaled from
`../wallpapers/studio-loop-smooth/`, the set `meta-live.py` plays at 16 fps).
`metaos.script` preloads all 32 and advances one frame per 4 refresh ticks
(~15 fps at 60 Hz). `generate-frames.py` rebuilds the set; `frames.inc`
records the inlined preload block. Install the whole dir including `frames/`.
