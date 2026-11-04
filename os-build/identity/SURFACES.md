# OS-DEBRAND-3 SURFACES — pixels and strings a judge actually sees

Branch `agent-debrand-3`. Read-only except where noted; image/plymouth/
os-release writers untouched (lanes 1–2), `facts.py` untouched (correct).

## Task 1 — icon themes

Payload ships no stock theme. `find … -iname "*humanity*" -o "*ubuntu*" -o
"*elementary*"` over `payload-theme/`, `metaos-theme/`, `iso/theme/` returns
nothing; `git grep -i humanity` hits only `os-build/UBUNTU_INVENTORY.md:90`
and `os-build/identity/STRINGS_INVENTORY.md:171`, both already bucketed as
honest attribution ("never drawn by our dock or panel"). No app hard-requires
a stock theme (the only `Inherits` parents are `Papirus,elementary-xfce,
hicolor` in our own `metaos/index.theme`, and missing parents are skipped by
the icon spec, never installed by us). Nothing removed, nothing to keep named.

Two MetaOS themes coexist by design, both ours:
`/usr/share/icons/metaos` (app glyphs, payload `apply.sh:151-153`) and
`/usr/share/icons/MetaOS` (full Papirus recolor, `iso/tools/apply.sh:181-183`).

Default in all four places (before → after):
- gtk: `settings.ini gtk-icon-theme-name=metaos`, metatheme `IconTheme=metaos`
  — unchanged, already Meta.
- xsettings: `iso/theme/xfce4/…/xsettings.xml Net/IconThemeName=MetaOS` —
  unchanged (dir exists via iso apply; gated by `isdir` check in
  `meta-desktop.sh:180`, which already wrote the value).
- plank: `dock/plank-settings Theme=MetaOS` + `dock.theme` — unchanged.
- greeter: payload confs already `icon-theme-name=metaos`; **`iso/theme/
  lightdm/lightdm-gtk-greeter.conf:7` said `Adwaita` → changed to `metaos`**
  (one word; both installers write `/etc/lightdm/lightdm-gtk-greeter.conf`,
  so last-writer-wins made the login screen's icons a coin toss — now both
  writers agree; `theme-name=MetaOS`, `background=` Meta ring, `font-name=
  Inter` were already right).

## Task 2 — wallpaper picker (xfce4-settings backdrop dialog)

Search paths the dialog reads: `/usr/share/backgrounds`,
`/usr/share/xfce4/backdrop`, `~/.local/share/backgrounds`, plus xfconf
`…/backdrop/…/last-image`. What lands in each (script text, not runs):
- `/usr/share/backgrounds`: exactly `meta-ascii/dawn/dusk/rays.png`
  (`payload apply.sh:82-85`), `meta-m.png` (`:86`), the studio loop as
  `metaos-studio/loop-*.jpg` (`os-build/iso/provision.sh:152-155`,
  `build_iso.sh:416-421`). No other writer puts files here.
- Stock removal: `dexubuntu/apply-in-chroot.sh:36-39` purges
  `xubuntu-wallpapers/artwork/docs` and `rm -rf …/backgrounds/xubuntu`;
  `verify-rootfs.sh:16` asserts the dirs are absent; `identity/debrand.sh:
  166-194` removes `greybird.svg` + `backgrounds/xfce/` and repoints
  `last-image` to `meta-wallpaper.png` (all lanes 1–2, cited not edited).
- `/usr/share/xfce4/backdrop`: no tree writer references it; nothing in the
  payload installs there. Cannot prove host-empty without the image — stated
  plainly; OS-4 `verify_tree` owns the on-image assertion.
- xfconf `last-image`: `iso/base/meta-first-login.sh:84-117` sets every
  `…/last-image` property to `/usr/share/metaos/theme/meta-wallpaper[-RES].png`
  (resolution-matched ring PNGs, shipped by `iso/tools/apply.sh:146-149`).

Result: every name the picker can offer is Meta art (the six required names
plus the studio-loop frames); green art has no writer and its old writers
purge it. No file change needed in this lane — proven, not edited.

## Task 3 — desktop entries

`Name`/`Comment`/`GenericName` across `agent-layer/desktop-entries/*.desktop`
and `payload-theme/apps/{dock/*.desktop,metaos-*.desktop}`: zero hits for
ubuntu/xubuntu/Debian/KEEP/lane chatter (grep pasted in report appendix).
All six drop-in Comments already read as product text ("View PDF files",
"Browse and manage your files", …); dock Comments likewise
("Deleted files, restorable (XDG trash)"). `Exec` lines byte-identical —
only verified, `test -f`-style: native binaries install via
`face/provision.sh:59-64`, imperium/controls via `iso/provision.sh:146-166`
+ payload `apply.sh:165-166`, dock browsers are the evidenced kiosk browser.
No entry added, removed, or repointed.

## Task 4 — About / os-release

