# R2-T1 REPORT — offline type, identity, boot surface, image build

Branch `agent-r2-t1`, worktree `/tmp/agent-r2-t1`. No QEMU (never run —
`pgrep -f qemu-system` → exit 1, `METAOS_ALLOW_QEMU` unset). No sudo, no
mount, no docker reads. `debugfs` does not exist on this host, so the live
image was never opened; package facts come from `/tmp/fs.manifest` (1876
lines, labelled as such everywhere). Main untouched (tip `f025d3a5`).

## Section A. Fonts in the image (1-18)

- Base manifest fonts (`grep -i font /tmp/fs.manifest`, first/last):
  first: `fontconfig ... fonts-droid-fallback fonts-liberation ...`
  last: `... fonts-urw-base35`. Full list in `fonts/META-FONTS.md`.
  Xubuntu-layer fonts kept deliberately: `fonts-dejavu-core`,
  `fonts-liberation*`, `fonts-noto*` (coverage, not branding).
- Chosen six (all OFL-1.1, neo-grotesque/geometric + mono, no serifs/
  scripts/decorative; rationale per family in `fonts/META-FONTS.md`):
  UI Inter, document Source Sans 3, mono JetBrains Mono, display Space
  Grotesk, label Archivo, spare IBM Plex Sans.
- Vendoring: NOT done — lane rules forbid network fetches and this host
  is offline for font fetching. `fonts/MANIFEST.txt` lists exact files +
  upstream URLs + UNPINNED-offline-2026-11-04 honest marker; `LICENSES/`
  holds a per-family README with the OFL source URL. Drop-in: add the six
  `.woff2`s beside `install.sh`, re-run `--check`.
- `install.sh` copies to `/usr/share/fonts/truetype/meta/` + conf to
  `/etc/fonts/conf.d/69-meta.conf`, runs `fc-cache -f`; second run:
  `install: 0 copied, 7 up-to-date` (idempotent, cmp-gated). `--check`
  FAILs naming each missing/zero-length declared file (proven on staged
  root). `sh -n` clean.
- `69-meta.conf` aliases sans-serif→Inter, serif→Source Sans 3,
  monospace→JetBrains Mono (XML parsed in fallback proof).
- `fc-match` is impossible here: `command -v fc-match fc-list fc-cache` →
  all missing (macOS). Fallback proof (parsed conf + staged files):
  `sans-serif -> prefer 'Inter' ... PRESENT non-zero`,
  `serif -> prefer 'Source Sans 3' ... PRESENT non-zero`,
  `monospace -> prefer 'JetBrains Mono' ... PRESENT non-zero`,
  `RESOLUTION-MAP: PASS`. Real `fc-match` must run on the Linux target
  post-vendoring — not faked.
- Remote URLs: `grep -rn 'fonts.googleapis\|fonts.gstatic\|fonts.google.com\|@font-face' site/ os-build/iso/payload-apps/ os-build/iso/payload-theme/ js/` → exit 1, zero hits. (Upstream source URLs live in MANIFEST/LICENSES docs only, by design.)
- `test-no-ubuntu.sh`: Meta staged root → `no-ubuntu: PASS` exit 0;
  Ubuntu-named-font fixture → `FAIL ... Ubuntu-named font files` exit 1.
- `provision-all.sh` step `4b` runs `fonts/install.sh "$ROOT"`.
  `build_iso.sh --tree-only` does NOT invoke it and its file list has no
  font dir (verified: no `truetype/meta` in `/tmp/t1-tree`) — REQUEST to
  the tree owner (file:line below).
- Terminal mono (`FontName=Monospace 11`), greeter/panel Inter — read,
  already Meta; only change requested is
  `terminal/metaos-terminal-profile.txt:20` → `JetBrains Mono 11`.
- Total added: 17480 bytes (`wc -c` sum; `du -sk` = 36K). Six woff2
  Regulars project to 0.6–1.2 MB — still under the 3 MB budget.

## Section B. Identity (19-38)

- Writers, in execution order: `dexubuntu/apply-in-chroot.sh:33` (chroot
  phase) → `payload-theme/apply.sh:222` (manual/lane-C) → `debrand.sh:107`
  via `provision.sh:231` + new `provision-all.sh` step 4c (LAST, wins on
  live media) → on install media, in-target `meta-branding.sh:51` (LAST,
  wins on installed system — now stamps the contract, see below).
