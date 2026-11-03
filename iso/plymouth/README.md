# MetaOS Plymouth splash

One blue ring on ink black, the name under it, pulsing with boot progress.
Original art: `ring-dot.png` is ours (24×24), no Apple asset anywhere.

**Label: CODE-INSPECTED.** Written and statically checked here. It has not
been booted — this Mac has no QEMU, and the plan's boot proof runs in the
base lane's VM. Nothing here claims a splash was seen on screen.

## Files

| File | What it is |
|---|---|
| `metaos/metaos.plymouth` | theme descriptor (INI): name, module, script paths |
| `metaos/metaos.script` | the splash itself: ring sprite, title, progress fade |
| `metaos/ring-dot.png` | the ring, 24×24 RGBA |

## Install into the base (Hana's Cubic project)

```sh
install -d /usr/share/plymouth/themes/metaos
install -m 644 metaos/metaos.plymouth metaos/metaos.script metaos/ring-dot.png \
    /usr/share/plymouth/themes/metaos/
plymouth-set-default-theme -R metaos
```

`-R` rebuilds the initramfs, which is what makes the splash show before
root is mounted. Without `-R` the theme is set but the early boot still
draws the old one.

## What the script does, plainly

- Background: `#0b1118` top to `#05080c` bottom (ink black).
- Ring: centred, 24 px above centre, opacity 0.72 ± 0.18, sine pulse.
- Title: "MetaOS" at 0.961/0.969/0.980 white, 24 px below centre, opacity
  rises with real boot progress (0.55 → 1.0). A stalled boot looks stalled.

## Check it without booting

```sh
python3 iso/tools/check_iso_config.py
```

That parses the descriptor, checks every `Image("…")` the script names
exists in the theme dir, and checks the script's braces balance. It cannot
tell you the splash looks good — only a boot can.
