# AGENT OS-3 REPORT — user session, defaults, launcher, entries, fonts

Worktree `/tmp/agent-os-3`, branch `agent-os-3` (from `main` f64588bb).
No QEMU, no sudo, no mount, no docker, no apt, no `fc-cache` (none possible
on this host anyway). No temp files left under the repo tree (all scratch in
`/tmp`: `/tmp/pb`, `/tmp/entries-broken`, `/tmp/profile-broken`,
`/tmp/check-broken.sh` — since removed where trivial).

## Baseline tables (tasks 1–8, recorded before any edit)

### 1. Terminal profile (before)

`os-build/iso/payload-theme/terminal/metaos-terminal-profile.txt` (12 lines):
Ubuntu-named things: comment line 2 (`Font: Ubuntu Mono (Ubuntu Font Licence
1.0, package fonts-ubuntu …)`), value line 12 (`FontName=Ubuntu Mono 11`).
Rest: bg `#070B16` @0.92, fg `#EDF5FF`, 16-colour palette on Meta blue
`#1877F2`. (`metaos-theme/terminal/…` copy already said `FontName=Monospace 11`
— the two copies disagreed; fixed by unifying.)

### 2. Launcher allowlist (before)

`os-build/face/launcher.py` ALLOW: `thunar`, `xfce4-terminal`, `mousepad`,
`thunderbird`, `mate-calc`, `firefox` → binaries of the same names (firefox
adds `--new-window about:blank`). Ubuntu-specific marks: docstring
`Xubuntu 24.04.5 base`, `Ubuntu shim`; entries `thunderbird`/`firefox` are
snap-distributed (Ubuntu mechanism) but version-evidenced present
(APP_MATRIX.md: thunderbird `2:1snap1-0ubuntu3`, firefox
`1:1snap1-0ubuntu5`, "default Xubuntu browser"). Not removed: removal would
kill the only browser and the only calendar-capable native app; the brief's
removal rule targets entries for programs *not installed*, and these are.

### 3. Desktop entries (before → after: only Comment lines changed + README)

| file | Name (menu shows) | Exec | Icon | person sees |
|---|---|---|---|---|
| atril.desktop | Atril | `atril %U` | accessories-document-viewer | PDF viewer |
| evince.desktop | Evince | `evince %U` | accessories-document-viewer | nothing (NoDisplay=true, deliberate) |
| meta-agent-status.desktop | Agent Status | `meta-agent-status` | utilities-system-monitor | agent layer status |
| mousepad.desktop | Mousepad | `mousepad %U` | accessories-text-editor | text editor |
| ristretto.desktop | Ristretto | `ristretto %U` | accessories-image-viewer | image viewer |
| thunar.desktop | Files | `thunar %U` | system-file-manager | file manager |

Comment fixes: stripped `Xubuntu 24.04.5` / `KEEP … Hana ack` / lane pointers
from all five editable Comments (user-visible strings); `meta-agent-status`
untouched (byte-copy of Bond's `iso/apps/desktop/meta-agent-status.desktop`,
enforced by `tests/agent-layer/test_desktop_entries.py`).

### 4. Font references in my paths (before)

`Ubuntu Mono` (terminal profile ×2 lines, both FONTS.md, launcher docstring
context, `metaos-theme/fonts/FONTS.md`), `Ubuntu` licence/name mentions in
FONTS.md + entries README + mimeapps comment. No `Ubuntu Light` / `Ubuntu
Condensed` anywhere. Nothing breaks by removal: terminal now uses the
fontconfig `Monospace` alias (DejaVu Sans Mono via `fonts-dejavu-core`,
evidenced in `iso/base/metaos.packages`).

### 5. Fonts installed in the image (tree evidence only)

`fonts-inter` (packages.txt ADD + metaos.packages + apply.sh:162),
`fonts-ubuntu` (apply.sh:162 + theme_proof D7 gate), `fonts-dejavu-core`
(metaos.packages). `fc-list`/`fc-match` do **not** exist on this build
machine — resolution is proven by package evidence, stated as such, not by
running them here. If the package lists lie, the D7 gate catches it on target.

