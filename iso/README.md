# iso/ — the MetaOS 1.0 lane

Everything that becomes the ISO. Four screens, one palette, and a checker that
refuses to let them disagree.

## The four surfaces

The machine shows the ring four times before anyone logs in. Each is separate,
and each is generated from `contracts/tokens.json`:

| Surface | Built from | Lives in |
|---|---|---|
| Boot menu | `tools/tokens_to_grub.py` | `boot/grub/` |
| Splash | `plymouth/metaos/` | `plymouth/` |
| Installer | `calamares/` | `calamares/` |
| Login | `tools/tokens_to_gtk.py` | `theme/lightdm/` |
| Desktop | `tools/make_wallpaper.py`, `tools/tokens_to_gtk.py` | `theme/` |

`contracts/tokens.json` is vendored from `opencode1/metaos-1.0` and pinned by
sha256 in `contracts/PIN.md`. Changing a colour means changing the pin, and
then the checker will make every surface regrow from it.

## Directories

| Path | What it is |
|---|---|
| `base/` | package manifest, first-login step, doctor |
| `boot/` | GRUB theme and the drop-in that selects it |
| `calamares/` | installer branding, module order, preseeded answers |
| `apps/` | five launchers, five dock items, Chromium policy and start page |
| `plymouth/` | splash descriptor, script and ring asset |
| `theme/` | wallpapers, GTK sheet, login screen |
| `contracts/` | the frozen palette and its pin |
| `tools/` | generators, the static checker, the installer, the gate, the boot kit |

## Commands

```
iso/tools/check_iso_config.py            static checks, 92 of them
iso/tools/check_iso_config.py --json     same, machine readable
iso/tools/verify_lane.sh                 checker plus every test; says LANE GREEN

iso/tools/apply.sh --root DIR            install the lane into a chroot or a staging tree
iso/tools/apply.sh --root DIR --verify   install, then run the doctor on it
iso/tools/apply.sh --root DIR --revert   remove exactly what the last run wrote

iso/tools/boot_kit.sh --check            what the boot machine is missing
iso/tools/boot_kit.sh --build --out DIR  userspace, kernel, builder, image
iso/tools/boot_log_verdict.py boot.txt   PASS/FAIL rows for a serial log
```

## Proofs

The lane owes one screendump per cut, named in `screenshots/iso/PROOF_PLAN.md`.
None exist: they need a VM, and this machine has none. The plan lists the
exact file, what it proves, and the command that produces it, so the boot run
on the 32GB MacBook can fill the table instead of guessing at filenames.

## What a green run means

A green `verify_lane.sh` means the files are well formed, point at things that
exist, and the generators produce exactly what is committed. It does not mean
anything has booted. Nothing on this machine can boot a VM, so every visual
claim in this lane is CODE-INSPECTED until the 32GB MacBook runs
`os-build/BOOT_ON_32GB_MAC.md` and someone looks at the screen.
