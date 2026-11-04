# AGENT_OS_1 REPORT — identity, naming, Ubuntu-to-Meta sweep

Lane branch `agent-os-1`, worktree `/tmp/agent-os-1`. No QEMU, no mounts, no
sudo, no docker, no apt at any point. Every proof below ran as a shell
command whose output is pasted in full or in faithful excerpt.

## Commits (mine only, all on `agent-os-1`, no merge/rebase/push)

- `aa4c95d2` os-1: portable rename_user (no sed -i), identity matrix,
  checker README, string tests
- (report) os-1: AGENT_OS_1 report — this file, committed last.

The branch also carries a parallel session's commits (`47b15f7c`
STRINGS_INVENTORY, `7b2fd4c4` debrand survivor, `4400423a` allowlist+checker,
`dd2d987e` payload/debrand fixes incl. two of my fixes the session committed
while I was proving them). I verified their content by running it rather than
rewriting it; where I changed their files the change is mine and proven
below. Shared-worktree collisions encountered: my `STRINGS_INVENTORY.md`
overwrite was reverted (kept the committed version), my `rename_user.sh`
portability fix was reverted once by the other session and re-applied,
`ALLOWLIST.tsv`/`check_strings.sh` are still being edited by the other
session as I write this — I did not commit those two files.

## What I changed

- `os-build/iso/payload-theme/identity/os-release`: `ID_LIKE="ubuntu debian"`
  → `ID_LIKE=debian`, dropped `UBUNTU_CODENAME`, `VERSION_CODENAME=noble` →
  `ribbon`, `VERSION="1.0"` → `"1.0 (Ribbon)"` (contract table + About-page
  `VERSION_CODENAME` consumer in `os-build/face/session.sh` both demand it).
- `os-build/iso/payload-theme/identity/lsb-release`: `DISTRIB_ID=Meta OS` →
  `MetaOS`, `DISTRIB_CODENAME=meta` → `ribbon` (matches `debrand.sh`'s writer
  and checker, plus MILO QA + UBUNTU_INVENTORY which already say MetaOS).
- `os-build/iso/payload-theme/identity/motd`: honest 3-line banner
  (product / base not rewritten / read os-release). `00-header`'s 3-line
  version is the parallel session's edit, kept as-is; the duplication is
  noted as a merge note for Buffy (keep one).
- `os-build/identity/debrand.sh`: fixed the desktop-dir sweep to match
  `buntu` (the old `grep Ubuntu` never matched Xubuntu-only files — proven:
  `xb.desktop` kept saying Xubuntu while `--check` passed), and added
  `--check` coverage for those dirs (`desktop names clean` FAILs naming the
  file). Survivor decision: `debrand.sh` survives (has the check contract +
  modes); `debrand2.sh` stays, now redundant but still called by
  `os-build/iso/provision.sh:202` — deletion request filed below.
- `os-build/identity/rename_user.sh`: replaced all 9 `sed -i` sites (plus
  GNU-only `\(...\|...\)` and `\?`) with a portable `resed()` helper
  (tmpfile + `cat`, ERE via `sed -E`). Rationale: BSD sed needs `-i ''`,
  and `\?`/`\|` silently do the wrong thing there. Task 3 answer: the script
  is pure file surgery under `$ROOT` (no daemons, no id/usermod calls), so it
  is safe on a never-booted root. GECOS: fixed in-script (`[Uu]buntu` →
  `Meta`) and asserted in `--check`; the live-system equivalent is
  `usermod -c Meta meta`.
- New: `IDENTITY_MATRIX.md` (23 surfaces, file + lane + PASS/FAIL/not-mine),
  `README.md` (judge doc with the real checker output + ~35 s timing),
  `test_check_strings.sh` (4/4 green, fixtures in `mktemp -d`, cleaned up).

## What I proved by running it

- `debrand.sh` on staged root `/tmp/fakeroot-1` (Ubuntu values, `/etc/os-release`
  → `../usr/lib/os-release` symlink): apply → 13 changes; `ls -l` shows the
  symlink survived (written through, never replaced); second apply → `0
  change(s)` + byte-identical tree (`md5` before/after equal); `--check`
  → PASS exit 0; `--json` → per-file objects exit 0; old positional form
  (`debrand.sh ROOT --check`) → PASS; Ubuntu-valued copy → FAIL naming
  `lsb-release` + desktop file, exit 1. `xb.desktop` rewritten to
  `Name=Meta OS Browser` (exactly 1 change on re-apply).
- `rename_user.sh` on staged fixture (ubuntu account, `Ubuntu` GECOS,
  lightdm autologin): `--check` → FAIL exit 1 naming all five problems;
  apply → all PASS exit 0; second apply byte-identical; zero `ubuntu`
  strings left in passwd/group/shadow.
- `check_strings.sh`: real tree → exit 1 with exactly the 5 cross-lane hits
  (below); `--explain` names suppressing rows; clean fixture → exit 0;
  one-banned-word fixture → exit 1 naming the file; allowlisted-only
  fixture → exit 0; temp file `OS1-TMP-PROBE.txt` with `Ubuntu` on the real
  tree → exit 1 naming it, file deleted after; `cd /tmp && sh
  /path/to/check_strings.sh` → identical verdict (cwd-independent);
  `sh -n` passes on all five shell files.
