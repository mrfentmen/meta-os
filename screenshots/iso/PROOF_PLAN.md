# Proof plan — iso lane

`metaos-contracts/PROOFS.md` asks for `screenshots/<lane>/H<n>-<what>.png`
plus HMP screendumps, one set per cut. This is the list this lane owes and
the command that produces each one.

**None of these exist.** No VM has run on the machine that wrote this lane, so
every row is BLOCKED on the same thing: one boot on the 32GB MacBook
(`os-build/BOOT_ON_32GB_MAC.md`). No placeholder image is committed: a blank
PNG in this directory would be a lie Milo cannot detect from the filename.

| Cut | File | What it proves | How to produce it |
|---|---|---|---|
| H+2 | `H2-grub.png` | the boot menu reads MetaOS and is not stock GRUB | screendump before the kernel loads |
| H+2 | `H2-splash.png` | Plymouth draws the ring, not a text console | screendump while booting |
| H+4 | `H4-greeter.png` | LightDM shows the MetaOS backdrop and theme name | screendump at the login screen |
| H+6 | `H6-desktop.png` | wallpaper, dock with five items, panel | screendump after login |
| H+8 | `H8-installer.png` | Calamares runs with the Meta branding and slideshow | screendump inside the live session |
| H+8 | `H8-installed.png` | an installed disk reboots to the greeter | screendump after first restart |
| H+10 | `H10-doctor.png` | `meta-doctor` prints `0 failed` on the installed system (the row count moves as rows are added, so the shot is the proof, not a number quoted here) | terminal capture |
| H+12 | `H12-boot.png` | the final ISO boots from cold | screendump |

## Before any capture

```
iso/tools/boot_kit.sh --check          # names every missing tool
iso/tools/apply.sh --root <chroot> --verify
```

A boot that reaches the greeter without `apply.sh` having run proves the base
image boots, not that this lane works. Both are needed.

## Wallpapers, per screen

`os-build/WALLPAPER_BOOT_CHECK.md` covers every wallpaper file at its own
resolution: `H2-grub.png`, `H4-greeter-<WxH>.png`, `H6-desktop-<WxH>.png`.
Those shots belong to the same cuts as the rows above; this plan lists the
cut-level ones, that page lists the per-screen ones.
