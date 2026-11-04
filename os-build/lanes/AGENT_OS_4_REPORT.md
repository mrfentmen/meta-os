# AGENT OS-4 REPORT — build, proof tooling, dead code, repo hygiene

Branch: `agent-os-4` (worktree `/tmp/agent-os-4`). No merge, no rebase, no
push. QEMU run zero times (only refusal paths executed); nothing mounted,
installed, or mastered; no temp files under the repo tree; no key, token, or
secret in any file.

## A. The no-boot guard (tasks 1–10)

VM-launching tools found by grep (name:line:command):

- `os-build/tools/show_os.sh:130` — `"$QEMU" \ … &` (plus a QEMU execution
  at line 103, the `-audiodev help` probe)
- `os-build/tools/proof_boot.sh:117` — `"$QEMU" \ … &` (detached)
- `os-build/tools/proof_iso.sh:102` — `"$QEMU" \ … &` (detached)
- `os-build/tools/frames_boot.sh:16` — `qemu-system-aarch64 \ … &`
- `os-build/tools/drive.py:84` — `Popen(["qemu-system-x86_64", …])`,
  standalone mode only (`--monitor` attach mode never boots)
- `os-build/iso/tools/vm_install_proof.sh:128` — `qemu-system-x86_64
  "${args[@]}"` inside `start_vm()` (dry, iso and reboot paths all enter
  there; even `--dry` boots firmware)

`pgrep`-only helpers (`install_agent_runtime.sh`, `set_spark_key.sh`) do not
launch and are unguarded. `sync_image.sh` only echoes a proof command.

One shared guard, `os-build/tools/qemu_guard.sh`: `qemu_guard "<tool>"`
reads the flag from the exported environment only (`printenv`, never a shell
variable, flag, or file), refuses with
`refused: <tool> boots QEMU. set METAOS_ALLOW_QEMU=1 to allow it.` and exits
2; anything but exactly `1` (including a missing printenv) refuses.
Fail-closed, POSIX sh, `sh -n` clean. Wired before the first QEMU execution
in each tool (before/after line numbers are the `qemu_guard` call lines in
the `sh -n` check below). `drive.py` checks `os.environ` before `Popen`
(also fixed a missing `import os` it tripped over). `vm_install_proof.sh`
sources the same file and guards at the top of `start_vm()` — note: that
file is outside the index's OS-4 path list, edited because task 8 orders it;
Buffy, keep it on this lane or move it explicitly.

Refusal transcript (the only runs of these tools; no VM started):

```
$ sh os-build/tools/frames_boot.sh
refused: frames_boot.sh boots QEMU. set METAOS_ALLOW_QEMU=1 to allow it.
exit=2
$ python3 os-build/tools/drive.py help
refused: drive.py boots QEMU. set METAOS_ALLOW_QEMU=1 to allow it.
exit=2
```

`pgrep -f qemu-system` afterwards: nothing. The allowed path
(`METAOS_ALLOW_QEMU=1 …`) was deliberately not exercised — running it would
be the boot this lane exists to prevent, and its correctness is a one-line
string comparison read plainly in the guard file. A wrapper cannot bypass
the guard with a shell-local variable: only the exported environment counts,
documented in the guard header and the tools README (which now lists every
tool with boots yes/no).

## B. Verification entry point (tasks 11–22)

Checker inventory (offline unless noted): `os-build/tools/*.mjs|*.py`
(claims, gates, manifests — repo-lore checkers, no boot, no network);
`os-build/iso/test/run_checks.sh` (skips QEMU stages without the binary);
OS-1's `check_strings.sh` + `ALLOWLIST.tsv` and OS-3's launcher/desktop
selftests do not exist yet — rows below prove it.

`os-build/tools/verify_tree.sh`: no args (or `--json`), works from any cwd,
uses `find` (no git), exits 1 with `DEAD: <names>` on stderr on any FAIL.
Full table, measured on this tree (`6 rows in 2s`, run in 2.3 s wall):

