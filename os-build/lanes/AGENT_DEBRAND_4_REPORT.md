# AGENT DEBRAND-4 REPORT

Branch `agent-debrand-4`, worktree `/tmp/agent-debrand-4`. No merge, no push.
Only `os-build/tools/` files plus this report touched. QEMU guard left on;
`pgrep -f qemu-system` empty before and after all work.

## What changed (3 files)

- `os-build/tools/verify_tree.sh` — extended to 10 rows: folded lane
  checkers (`debrand-strings` → check_strings.sh bare, `desktop-entries-check`
  → check_entries.sh --check, `profile-check` → check_profile.sh --check,
  `tokens-check` → test_tokens.sh bare; stale selftest.sh/check_desktop.sh
  paths replaced with the real files), new inline rows `no-stock-art`,
  `wallpaper-reachability`, `brand-identity` (line-anchored machine
  contexts with per-hit reasons), absent format now `absent (owner: lane N)`,
  `run_checker` takes per-checker args. macOS bash-3.2 note: `case` inside
  `$()` is a syntax error there — the symlink scan uses a temp file.
- `os-build/tools/DEBRAND_GATE.md` — new: per-row proves/cannot-prove,
  image-path map, known conditions, exact commands.
- This report.

## Proof (all run, outputs kept)

- `sh -n` clean. Full table: 4 PASS/expected rows
  (`allowlist` 294 lines, `desktop-entries-check`, `profile-check`,
  `tree-refs` 22 files, `no-stock-art`, `wallpaper-reachability`) and FAILs:
  `debrand-strings` (+x bit; content separately has 78 unsuppressed hits),
  `tokens-check` (+x bit only; content 18/18), `brand-identity` (3 artifact
  lines), `no-ubuntu` (5 files). Exit 1 with `DEAD:` naming all four.
- `--json | python3 -m json.tool` parses. Absent mechanism proven on an
  empty root: all lane rows read `absent (owner: lane N)`.
- Planted faults (each added, observed, removed; worktree `git status`
  clean of plants after): `greybird-wall-green.png` → `no-stock-art FAIL:
  1 stock-art hits`; `Comment=Xubuntu probe entry` (.desktop) →
  `brand-identity` 3→4 hits with file:line; `ID_LIKE=ubuntu` (+NAME/ID)
  os-release → `brand-identity` 3→5 hits.

## Cross-lane findings (reported, not fixed)

- Lane 2: `check_strings.sh` lacks +x; lane 1: `test_tokens.sh` lacks +x —
  `chmod +x` both (rows report "present but not executable" until then).
  Consider allowlist rows for checker pattern-literals
  (including this gate's `-e` lines) or accept documented self-hits.
  `brand-identity` needs a ruling on `os-build/iso/calamares/meta-branding.sh:33`
  (OS-2's writer) and `dexubuntu/identity/os-release:7,12`.
- Lane 3: `check_entries.sh` is the real entries checker; verify_tree's old
  `selftest.sh`/`check_desktop.sh` paths never existed.
- OS-2: `meta-branding.sh:33` writes `ID_LIKE=ubuntu` over /etc/os-release
  (already in IDENTITY_MATRIX as your FAIL — gate now fails on it too).
- Buffy: `spike-{a,b}-session.sh` orphans in `os-build/face/`; theme drift
  table belongs to the art lane, not re-derived here.
- `no-ubuntu`'s 5 survivors (terminal checker self-grep, READMEs, tokens
  test patterns) are known-leak prose the allowlist deliberately omits.