- `debrand.sh` is the single writer. `apply.sh` gated behind
  `METAOS_SKIP_IDENTITY=1` (default unchanged for stale callers;
  `provision-all.sh` step 4 passes the flag). `test_single_writer.sh`:
  `single-writer: PASS (debrand.sh primary, rest gated)` exit 0
  (KNOWN-EXTERNAL: `crates/.../build-image.sh:56`,
  `os/build-image.sh:56` print as requests, do not fail).
- Contract values stamped everywhere: `NAME="Meta OS"`,
  `PRETTY_NAME="Meta OS 1.0 (Ribbon)"`, `VERSION="1.0 (Ribbon)"`,
  `VERSION_ID="1.0"`, `VERSION_CODENAME=ribbon` (product name; nothing
  reads Ubuntu's codename — `UBUNTU_CODENAME` dropped, nothing consumed
  it), `ID=metaos`, `ID_LIKE=debian` (dependent readers: only
  `debrand --check`, `verify-rootfs.sh`, the new tests — apt reads
  `sources.list.d`, not this field), `HOME/DOCUMENTATION/SUPPORT/BUG`
  URLs. Byte-identity proven:
  `debrand output == dexubuntu/identity/os-release` → True;
  `debrand output == meta-branding.sh block` → True.
- Symlink write-through proven: staged root with
  `etc/os-release -> ../usr/lib/os-release`, Ubuntu content in target →
  apply writes through the link (`wrote .../etc/os-release`, target
  updated), `ls -l` identical before/after, second apply no-ops by cmp.
- Second `--apply`: `debrand: done, 0 change(s)` + md5 diff empty →
  `ZERO-BYTE second apply`.
- `--check` on a full staged root: 30 PASS + 1 expected SKIP (backdrops,
  user not seeded), `debrand --check: PASS`, exit 0. Ubuntu-valued
  copy: FAIL rows naming each file, exit 1.
- `rename_user`: staged fixture → `meta:x:1000:1000:Meta:/home/meta:/bin/bash`,
  0 `^ubuntu:` lines, `--check: PASS` (getent-equivalent pasted).
- `check_strings.sh`: exit 1, `58 unsuppressed hit(s)`. Zero are mine
  (my checkers/docs are allowlisted with per-row reasons). All 60 are
  cross-lane: real leaks (`face/meta-desktop.sh:41` /home/ubuntu fallback,
  desktop `Comment=` Xubuntu — both deliberately unallowlisted) plus
  probes/comments/docs owned elsewhere, each listed in the report table.
  Task 31's exit-0 is therefore NOT met: reaching it would require
  allowlisting other lanes' leaks or editing their files, both forbidden.
  The honest verdict (a sweep that fails loudly) beats a quiet lie.
- `meta-branding.sh` re-stamped to the contract (was `ID_LIKE=ubuntu` +
  overwrite; now contract values, gate comment). It still runs last on
  install media — harmless now that it stamps the contract.

## Section C. Boot surface (39-56)

- Rendered-by-inspection (no boot): `background.png` 1920x1080 RGB both
  themes; `meta-m 512x512 RGBA`, `progress 560x28 RGBA`; `scaled 1366x768`
  via in-script `Scale()` (no extra asset needed). Darkest pixel sampled
  with PIL from `meta-rays.png`: `(7, 11, 22)` = `#070B16`, matching
  `SetBackgroundTopColor/BottomColor (0.027, 0.043, 0.086)`.
- `grep -rni ubuntu-logo|ubuntu_logo|ubuntu-text` over both theme dirs +
  provision-all → empty, exit 1. Splash text:
  `caption.text = Image.Text ("Loading into MetaOS", ...)` (both
  variants; splash copy added this lane).
- 240 frames on disk, 242 `Image()` refs; `ribbon.n = 240`. Task 43's
  ≤40 conflicts with the pre-existing `apply.sh` ≥120 floor and
  `theme_proof` ≥120 gate — trimming unilaterally would break the build,
  so frames are unchanged and `check-plymouth.sh` reports (not gates) the
  count. Open decision recorded below.
- Greeter password colours: read-only — `gtk.css:78-85`
  `entry:focus { border-color: @meta_accent }` with
  `@define-color meta_accent #4f7ec2`; token drift noted (GTK ink/paper
  `#000000/#ffffff` vs splash `#070B16/#EDF5FF`) — request, not edited.
- No text-plugin theme exists anywhere in the tree
  (`find os-build -iname '*text.plymouth'` → empty) — requested, not done.
