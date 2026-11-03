# SHELL_REVIEW.md — manual quoting review checklist

shellcheck is NOT installed on this Mac, and per task instructions it was
deliberately NOT installed: **shellcheck = BLOCKED**. Substitute used here:
`sh`/`bash -n` on every script (the `run_checks.sh` "shell syntax" step)
plus the manual checklist below: quoting of expansions, POSIX-ness of the
`#!/bin/sh` files, and dangerous-operand scans.

Re-run everything on this page with (from the lane dir `os-build/iso`):

```sh
for f in merge-layers.sh finalize-iso-tree.sh grub-fix.sh provision.sh \
         calamares/meta-branding.sh; do sh -n "$f" && echo "OK $f"; done
for f in build_iso.sh tools/vm_install_proof.sh test/run_checks.sh \
         test/verify-base.test.sh test/base-layout.test.sh \
         test/test_stages.sh; do bash -n "$f" && echo "OK $f"; done
grep -nE '(rm +-rf? +|cd +|cp +-r? +|chroot +|mount +)[^"]*\$[A-Za-z_]' \
  merge-layers.sh provision.sh build_iso.sh finalize-iso-tree.sh \
  grub-fix.sh calamares/meta-branding.sh   # want: no output
grep -nE '\[\[|^[^#]*\blocal\b|^[^#]*\bsource\b|&\>|shopt|pipefail' \
  merge-layers.sh finalize-iso-tree.sh grub-fix.sh provision.sh \
  calamares/meta-branding.sh               # want: only ${..} expansions
```

## Per-file verdicts (reviewed 2026-11-03, branch opencode1/build-tests)

| file | shebang / flags | quoting | POSIX check | verdict |
|---|---|---|---|---|
| `merge-layers.sh` | `#!/bin/sh`, `set -e` | all `$WORK/$SRCDIR/$ISO/$OUTDIR` operands quoted; `while IFS= read -r` loop; `"$@"`-style globs quoted (`"$WORK/livefix/$moddir/"*/` keeps the `*` unquoted, correct) | no `[[`/`local`/`source`/`==`; only POSIX `${VAR:?...}` / `${VAR:-...}` | CLEAN, no fix |
| `finalize-iso-tree.sh` | `#!/bin/sh`, no `set` | `"$TREE/..."` quoted; heredoc `<<'PYEOF'` quoted so `$` never leaks into python | no bashisms | CLEAN, no fix. Known wart (NOT quoting): no `set -e`, so a missing tree exits 0 via the disk-info skip path — tolerated because `merge-layers.sh` asserts grub counts right after the call (pinned in `test_stages.sh`) |
| `grub-fix.sh` | `#!/bin/sh`, no `set` | `"$f"` quoted; `"$1"` read without `-u` so the no-arg default path works | no bashisms | CLEAN, no fix |
| `provision.sh` | `#!/bin/sh`, `set -eu` | `"$ROOT/..."` quoted throughout; `for arg in "$@"`; `cp -a "$HERE/..."`; heredocs quoted (`<<'PLYMOUTH'` etc.); `shift \|\| true` guards the flags-empty case under `-e` | no bashisms | CLEAN, no fix |
| `build_iso.sh` | `#!/bin/bash`, `set -euo pipefail` | `"$base"/"$sq"/"$work/..."` quoted; `local mksq_args` array + `"${mksq_args[@]}"`; `awk -v b="$base"` avoids injection | bash-only constructs legal under bash shebang | CLEAN, no fix |
| `calamares/meta-branding.sh` | `#!/bin/sh`, `set -eu` | absolute target paths (no variables to quote); heredocs quoted; `command -v` guard before `plymouth-set-default-theme -R` | no bashisms | CLEAN, no fix |
| `tools/vm_install_proof.sh` | `#!/bin/bash` | covered by `bash -n`; qemu/QMP args quoted at call sites | n/a (bash) | CLEAN, no fix |
| `test/*.sh` (5 files) | `#!/bin/bash`, `set -uo pipefail`, no `set -e` (assert-failures must not abort) | `"$tmp/..."` quoted; `grep -qF -- "$needle"` uses `--` so needles starting with `-` are safe; `env VAR=... cmd` form for shim tests; `sed -i.bak` for BSD/GNU portability | bash-only constructs legal under bash shebang | CLEAN, no fix |

## Checklist actually executed

- C1 unquoted dangerous operands (`rm`/`cd`/`cp`/`chroot`/`mount` followed by
  a bare `$VAR`): zero hits across all six build scripts.
- C2 bashisms in `#!/bin/sh` files (`[[`, `local`, `source`, `&>`, `==`,
  `shopt`, `pipefail`): zero hits (remaining `${...}` matches are POSIX
  parameter expansion).
- C3 heredoc quoting: every heredoc carrying `$` or backticks uses a quoted
  delimiter (`<<'EOF'` style); verified by inspection of all four build
  scripts plus `meta-branding.sh`.
- C4 `set -e` + `shift`/`grep` interactions: `shift || true` in
  `provision.sh`/`build_iso.sh`; `grep ... || true` where a zero-count is a
  legal result (`merge-layers.sh` G3/G5 counters); `grep -c` in test helpers
  runs without `set -e` so a zero count cannot abort the harness.
- C5 `read` loops: `IFS= read -r` used for the LAYERFS_PATH patch loop
  (`merge-layers.sh`); no unguarded `for x in $(...)` over filenames.

## Result

No quoting bug found, so per the fence rule (fix + proving test together or
not at all) **no build script was modified**. If shellcheck ever becomes
available on a Linux host, the one command worth running is
`shellcheck -S warning os-build/iso/*.sh os-build/iso/test/*.sh`, and any hit
it reports above this checklist should arrive with its own fixture.