### 6. `git grep -in ubuntu` in my paths, bucketed

- After my edits, zero hits in: terminal/, apps/, launcher.py,
  desktop-entries/ (all files).
- Remaining, both copies of FONTS.md: `Ubuntu Mono` / `fonts-ubuntu` —
  **honest attribution**: the installed package and the font's proper name
  cannot be named without the word. Bucket: required proper noun, not a leak.
- Dead comment / compat: none left in my paths.

### 7. The three judge-visible items (task 8 — all fixed or requested)

1. **Terminal font named Ubuntu** — profile said `Ubuntu Mono`; fixed to
   `Monospace 11` in both copies. Live `terminalrc` + proof assertion still
   say it → cross-lane requests below.
2. **Dead Calculator tile** — dock entry ran `galculator` (matrix-proven
   absent); image ships `mate-calc` 1.26.0. Fixed to `mate-calc`.
3. **Lane chatter in user-visible strings** — `Comment=` fields and the
   mimeapps comment named Xubuntu/KEEP/Hana/OC-teams. User-facing fields now
   plain descriptions; decision history stays in READMEs, not in the menu.

## Changes

- `terminal/metaos-terminal-profile.txt` (both copies, byte-identical):
  `Monospace 11`, `[Configuration]` + `ColorUseTheme=FALSE` to match the live
  terminalrc key set, header comment naming the install path/reader, explicit
  cursor/scrollback non-statement. No colours changed (all values byte-kept).
- `terminal/README.md` (new): install path, reader, missing-file behaviour,
  prompt ownership + exact rendered prompt string.
- `terminal/check_profile.sh` (new, `--check`): parses both copies,
  rejects duplicates/unknown keys/non-`key=value` lines/Ubuntu strings,
  requires 4 keys, asserts copies identical. Passes (exit 0, pasted below);
  fails loudly on a broken fixture (exit 1, pasted below).
- `os-build/face/launcher.py`: docstring de-Ubuntu'd (facts kept); 403 now
  names the app (`not allowed: <app>`); 500 now names the binary
  (`not installed on this image: <binary>`); `GET /apps` computed via
  `shutil.which` at request time (unresolvable apps omitted, never listed).
  Wire format unchanged: `POST /launch {"app"}` → `{"ok": bool, …}`;
  `shell.html` reads only `r.ok` (verified lines 158–165); `/apps` is
  additive (no page fetches it yet).
- `os-build/face/test_launcher_allowlist.py` (new, `--check`): fake-PATH
  proof against the real handler — 5/5 PASS, pasted below.
- `agent-layer/desktop-entries/`: 5 Comments rewritten (plain descriptions);
  mimeapps comment `Xubuntu` → `base ISO` (mappings byte-identical, existing
  validator still 7/7 green); dock calculator `galculator` → `mate-calc`;
  `check_entries.sh` (new, `--check`) — passes on tree, fails on broken
  fixture (both pasted below); `README.md` one-word fix.
- `os-build/iso/payload-theme/apps/README.md` (new): one line per app, no
  marketing; documents the 12-dock gate and the epiphany/kiosk evidence.
- `fonts/FONTS.md` (both copies, identical): installed / referenced /
  missing table with tree evidence per row, fallback chain, spelling
  reference, honest `fc-list`-absent statement.

Declined with reason (not skipped silently): renaming entry `Name=` values to
"Meta names" (no Meta names for viewers/editors exist anywhere in the tree or
the identity contract — inventing them would be worse; `Files` precedent
noted); removing `evince.desktop`/`meta-agent-status.desktop` (existing
validator + OC1 handoff contract require them; evince already `NoDisplay`);
editing `meta-agent-status.desktop` at all (byte-copy rule); adding
cursor/scrollback keys to the profile (provision's real terminalrc doesn't
set them — inventing keys is fabrication).

## Proof transcripts (ran and saw)

