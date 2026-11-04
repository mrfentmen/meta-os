# WALLPAPERS — no stock desktop may ever paint green again

Three separate fallback paths all ended at stock art (verified on
`/tmp/metaos.ext4`, read-only mount). The payload never shipped these files,
so there is no payload copy to delete — the image side is the only copy and
`debrand.sh` removes it there. What the payload *does* carry is the Meta art
that replaces each fallback, listed at the bottom.

## Removed from the image (by `debrand.sh --apply`)

| path on the image | why it went | what replaced it |
|---|---|---|
| `/usr/share/xfce4/backdrops/greybird-wall-1920x1200.png` | Xubuntu's green-grey default; it is what xfdesktop falls back to when the configured backdrop is missing or not yet resolved. This is the green wallpaper the boss kept seeing. | Nothing: the file is deleted. xfdesktop's configured backdrop (`meta-wallpaper.png`) is installed by the image build, so the fallback path goes cold. |
| `/usr/share/desktop-base/*-theme/wallpaper` and `*/wallpaper-withlogo` (emerald, moonlight, softwaves, spacefun, joy, joy-inksplash, homeworld, futureprototype, tribar, and any other `*-theme` dir) | Ten Debian theme paint sets nothing in the tree references (repo-wide grep for `desktop-base/` theme paths finds only comments). Only stock settings apps read them. | Nothing: the paint dirs are deleted. Theme shells (metadata, grub subdirs) stay so package/alternatives bookkeeping is untouched. |
| `/usr/share/backgrounds/warty-final-ubuntu.png` (regular file) | Carries Ubuntu's name on a path the greeter schema default still names. Content was already Meta ink, but the name is the leak. | A symlink `warty-final-ubuntu.png -> meta-ink.png` in the same directory. The symlink stays because the gsettings schema default (`99_metaos-greeter.gschema.override` documents this history) and `provision.sh` both still name the old path. If face provision runs after debrand it replaces the link with a regular file of identical Meta bytes — still no green. |
| `/usr/share/plymouth/themes/*` except `{metaos, text, details, spinner, metaos-text}` — i.e. emerald, joy, and every `ubuntu*` theme | Dead weight with third-party names; emerald is bright green at boot. | `metaos` (ours, stays the default via `plymouthd.conf`), `metaos-text` (new: `[Plymouth Theme] ModuleName=text`, created by debrand), `text` + `details` (text-mode fallbacks when KMS fails — deleting them would leave an unreadable boot), `spinner` (minimal graphical fallback some units reference). |
| `/etc/alternatives/text.plymouth` (old target) | Pointed at `ubuntu-text`, which the loop above deletes — a dangling boot-text alternative. | Re-pointed (symlink) at `/usr/share/plymouth/themes/metaos-text/metaos-text.plymouth`. Direct symlink, not `update-alternatives --set`: the build root is not `/`, and the alternatives database entry for the deleted theme is stale-but-harmless. |
| `/usr/share/plymouth/themes/ubuntu-text/` (and every other `ubuntu*` theme dir) | Ubuntu boot art; the `ubuntu-text` alternative target. | Deleted; covered by the loop above and the pre-existing check. |

Notes on what was deliberately NOT done:

- The `desktop-base` theme *shells* stay. Ripping whole package-owned
  theme dirs risks the `desktop-background` alternatives bookkeeping that
  other tooling may still query; the paint (what can show on screen) is all
  gone, which is what the mission requires.
- `os-build/iso/payload-theme/greeter/99_metaos-greeter.gschema.override`
  still mentions the old warty background in a comment. That comment is the
  honest history of *why the override exists* and why the warty symlink
  stays; it is not painted anywhere. Left alone.
- `os-build/face/provision.sh` still installs Meta ASCII bytes *at* the
  warty path (face lane's file; not edited). Bytes are identical to
  `meta-ink.png`, so either order of debrand-vs-provision ends green-free.

## Remaining wallpapers (`/usr/share/backgrounds/` after a build)

| file | what it is |
|---|---|
| `meta-ascii.png` | ASCII-art Meta logo in Meta blue on ink. Greeter background (`lightdm-gtk-greeter.conf`) and the byte source of `meta-ink.png`. |
| `meta-ink.png` | Same bytes as `meta-ascii.png`, under the name the greeter fallback path resolves to. The warty symlink points here. |
| `meta-rays.png` | Blue sunburst rays on ink. Unity-greeter background (schema override). |
| `meta-dusk.png` | Near-black ink with faint vertical pinstripes. |
| `meta-dawn.png` | Ink with faint blue-grey vertical pinstripes. |
| `meta-m.png` | The Meta mark. Greeter logo and default user avatar. |
| `meta-wallpaper.png` | The desktop backdrop xfconf points at (installed by the image build). |
| `warty-final-ubuntu.png` | Symlink → `meta-ink.png` (see above; name kept only because the schema default and provision.sh still reference it). |

GRUB (`payload-theme/grub/`): `theme.txt` names only `background.png`
(ink-blue rays, Meta) and `mark.png`; no Ubuntu art, no change needed.
Greeter (`lightdm-gtk-greeter.conf`): `background=/usr/share/backgrounds/meta-ascii.png`,
verified present in the payload; left alone per task 6.
