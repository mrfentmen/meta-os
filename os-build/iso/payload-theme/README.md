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