`check_profile.sh --check` → `OK` ×2 + `both copies identical`,
`failures=0`, exit 0. Broken layout (`BogusKey`, bare line, duplicate
`FontName`, Ubuntu string, copies differ) → 7 FAIL lines, exit 1.
`test_launcher_allowlist.py --check` → all 5 PASS (`apps` computed
`[…5 live…]`, 403 names `snap-store`, 500 names `mate-calc` +
`not installed on this image`, present app 200), exit 0.
`check_entries.sh --check` → 6 OK, exit 0; broken fixture (missing Comment/
Categories/TryExec mismatch/banned words) → 5 FAIL lines, exit 1.
`tests/agent-layer/test_desktop_entries.py` → 7 passed before and after.
`sh -n` clean on both new scripts; `python3 -m py_compile` clean on both
launcher files. `test -f` pastes: `payload-theme/icons/metaos/imperium.png`
EXISTS, `calculator.png` EXISTS; drop-in icons are theme names resolving via
`papirus-icon-theme` (metaos.packages, desktop-shell lane) — no tree files to
`test -f`, stated plainly. Full page+data fetch analogue: n/a (no network
service in this lane); all checks are file-local.

## Read, not run (the line is not blurred)

Binary presence (thunar/xfce4-terminal/mousepad/mate-calc/thunderbird/
firefox/atril/epiphany) rests on APP_MATRIX.md version strings, packages.txt
KEEP lines, metaos.packages base line, SESSION.md epiphany 46.5 + guest
window log — convergent tree evidence, none of it re-executable here by
design (no QEMU/mount). `meta-agent-status` binary has NO install evidence in
tree → tabled UNKNOWN (kept: byte-copy + validator forbid changes).
`ristretto`/`atril` versions unrecorded → tabled as evidenced-but-unversioned.
Prompt rendering read from `fix_terminal_prompt.sh:40`, not executed here.

## Cross-lane requests (exact lines, no edits made)

1. Buffy, `os-build/face/provision.sh` terminalrc block (`FontName=Ubuntu
   Mono 11`, ~line 190): change to `FontName=Monospace 11`, or the live
   default reintroduces the name my profile removes.
2. Buffy, `os-build/iso/payload-theme/theme_proof.sh:187`
   (`grep -q '^FontName=Ubuntu Mono 11'`): change to `^FontName=Monospace 11`,
   or the proof fails on the new installed copy.
3. Buffy, `os-build/face/meta-desktop.sh:287` (`add_app calc …
   galculator`): change to `mate-calc` (galculator absent per APP_MATRIX;
   mate-calc 1.26.0 present).
4. Buffy, `os-build/iso/payload-theme/README.md:66` (`terminal profile:
   Ubuntu Mono 11`): change to `Monospace 11`.
5. Bond/OS-4: confirm where the `meta-agent-status` binary is installed
   (no evidence in tree; entry kept per byte-copy rule either way).
6. OS-4 `verify_tree.sh`: please call `…/terminal/check_profile.sh --check`,
   `agent-layer/desktop-entries/check_entries.sh --check`, and
   `python3 os-build/face/test_launcher_allowlist.py --check` by these paths;
   treat missing as `absent`, never as pass.
7. OS-1: no action needed from OS-3's side; noting that
   `payload-theme/identity/os-release` carries `ID_LIKE="ubuntu debian"` +
   `UBUNTU_CODENAME` (your call per the identity contract) and the live user
   in SESSION.md is still `ubuntu` (prompt itself already fixed by OS-4's
   tool).

## Definition-of-done check

- No `ubuntu` in terminal profile, entries, or launcher messages (grep
  clean; only proper-name package/font attributions remain in FONTS.md).
- Every `Icon=`/`Exec=` I ship resolved in-tree or in package evidence
  (past tables above; `imperium.png`/`calculator.png` via `test -f`).
- `/apps` reports computed truth; 403/500 still refuse loudly, now with names.
- Report separates ran-vs-read (sections above).

## Commits

- `5b244a40` OS-3: userland defaults — terminal, launcher, entries, fonts
  (19 files, all in-lane, on `agent-os-3`; this report included).
- `os-build/face/test_launcher_allowlist.py` sits beside the owned
  `launcher.py` in `os-build/face/` per the task's "script under your paths"
  order — Buffy, move it if it collides with the desktop rewrite.
- No merge, no rebase, no push, no `--force`.