```
check | result | detail
allowlist | absent (owned by OS-1) | os-build/identity/ALLOWLIST.tsv not present yet
identity-strings | absent (owned by OS-1) | os-build/identity/check_strings.sh not present yet
launcher-allowlist | absent (owned by OS-3) | agent-layer/desktop-entries/selftest.sh not present yet
desktop-entries | absent (owned by OS-3) | agent-layer/desktop-entries/check_desktop.sh not present yet
tree-refs | PASS | 21 .desktop files: Name+Exec present, absolute icons resolve
no-ubuntu | FAIL | 28 files mention ubuntu (e.g. os-build/iso/payload-theme/panel/xfce4-panel.xml;os-build/iso/payload-theme/greeter/10-metaos-live.conf;os-build/iso/payload-theme/greeter/K)
DEAD: no-ubuntu
```

That failure is the honest baseline: without OS-1's allowlist every hit
counts, and 28 shipped files mention ubuntu (theme configs, greeter conf,
debrand scripts that must name what they remove). `--json` verified:
`verify_tree.sh --json | python3 -m json.tool` parses (exit 0), six objects,
same rows. Expected checker paths are constants at the top of the script so
Buffy can repoint them when the lanes land.

## C. The build (tasks 23–32)

`build_iso.sh` pipeline: `--check` (configs + tool readiness, runs on the
Mac) → `--root` (provision a Cubic chroot, needs root) → `--iso` (Linux +
root + xorriso: verify base hash, extract ISO, unsquash, provision.sh into
the rootfs, re-squash, xorriso replay, sha256) → `--inspect` (payload
presence inside the squashfs). Root/network points: everything from
`--root`/`--iso` on needs root; `apt-get` inside the chroot needs network;
`--verify-base/--base-info` run on the Mac via bsdtar. One line (task 24):
it currently produces nothing on this machine — `--check` is local, every
producing mode needs Linux root (and today, missing files, see below).

Note: the index lists `build-arm64-inner.sh` and `metaos-install.sh` as
OS-4 paths, but neither file exists in this tree. Nothing was edited there
because there is nothing there; if they are supposed to exist, that is a
request for whoever owns their creation.

`--tree-only [DIR]` is new in `build_iso.sh`: it assembles the repo payload
into a temp dir with no root, no loop mount, no chroot, no network, by
mirroring provision.sh's COPY sections (cited `PROV:<line>` per step) plus
the root-tolerant `agent-layer/stage.sh`, and stops where provision.sh
starts needing a base rootfs. Deliberately not run: packages + initramfs
(chroot/apt) and the identity scripts (OS-1's; they expect a full base
tree). Proven run: `bash os-build/iso/build_iso.sh --tree-only
/tmp/agent4-treeonly` → **350 files, 21M**, full listing printed, ending
`tree-only: done. No ISO mastered`. Temp tree removed afterwards.

Tree verification on that 350-file tree (task 27 — theme, agent payload,
splash PASS in-tree; face site source present in repo root but installed by
`face/provision.sh` (Buffy), outside this path; boot menu ships in the base
ISO and is patched by `finalize-iso-tree.sh`, outside this path):

- theme: PASS (`usr/share/themes/MetaOS`, panel, dock, greeter conf present)
- agent payload: PASS (`usr/share/metaos/agent`, incl. `aegis/opsec.mjs`)
- splash: PASS (`usr/share/plymouth/themes/metaos/metaos.plymouth`)
- face site: source present (`index.html`, `bus.html`, `surfaces.html`,
  `logo-studio.html` at repo root); installed by Buffy's provisioner
- boot menu: base-ISO file; `finalize-iso-tree.sh` + `merge-layers.sh`
  syntax-checked (`sh -n` clean)

Symlinks (task 28): 6 total, 0 broken when absolute targets are resolved
against the tree (naive `test -e` fails them because they point at
`/usr/lib/systemd/...` — correct inside the image, absent on the Mac; the
report records the method). `/Users/` in tree text files (task 29): exactly
one file, `aegis/opsec.mjs`, and both hits are placeholder patterns in
comments (`/Users/<name>/`, `/Users/you/` in an allow-list) — no baked host
path. Ten largest (task 30): `maplibre-gl.js` 803K, then nine
`studio-loop/loop-*.jpg` ~412–424K each — the wallpaper loop frames are
where the megabytes live. No ISO was mastered, and none will be on this
lane (task 31).

## D. Dead code and duplicate trees (tasks 33–42)