- `sh os-build/identity/test_check_strings.sh` → `4 passed, 0 failed`.
- Timing for the README: `check_strings.sh` ≈ 35 s wall on this machine.

## What I skipped and why (10 items)

- Task 2's "is debrand2.sh still needed": answered (no, redundant — but NOT
  deleted: `os-build/iso/provision.sh:202` still calls it; deletion + caller
  update requested below).
- Task 24's vacuity row: the parallel session added the bogus
  `no/such/file.txt` row and has not removed it yet; I proved non-vacuity
  instead via the one-banned-word fixture (exit 1) and the temp-file probe.
  I did not touch their row.
- Whole-word `-w` matching means all-caps `UBUNTU_*` (e.g. dexubuntu's
  `UBUNTU_CODENAME`) is invisible to the checker — outside the six briefed
  words; noted, not widened unilaterally (would need OS-4 agreement).
- No boot/QEMU/mount per hard rules: image-level proof (lspci-free `lsb_release
  -a` on hardware, greeter pixels) is replaced by staged-root runs + static
  parse; the report says so everywhere instead of claiming it.
- `site`/`00-header` duplication, `table-layout`-style cosmetics: not mine,
  not touched.
- `ALLOWLIST.tsv` + `check_strings.sh` final commit: left to the session
  actively editing them (my anchoring fix for `allow()` is already in the
  tree; verified by the 5-hit run).

## Every cross-lane request (task 47 — files I did not touch that still print Ubuntu)

1. `os-build/iso/calamares/meta-branding.sh:33` (OS-2): `ID_LIKE=ubuntu`
   written into `/etc/metaos-release` and copied over `/etc/os-release` on
   the INSTALLED system; also `NAME/PRETTY` lack Ribbon and there is no
   `VERSION_CODENAME`. Request: `ID_LIKE=debian`, `PRETTY_NAME="Meta OS 1.0
   (Ribbon)"`, `NAME="Meta OS"`, `VERSION="1.0 (Ribbon)"`,
   `VERSION_CODENAME=ribbon` (keep `ID=metaos`, `VERSION_ID=1.0`). This is
   the last writer and defeats every earlier fix on install media.
2. `os-build/metaos1-base/dexubuntu/identity/os-release:7,12` (Pax /
   metaos1-base owner): same `ID_LIKE=ubuntu` + `UBUNTU_CODENAME` + `MetaOS
   1.0` without Ribbon. Request: mirror the payload file (debian / ribbon /
   no UBUNTU_CODENAME), or delete the file and stop installing it — two
   competing os-release writers is the bug beneath the bug. (Competing
   writers, last-wins order: dexubuntu → payload apply.sh → debrand.sh →
   meta-branding.sh.)
3. `os-build/iso/provision.sh:202` (whoever owns it — not in the index
   table): after the survivor decision the loop should read `for script in
   debrand.sh rename_user.sh; do` (drop `debrand2.sh`, now redundant).
4. `agent-layer/desktop-entries/atril.desktop:6`,
   `evince.desktop:6` (OS-3): `Comment=` shown in menus names Xubuntu.
   Request: reword without the base name (keep the KEEP/ack state in README,
   not in the user-visible string).
5. `os-build/face/meta-desktop.sh:34` (Buffy): `HOME_DIR="${HOME:-/home/ubuntu}"`
   fallback points at a home that no longer exists after the rename.
   Request: default to `/home/meta`.
6. `os-build/iso/payload-theme/gtk/gtk.css:8` (Buffy): `font-family: ...
   'Ubuntu' ...` — font fallback, correctly NOT a leak; no change requested,
   recorded so nobody "fixes" it into a missing-font bug. Same for
   `terminal/metaos-terminal-profile.txt` `FontName=Ubuntu Mono` (OS-3):
   font name + `fonts-ubuntu` package ref, keep.

## Plain statements (tasks 48–50)

- The tree (and the image built from it) does NOT pass `check_strings.sh`
  as-is: 5 hits survive, all listed above, all in files I do not own. My
  files and every allowlisted honest hit pass; nothing I own leaks.
- Commits: `aa4c95d2` (mine, listed above) on `agent-os-1`; the branch also
  carries the parallel session's `47b15f7c`, `7b2fd4c4`, `4400423a`,
  `dd2d987e`. I did not merge, rebase, or push. `main` untouched by me
  (I never checked it out; all work happened in `/tmp/agent-os-1`).
- No QEMU ran (`qemu-system-*` never invoked — the binary was never even
  located), nothing mounted, no sudo/docker/apt. Temp dirs (`/tmp/fakeroot-1`,
  `/tmp/fakeroot-user*`, fixture `mktemp -d` dirs, `/tmp/os1-*` logs) all
  live outside the repo; the repo tree contains no temp file of mine
  (`git status` shows only the two lane files the other session is editing).

## Definition-of-done check

- `sh os-build/identity/check_strings.sh` gives a real verdict on the
  current tree and exits truthfully (1, naming 5 unowned leaks). ✓
- `--apply` then `--check` passes on a staged fake root, twice in a row,
  byte-identical. ✓ (`rename_user.sh` likewise.)
- `ALLOWLIST.tsv` exists, tab-separated, every row has a reason. ✓ (282
  data rows at report time; count moves as the lane's other editor works.)
- `IDENTITY_MATRIX.md` names an owner per surface. ✓
- Leftovers name their owners. ✓ (§47 above.)
