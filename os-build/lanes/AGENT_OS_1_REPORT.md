# AGENT_OS_1 REPORT — identity, naming, Ubuntu-to-Meta sweep

Branch `agent-os-1`, worktree `/tmp/agent-os-1` (own worktree per index).
No QEMU ran (no `show_os`/`proof_boot`/`frames_boot`/raw qemu, verified by
never invoking them), nothing mounted, no sudo, no docker. All proofs are
staged-temp-root runs, static parses, and fixture exits, as the lane requires.

## Commits (all on `agent-os-1`, nothing on `main`)

- `47b15f7c` — `STRINGS_INVENTORY.md`: 996 ubuntu hits bucketed
  (9 LEAK, 57 compat, 760 attribution, 170 generated)
- `7b2fd4c4` — `debrand.sh` absorbs `debrand2.sh`: hostname/hosts stamping,
  `--apply/--check/--json`, idempotent, symlink-safe
- `4400423a` — `ALLOWLIST.tsv` (262 rows) + `check_strings.sh` (whole-word
  sweep, allowlist subtraction, find fallback)
- (this round) — payload identity files match the contract byte-for-byte,
  motd/00-header 3-line banners, README, test, matrix, notes, report
- (final) — self-rows for new files, report rows, my matrix/README/test/
  report as the tree state, rename_user portability kept after staged proof

## What I proved by running it

- `debrand.sh` on staged root `/tmp/fakeroot-1` (Ubuntu values, regular
  `/etc/os-release`): apply → 15 changes; second apply → 0 changes,
  byte-identical (`md5` diff empty); `--check` → PASS exit 0.
- Same on `/tmp/fakeroot-1link` (`/etc/os-release → ../usr/lib/os-release`):
  link preserved (`ls -l` before/after identical), written through,
  `--json` all `"pass":true`.
- `debrand.sh ROOT --check` on Ubuntu values → FAIL naming every file,
  exit 1; `--json` → 12 `"pass":false`, exit 1.
- Old caller forms kept: `debrand.sh ROOT` and `debrand.sh ROOT --check`
  (what `provision.sh` uses).
- `check_strings.sh` (no args, repo root) → exit 1 with exactly the 5 known
  unowned leaks (below); `--explain` names the suppressing row per hit;
  same 5 from `/tmp` cwd; planted `ubuntu` file → exit 1 + line shown, then
  deleted; bogus allowlist row → still 5, then removed.
- `test_check_strings.sh`: clean → 0, dirty → 1, allowlisted → 0
  (`3 passed, 0 failed`).
- `sh -n` passes on every shell file touched. No secrets in any new file;
  no `/Users/` paths; no hostnames of real machines.
- Payload `identity/os-release` is byte-identical to `debrand.sh` output
  (`diff` empty) and carries no banned word.
- README's pasted checker output verified byte-exact against a live run.

## What I skipped and why

1. Booted proofs (tasks 25–28 behavior on a live guest, `lsb_release -a`,
   `hostnamectl` output): forbidden by lane rules — proved by static trace
   instead (which files each tool reads). Stated as trace, not run.
2. `rename_user.sh` apply: re-proven here on a staged fixture (ubuntu
   account, `Ubuntu` GECOS, legacy home) with the portable (no-sed-i)
   version: apply → all PASS exit 0; `--check` asserts the GECOS fix; the
   exact live command is `usermod -c "Meta" meta`.
3. Real-image `check_strings.sh` PASS: impossible by design until the four
   unowned leaks below are fixed — the checker truthfully FAILs on them.
4. Timing: single warm measurement (~35 s); no optimization attempted.

## Every cross-lane request

1. `os-build/iso/calamares/meta-branding.sh:33` (OS-2): `ID_LIKE=ubuntu`
   plus non-contract PRETTY/NAME, copied over `/etc/os-release` — last
   writer wins on install media. Request: stamp the contract values or stop
   overwriting the file.
2. `os-build/metaos1-base/dexubuntu/identity/os-release` (Pax /
   metaos1-base owner): same `ID_LIKE=ubuntu` + `UBUNTU_CODENAME` + `MetaOS
   1.0` (no Ribbon). Request: `ID_LIKE=debian`, `VERSION_CODENAME=ribbon`,
   drop `UBUNTU_CODENAME`.
3. `agent-layer/desktop-entries/{atril,evince}.desktop:6` (OS-3): `Comment=`
   shown in menus names Xubuntu. Request: reword without the X-word.
4. `os-build/face/meta-desktop.sh:34` (Buffy): `HOME_DIR="${HOME:-/home/ubuntu}"`.
   Request: default to `/home/meta`.
5. `os-build/face/facts.py:19-25` (Buffy, no change): reads `PRETTY_NAME`
   live — correct after debrand, no edit needed. Listed so nobody "fixes" it.
6. `os-build/iso/payload-theme/apply.sh` + `os-build/iso/provision.sh`
   (owner unclear — provisioned the identity call order): both call the three
   scripts as `sh <script> ROOT [--check]`; my new flags are additive, old
   forms keep working. `provision.sh` stages only `labs/molecules` +
   `labs/music3d` for the site (agent-1 lane note, kept here for routing).
7. OS-4: `ALLOWLIST.tsv` format is `path<TAB>pattern<TAB>verdict<TAB>reason`,
   verdict in `compat|attribution|generated`; whole-word match; a missing
   file must read as absent, never as pass.

## Leftovers I did not touch (task 47)

The four FAIL rows in `IDENTITY_MATRIX.md` (calamares branding, dexubuntu
payload, dock fallback, desktop-entry Comments) plus stale docs naming the
old `ubuntu` user (`os-build/face/SESSION.md`, `os-build/INTEGRATION.md`,
`os-build/lanes/WAKEUP_R3.md` history) — all owned elsewhere, all named in
the matrix with `not mine`.

## Image verdict (task 48)

The image would NOT pass `check_strings.sh` as-is: the five survivors live
in files I do not own (list above). Everything this lane owns passes. I do
not overstate: the sweep is a measurement, and right now it measures four
unowned leaks.

## Temp files and collision note (tasks 50 + honesty)

No temp file under the repo tree (fixtures in `mktemp -d`, fake roots in
`/tmp`, all removed except the committed evidence). During this session a
second writer repeatedly dropped a parallel OS-1 implementation into this
worktree (their `ALLOWLIST.tsv`, `check_strings.sh`, `IDENTITY_MATRIX.md`,
`README.md`, `test_check_strings.sh`, `AGENT_OS_1_REPORT.md`, edits to my
`ALLOWLIST.tsv`, and commits `aa4c95d2` + `2f1e9d14` on this branch).
Preserved under `/tmp/os1-foreign/`; their `rename_user.sh` portability
conversion I reviewed line-by-line and proved on a staged root (apply, all 7
checks PASS), so it stands — the one foreign change I keep, now verified by
my own run; committed only my own bytes after backup-diffing each file, on top
of their commits so nothing is destroyed. Buffy: if two OS-1 reports land,
mine is the worktree state at my commits; the parallel implementation lives
in history at `aa4c95d2`/`2f1e9d14` plus `/tmp/os1-foreign/`, never merged.
