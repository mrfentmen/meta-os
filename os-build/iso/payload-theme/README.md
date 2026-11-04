# MetaOS 1.0 theme + shell tree (OpenCode 1 lane)

Branch: opencode1/theme-finish (from opencode1/metaos-1.0). Pax merges. Milo gates.
Brand kit: studio defaults locked until the boss says otherwise —
blue #1877F2, white #EDF5FF, black #070B16,
accents cyan #00C8FF, violet #8B5CF6, pink #FF4F9A, emerald #20D6A3, gold #FFBD4A.

Layout: greeter/ (LightDM gtk-greeter conf + validated keys),
splash/ (plymouth script-plugin theme), panel/ (Xfce top bar configs),
dock/ (Plank theme + launcher set), gtk/ (theme recolor), icons/ (Papirus
recolor script + exact file list), wallpapers/ (procedural originals),
fonts/ (licensed picks + license files), terminal/ (metafetch welcome + profile).
Proofs: VM screenshots per milestone under os-build/logs/OC1B-* style
naming (metaos- prefix).

## Status (theme-finish)

- [x] splash/ — plymouth script-plugin theme complete (descriptor + script +
      3 PIL-generated PNGs + INSTALL.md with alternatives --install/--set).
      Script references resolve; live-boot screenshot still pending
      (`screenshots/theme/H12-splash-boot.png` — named, not faked).
- [x] greeter/ — conf targets lightdm-gtk-greeter keys only; `background-color`
      (invalid) removed, logo wired via `default-user-image` (M mark);
      validated key set recorded in `KEYS.md` against the upstream template.
- [x] icons/ — recolor scoped to `places/{folder-blue*,user-blue-*}` with the
      two-tone map (`#5294e2`->`#1877F2`, `#4877b1`->`#1360C4`); exact 78-name
      list committed in `ICONS.md`, no binaries.
- [x] panel/ — Xfce top-bar XML, parsed + validated.
- [x] dock/ — Plank theme, validated.
- [x] gtk/ — CSS override, validated.
- [x] terminal/ — welcome hook + profile, shell-checked.
- [x] wallpapers/ — 3 procedural 4K PNGs (PIL originals) + generator.
- [x] fonts/ — Inter via apt (`fonts-inter`), no licensed binaries in tree.
- [x] apply.sh — installs greeter conf (fixed path), backgrounds + M mark,
      splash theme, plank, gtk, welcome hook; guarded plymouth activation.

Validation (this lane, no boots): XML parsed, INI-style confs key-checked,
`bash -n` on shell scripts, `python -m py_compile` on generators,
PIL verify on all PNGs, plymouth script `Image()` refs resolved,
no Apple/Ubuntu/Xubuntu marks in visible strings.

## Status (lane D, 2026-11-03)

- `apply.sh` rewritten: preflight gate (32 splash frames / 20 icons / 12
  dock launchers + every named source), absolute dest paths, `[ROOT]` arg
  for lane C (`./apply.sh /mnt`). Ran against `/tmp/metaos.ext4`;
  `theme_proof.sh` 10/10, md5 repo-vs-image 98/98 MATCH, report:
  `os-build/lanes/D_IDENTITY_REPORT.md`.
- `splash/frames/`: 32-frame spinning ribbon (480x272, downscaled from the
  settled `studio-loop-smooth` set `meta-live.py` plays at 16 fps);
  `metaos.script` preloads all 32 and steps ~15 fps; mirrored byte-identical
  to `os-build/iso/plymouth/metaos/`. Contact sheet:
  `os-build/lanes/D_plymouth_contact.jpg`. Boot capture is lane C's.
- `grub/`: `theme.txt` (Meta OS 1.0, timeout 10) + generated PNGs; lane C
  wires `GRUB_THEME`.
- `greeter/`: gtk-greeter conf (`icon-theme-name=metaos`) + new
  `unity-greeter.conf` for the installed greeter. Autologin is
  `autologin-user=meta` with `user-session=metaos`, matching the account
  `rename_user.sh` creates — when this said `ubuntu` and the account was
  `meta`, a rebuild landed on a greeter with no account to log into.
- `identity/`: os-release `Meta OS 1.0 (Ribbon)` / `ID=metaos`, hostname,
  issue, motd (symlink-preserving install).
- `icons/`: 20 glyphs + `index.theme` (`Inherits=Papirus,elementary-xfce,
  hicolor`) + `check-icons.sh` (98/98 resolve in image).
- `apps/dock/`: 12 launchers; all 17 dock-app Names resolve (5 pre-existing).
- `gtk.css`: Inter-first stack; terminal profile: Ubuntu Mono 11
  (`FONTS.md` records both licences, no binaries shipped).
- `metaos-theme/` left untouched (superseded tree, kept as-is).
