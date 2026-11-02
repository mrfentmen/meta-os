# Light gate — the clean-clone gate without cargo or QEMU

Lane 5 of `BOND_LIGHT_LANES.md` (Bond, 2026-11-02). One command proves the
parts of a clean-clone gate that fit an 8GB machine:

```sh
./os-build/tools/light_gate.sh
```

Exit `0` = every check passed (warnings may be present). Exit `1` = a real
check failed; the temp dir is kept and its path printed. Exit `2` = a required
tool is missing. `KEEP=1` keeps the temp dir on success too.

## What it checks

| Stage | Check |
|---|---|
| clone | Clones this repo's `HEAD` into a fresh temp dir, checks out the exact source commit, proves the clone's `HEAD` is the same commit. |
| tree | Compares the tracked file list (`git ls-files`, `.git` excluded) and the committed `HEAD` tree hash-for-hash. On a clean worktree it also compares the sha256 of every tracked file's bytes. |
| docs | Runs the exact boot-log grep lines stated in `os-build/gates.md` (`-F` for fixed strings, `-E` for the K5 tick line), checks every log path named there exists, asserts no committed log carries a K7 claim, and resolves every path-shaped reference in `BOND_LIGHT_LANES.md`. The hardcoded patterns are also checked against `gates.md` so the script cannot drift from the documented gate. |
| suites | Inside the clone: `npm test` (Node `node:test`, no install needed), then `pytest` once per Python directory — `tests/queue-python`, `tests/custos`, `tests/officina` (they cannot share one run: custos and officina both define `test_pack.py`). |

Every stage prints `ok`, `FAIL`, or `WARN` per line; the `FAIL` lines name the
file and the string that did not match. Nothing is piped through a filter that
would hide an exit status.

## What it deliberately does not run

- `cargo build` / `cargo check` / `cargo test` over the crates workspace.
- QEMU/UTM against the kernel or the face image.
- Anything holding a model.

The script prints both omissions as `SKIP` lines at the end. A green light gate
is **not** a green full `os-build/gate.sh`: the full gate still has to compile
the userspace binaries and the kernel and boot the image on a Mac. Quote the
light gate for the clone/tree/docs/suites claim only.

## Dirty worktrees

A clean-clone gate compares committed history. When the worktree is dirty (normal
mid-lane), the script prints a `WARN`, compares the committed `HEAD` trees instead
of worktree bytes, and never treats uncommitted files as if they were in the
clone. A lane's new tests are therefore not run by this gate until they are
committed; run them directly for lane evidence.

## Known drift this gate reports (2026-11-02)

The gate is meant to fail on drift, so these are findings, not script bugs:

- **K3 banner line:** `gates.md` says
  `grep 'META OS - milestone K3' os-build/logs/K3-boot.txt`, but the committed
  `K3-boot.txt` contains `K3 timer: 10 ticks after 407902 spins` and no
  `milestone K3` line. The check fails and names the file.
- **K7 wording:** `gates.md` says `K7: NO LOG`, but
  `os-build/logs/K7-boot.txt` exists; its banner is `META OS 0.1 (K6)`, so it
  makes no K7 claim. The script passes the claim check and emits a `WARN` for
  the stale wording.

Fixing either document is a separate call: this lane builds the instrument and
reports what it measures. It does not edit `gates.md`.