- Initramfs survival: static trace only (`provision.sh:55` copies theme,
  `:191-192` `plymouth-set-default-theme -R metaos`,
  `build_iso.sh:330` tree copy, `merge-layers:161/164` copy + `update-
  initramfs`). Boot-time proof impossible without QEMU — stated.
- Shutdown double-show: one `on_quit` per shipped script; the quit
  ordering lives outside my paths — requested, not changed.
- GRUB: no `grub.cfg` template in repo (honest: entries dumped from a
  built tree are unavailable; fixture-based proofs instead).
  `grub-fix.sh` converges live titles + recovery + `set timeout=10` +
  `set default="Try or Install Meta OS 1.0"` + strips recovery
  `quiet splash`: first run `grub fixed: 1 layerfs, 1 console, 2 titles,
  1 recovery-quiet-removed, ...`, second run identical except
  `0 recovery-quiet-removed`, byte-identical diff → IDEMPOTENT.
  `check-grub.sh` on fixed file: `PASS grub-brand ...`, `PASS ... Meta OS
  title ...`, exit 0; `xubuntu.seed` path carved out (renaming it would
  break boot).
- Greeter/session (read-only + my conf edits): session `user-session=
  metaos`, `allow-guest=false`, clock `%a, %b %e %H:%M` (= panel),
  `font-name=Inter 11`, cursor pinned, `show-hostname=true` both confs;
  `metaos.desktop` (`Name=Meta OS`, `Exec/TryExec=/opt/face/session.sh`)
  fails loudly if the session is missing. `check-greeter.sh`: 18 PASS,
  exit 0; Ubuntu-injected copy → `FAIL brand`, exit 1.
- Lightdm log (69): unreadable — no debugfs, no python ext4 module,
  `hdiutil` rejects the image; no sudo/mount/QEMU per constraints.

## Section D. Desktop theme (57-76, my paths only)

- Panel height 30/font 13 vs face reference (30px/13px) — already match,
  no edit. xfwm4 `button_layout=|HMC`, 15 svg + 15 png per button,
  not stock order — no edit. Icon `Icon=` all 12 resolve to shipped
  PNGs, empty missing list.
- New: `wallpapers/xfce4-desktop.xml` (`last-image=.../meta-rays.png`,
  style 5, both workspaces); `apply.sh` + `provision.sh` 2-line installs
  each (preflight-gated).
- Cursor, notifications, scaling, power, lock screen, welcome dialog,
  PS1, About panel: nothing in my paths — verified absent, requested
  (file:line list below). Greeter background already
  `meta-ascii.png` (exists in payload) — left alone.
- Theme tokens: `gen_theme.py --check` exit 0; single source
  `tokens/meta.tokens.json` feeds gtk/xfwm4/dock/panel (read-only proof).
- Stock Xubuntu wallpapers in my payload dirs: none (only
  `meta-{ascii,rays,dusk,dawn}.png`) — nothing to remove.

## Section E. Build and image (77-89)

- `build_iso.sh --tree-only /tmp/t1-tree`: exit 0, `done` line pasted,
  820 files, 75M. 6 broken symlinks, all pre-existing `oc2-*`
  agent-layer links (not mine; reported). No `grub.cfg` in tree (comes
  from base ISO at full build). Font dir, grub defaults, xsessions
  desktop are NOT in the tree output — wiring requests filed (tree owner
  must add the copy lines; my files exist in-repo).
- `/Users/` grep over install/provision scripts: exit 1, zero hits.
- `provision-all.sh` order verified: 1 packages → 2 installer lane →
  3 dexubuntu SKIP (chroot-only) → 4 branding (skip-identity) → 4c
  debrand re-stamp+check → 4b fonts → 5 face → 6 agent relay → 7 metaosd
  → 8 ownership. Fail-loud gates present (`fail ... missing`, `apply-
  GATE-FAIL`). Fresh-root manifest diff: 21/21 theme destinations land
  (run stopped at the fonts gate: expected — fonts not vendored yet).
- `curl|wget`: single hit is the apt package name `curl` in the install
  list — zero fetch usages in scripts.
- `sh -n`: clean on all 12 edited/new shell files (list pasted in
  transcript). `py_compile`: clean on `check_installer.py`,
  `gen_theme.py`, `check_buttons.py`, `meta-live.py`, `app-icons.py`.