Theme trees: `metaos-theme/` = 51 files, `os-build/iso/payload-theme/` =
228 files. **22 identical, 29 drifted, 177 only-in-payload (76 jpg, 62
png, 14 desktop, …), 0 only-in-metaos-theme.** The shipped tree is
`os-build/iso/payload-theme` — cited: `provision.sh:104
PAYLOAD="$HERE/payload-theme"` and `face/provision.sh:70
THEME_SRC="$HERE/../iso/payload-theme"`; no build script sources
`metaos-theme/`. Drifted text files include `gtk/gtk.css`,
`panel/xfce4-panel.xml`, `splash/metaos.script`, `wallpapers/live/meta-live.py`
— the judge always sees the payload side. Drifts are handed to Buffy (all
in Buffy's theme paths) as a request with this table; nothing fixed,
nothing deleted there.

Orphan scan (task 37): every basename under `os-build/**/*.sh` grepped
across the repo (script-generated, `/tmp/agent4-orphans.py` method: full-text
scan, self-hits excluded). Exactly two files nothing references:

- `os-build/face/spike-a-session.sh`, `spike-b-session.sh` — Buffy's paths:
  NOT deleted, handed over as a request.
- `os-build/tools/install_imperium_app.sh` — mine, superseded by
  provision.sh's imperium section (same sources, same destinations, plus
  receipt checks): **deleted**, `git rm`, zero-hit grep pasted in the commit
  trail (`grep -rn install_imperium` → only itself).

`os-build/logs/`: 674 files, ~15 MB, all Nov 2026 — generated evidence, not
source (no build reads it). Not deleted; indexed per directory in
`os-build/tools/logs_index.md` (task 40).

Untrue headers (task 41): `os-build/tools/README.md` claimed drive.py "lives
on main, not on this branch" while it sits in the same directory — fixed
(mine). `build_iso.sh`'s claim label said `--check` is the only locally
proven mode — stale the moment `--tree-only` passed; fixed to name both
(mine). No other false header found in my files; `drive.py`'s `gate.sh`
reference and `vm_install_proof.sh`'s `--dry` claim both check out
(`os-build/gate.sh` exists, `qemu-system-x86_64` is on this Mac).

## E. Proof and handoff (tasks 43–50)

Can a judge verify this tree without booting anything, and what exactly do
they type? Yes — two commands, both run above on this Mac:

```
sh os-build/tools/verify_tree.sh          # table + DEAD: on failure, exit 1
bash os-build/iso/build_iso.sh --tree-only /tmp/t   # 350 files, 21M, listing
```

The demo-screen command is `verify_tree.sh`; its real output is the table
in section B (current verdict: 4 absent rows owned by OS-1/OS-3, 1 PASS, 1
FAIL on 28 unexcused ubuntu mentions — the merge order 4 → 1 → 2 → 3 exists
so this baseline can only improve).

Absent-check dependency map (task 46): `allowlist`, `identity-strings`
wait on OS-1 (`os-build/identity/ALLOWLIST.tsv`, `check_strings.sh`);
`launcher-allowlist`, `desktop-entries` wait on OS-3
(`agent-layer/desktop-entries/selftest.sh`, `check_desktop.sh`). Exact
filenames are constants at the top of `verify_tree.sh`.

`sh -n` passes on every shell file touched (guard, verify_tree, show_os,
proof_boot, proof_iso, frames_boot, vm_install_proof, build_iso,
finalize-iso-tree, merge-layers) and every edited launcher carries the
guard (task 47). No absolute `/Users/` path, secret, or real hostname in
any of my files (task 48; the one `/Users/you/` in the tree is OS-1's
allowlist fodder, requested above).

Commits on `agent-os-4` (task 49), nothing on `main`:

- guard commit: every QEMU-launching tool refuses without the flag
- verify_tree commit: offline table with absent-tolerant lane rows and --json
- tree-only commit: rootless payload assembly in build_iso.sh
- dead-code commit: drop superseded installer, index evidence, fix headers
- this report

QEMU run zero times (task 50): the only executions were the two refusal
transcripts, both exited before any QEMU process existed (`pgrep` clean
after). Nothing mounted, nothing installed, no ISO mastered, temp trees
under `/tmp` removed; `git status` in the worktree shows only this report
untracked-then-added.
