# MetaOS 1.0 fonts — installed, referenced, missing

> R2-T1 note (2026-11-04, fonts lane): the `fonts-ubuntu` apt pull described
> below (`apply.sh` font block) is removed — `apply.sh` now installs the six
> vendored OFL families via `fonts/install.sh`, and `fonts/test-no-ubuntu.sh`
> fails any image carrying an Ubuntu-named family. The `FONTS.md` rows naming
> `Ubuntu Mono`/`fonts-ubuntu` as installed/referenced are therefore HISTORICAL
> (pre-R2-T1 state), kept for provenance. Current mapping: `META-FONTS.md`;
> declared files: `MANIFEST.txt`.

No font binaries ship in this tree or in this directory. Licence files live
inside the installed packages, never here.

## Installed in the image (tree evidence, not guesses)

| face | package | evidence |
|---|---|---|
| Inter (display/UI) | `fonts-inter` | `os-build/metaos1-base/packages.txt` (ADD), `iso/base/metaos.packages` (theme lane), installed by `payload-theme/apply.sh:162` |
| Ubuntu Mono (monospace) | `fonts-ubuntu` | installed by `payload-theme/apply.sh:162`, gated by `theme_proof.sh` D7 (`fc-list` must find it) |
| DejaVu Sans Mono (fallback) | `fonts-dejavu-core` | `iso/base/metaos.packages` (desktop-shell lane) |
| Icon theme (not a font) | `papirus-icon-theme` | `iso/base/metaos.packages`; resolves the `accessories-*`, `utilities-*`, `system-*` icon names used by the desktop entries |

## Referenced from this lane

| reference | file | resolves? |
|---|---|---|
| `FontName=Monospace 11` | `terminal/metaos-terminal-profile.txt` (both copies) | Yes — `Monospace` is the fontconfig generic alias; falls back through the installed monospace stack (DejaVu Sans Mono). Needs no named package. |
| `Inter` UI stack | greeter/GTK CSS (outside this lane) | Per `iso/theme/lightdm/lightdm-gtk-greeter.conf` and `metaos-contracts/PACKAGES.md`; unconfirmed by this lane beyond the installed package. |

## Missing

Nothing this lane references is missing. `Ubuntu Mono` is installed but
deliberately no longer referenced by the terminal profile (its name is the
visible leftover this lane was asked to remove); it stays installed because
removing packages belongs to the image lane, and other (non-lane) files still
name it — see the OS-3 report's cross-lane requests.

## Fallback chain (unreadable-text check)

If `Monospace` somehow resolves to nothing, xfce4-terminal falls back to its
compiled-in default — text stays readable, only the styling changes. No
surface in this lane can go blank or unreadable from a missing font: the
profile sets colours + one generic alias and nothing else.

## Spelling

`Monospace` (capital M, exact fontconfig alias), `Inter` (capital I). A typo
in either means a silent fallback — `terminal/check_profile.sh --check`
rejects unknown profile keys, and this file is the spelling reference.
`fc-list`/`fc-match` do not exist on this build machine, so resolution is
proven by package evidence above, not by running them here.