- `verify_tree.sh`: ran; table pasted with other lanes' FAIL rows
  (identity-strings needs executable `check_strings.sh`; launcher-allowlist
  absent/OS-3; no-ubuntu lists shipped files incl. other lanes' probes).
- Cross-lane requests: full table below.

## F. Proof and handoff (91-100 mapping)

91: staged full-root `--check` → PASS exit 0 (above). 92: `check_strings`
exit 1 with 58 cross-lane hits (task as written unmeetable — see §B;
zero hits are mine). 93: font `--check` → FAIL naming the 6 missing
binaries (correct: nothing vendored yet). 94: splash 9 PASS + INFO frame
count + GRUB PASS/FAIL pair, pasted above. 95: `fc-match` impossible on macOS
(pasted `command -v` empties); fallback resolution-map PASS pasted
instead — Linux target run still owed. 96: unbootable-by-rule items:
splash render, initramfs content, GRUB menu, greeter pixels, session
behavior, install end-state, boot/shutdown timing. 97: remaining Ubuntu
strings — the 58-hit list (real leaks: face fallback, desktop Comments,
meta-branding now fixed; rest are probes/comments/docs owned elsewhere).
98: no file touched outside my owned paths (diff audit: zero hits for
forbidden prefixes; `greeter/` + `iso/calamares/` path notes below).
99: `pgrep -f qemu-system` → exit 1; `mount | grep metaos` → empty.
100: this report.

## Owned-path notes (auditor-flagged, addressed)

- Brief says `os-build/calamares/`; the tree has only
  `os-build/iso/calamares/`. All my installer work is in the real tree.
- Brief lists `payload-theme/lightdm/`; live drop-ins live in
  `payload-theme/greeter/`. I edited the greeter confs (the files the
  installer actually copies) and put the session desktop + checks in the
  new `lightdm/` dir. If greeter/ belongs to another lane, this doubles
  as a request for the path amendment.
- `metaos.desktop` `Exec=/opt/face/session.sh` necessarily references the
  session binary outside my paths — that is the point of a session file.

## Cross-lane requests (file:line + ask)

- Boot/ISO lane: `build_iso.sh` tree-only file list — add font dir
  (`fonts/*.woff2 → usr/share/fonts/truetype/meta/`, `69-meta.conf`),
  grub defaults (`metaos-grub-defaults → etc/default/grub.d/99-metaos.cfg`),
  xsessions desktop; add `-volid "MetaOS_1_0"` (precedent
  `repack-iso.sh:61`); set `GRUB_DISTRIBUTOR="MetaOS"`
  (`iso/boot/grub/metaos-theme.cfg` currently only sets THEME, TIMEOUT=5
  vs theme `timeout=10`); confirm `update-initramfs` content post-build;
  confirm single `plymouth-quit` ordering (shutdown double-show).
- Greeter/theme owner: greeter password-entry palette + GTK token drift
  (`gtk.css:78-85` accent `#4f7ec2` vs splash `#1877F2`); text-plugin
  fallback theme (none exists); `theme_proof.sh:184-191` Ubuntu Mono
  assertions vs vendored Meta fonts; `payload-theme/identity/os-release`
  missing `DOCUMENTATION_URL`; `identity/motd` base-name line;
  `00-header` dual-write; 240-vs-≤40 frame decision.
- Face/Buffy: `face/meta-desktop.sh:41` `/home/ubuntu` fallback → meta;
  terminal `FontName` mono (profile + provision rc block);
  cursor/notification/scaling/power/lock/PS1/About/first-run items
  (no my-path config exists — full list in §D).
- OS-3/agent-layer: desktop-entry `Comment=` Xubuntu lines;
  `stage.sh` 6 dangling `oc2-*` symlinks in tree output.
- Image owner: package removals R-101 (Pro/ESM), R-102 (xubuntu branding
  payloads), R-103 (ubuntu-release-upgrader*), R-106 (plymouth ubuntu
  themes if present); per-package `Installed-Size` at removal time.

## Next three steps

1. Vendor the six woff2 + LICENSES texts, re-run font `--check` green,
   then `fc-match` on the Linux target for all three generics.
2. Gate `meta-branding.sh` hostname/issue/motd writes like os-release
   (currently ungated but contract-valued), and get the tree owner to
   install the font dir, grub defaults, and xsessions desktop.
3. Decide the 240-frame question with the boot lane, then do the one
   booted pass this lane could never do: splash→greeter→session
   screenshots with the new type live.