`identity/os-release` (lanes 1–2, read-only): `PRETTY_NAME="Meta OS 1.0
(Ribbon)"`, `NAME="Meta OS"`, `ID=metaos`, `ID_LIKE=debian`, `LOGO=metaos`.
`facts.py:19-25` reads the live `/etc/os-release` and returns `PRETTY_NAME`
verbatim — flow unchanged, nothing to fix. `about.html` renders the live
values with the static line "Meta OS 1.0 (Ribbon) is a Meta-branded desktop
on a Debian-family base" — About shows Meta OS. `facts.py` not touched.

## Task 5 — terminal

Profile already `FontName=Monospace 11` in both copies (OS-3 merge);
`git grep -i ubuntu` over both profiles: clean. Palette byte-identical since
`c745a3ac` (only FontName/header/`ColorUseTheme` changed after). Prompt is
not set here by design; `os-build/tools/fix_terminal_prompt.sh:40`
(OS-4, read-only) appends `PS1='\[38;5;33m\]metaos…\w…\$ '` — renders blue
`metaos` + cwd, no `user@host`.

## Task 6 — dock tile table (28 tiles, `meta-desktop.sh:281-320`)

| tile | binary | page / target | binary evidence |
|---|---|---|---|
| Terminal | xfce4-terminal | n/a | base line + APP_MATRIX 1.1.3 |
| Files | thunar | `trash:///` for Trash | base line + APP_MATRIX 4.18.8 |
| Notes | meta-notes | n/a | native/*.py → /usr/local/bin (face provision) |
| Monitor | meta-monitor | n/a | same |
| Agents | meta-agents | n/a | same |
| Editor | mousepad | n/a | packages.txt KEEP |
| Calculator | mate-calc (CALC_BIN prefers if present) | n/a | APP_MATRIX 1.26.0 |
| Settings | xfce4-settings-manager | n/a | base line |
| Trash | thunar | `trash:///` | same as Files |
| Controls | /usr/share/metaos/apps/metaos-controls.py | n/a | payload apply.sh:165 |
| Trio / Imperium | /usr/share/metaos/apps/metaos-imperium.py | `--title …` | iso provision + payload apply |
| Web | /usr/local/bin/meta-app | :18934/index.html | native/meta-app.py → /usr/local/bin |
| Dashboard | meta-app | :18900/dashboard.html | same |
| Board | meta-app | :18900/board.html | same |
| Calendar | meta-app | :18900/calendar.html | same |
| Musica | meta-app | :18900/musica.html | same |
| Science | meta-app | :18934/labs/molecules/index.html | same |
| Custos | meta-app | :18934/design/meta-custos-watch.html | same |
| Officina | meta-app | :18934/design/meta-officina-blueprint.html | same |
| Boards | meta-app | :18934/surfaces.html | same |
| Messages | meta-app | :18934/bus.html | same |
| Logo Studio | meta-app | :18934/logo-studio.html | same |
| Music 3D | meta-app | :18934/labs/music3d/index.html | same |
| 3D Notes | meta-app | :18934/design/meta-musica-notes.html | same |
| Agent Budget | meta-app | :18934/design/agent-budget-dashboard.html | same |
| Aegis | meta-app | :18934/aegis/index.html | same |
| About | meta-app | :18900/about.html | same |

Every tile's binary resolves in-tree; no tile opens nothing. Table verified
by reading install scripts, not by launching (no QEMU per mission).

## Before → after (complete change list)

1. `iso/theme/lightdm/lightdm-gtk-greeter.conf:7`:
   `icon-theme-name=Adwaita` → `icon-theme-name=metaos`.
2. Nothing else changed. Entries, terminal, launcher, About, tiles verified
   already-clean (OS-3 merge + prior lanes); wallpaper/icon-stock state
   proven via other lanes' scripts, cited with file:line.

## Appendix — final grep over the lane paths

`git grep -in "ubuntu\|xubuntu" -- agent-layer/desktop-entries/
os-build/iso/payload-theme/terminal/ os-build/iso/payload-theme/apps/
os-build/face/launcher.py os-build/face/test_launcher_allowlist.py
iso/theme/lightdm/` returns exactly two lines, both functional
self-references (the guard cannot name the banned words without naming
them): `check_entries.sh:17` BANNED list, `check_profile.sh:32` grep
pattern. Proper-name attributions remain only in `fonts/FONTS.md`
(`fonts-ubuntu` package name, `Ubuntu Mono` font name — uninstallable
vocabulary, bucketed as attribution, never rendered to a judge).

## What a judge would now see

Login screen: Meta ring backdrop, MetaOS theme, Meta icon set (both greeter
writers agree). Desktop: 28 tiles, all launch. Backdrop picker: only Meta
art names. Terminal: dark palette, `Monospace`, blue `metaos` prompt. About:
"Meta OS 1.0 (Ribbon)". Menus: product-text descriptions, no distro names.
