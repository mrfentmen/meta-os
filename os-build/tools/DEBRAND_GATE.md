# DEBRAND_GATE — what verify_tree.sh proves about Ubuntu leftovers

One command, no boot, no network:

```
sh os-build/tools/verify_tree.sh          # table, exit 1 + DEAD: on failure
sh os-build/tools/verify_tree.sh --json   # same rows as JSON (parses: | python3 -m json.tool)
```

Exit code is stable: 0 iff no row reads FAIL. `absent (owner: lane N)` rows
never fail the run. Timing and `DEAD:` go to stderr, so `--json` is pure
JSON on stdout. Works from any directory; uses `find`, never git.

## Row by row: proves / cannot prove

| Row | Proves | Cannot prove |
|---|---|---|
| `allowlist` | lane 2's `ALLOWLIST.tsv` exists and is non-empty | nothing about its contents (a wrong row passes this row) |
| `debrand-strings` | lane 2's `check_strings.sh` whole-word sweep (ubuntu/Ubuntu/Xubuntu/xubuntu/canonical/Canonical, allowlist-subtracted, `file:line` output) passes | nothing if the script is missing/not executable (row reports that instead); English prose *about* leaks is allowlisted by path, so it passes by design |
| `desktop-entries-check` | lane 3's `check_entries.sh --check`: keys, Comment, TryExec, Categories, no banned words in drop-ins | icon existence (proven separately per that script's header) |
| `profile-check` | terminal profile copies parse, agree, name no Ubuntu font | that the profile is actually installed anywhere |
| `tokens-check` | generated theme files agree with `meta.tokens.json`, no ubuntu string on the four visible surfaces | anything about the live image |
| `no-stock-art` | no greybird-wall*/warty* files, no emerald/ubuntu-logo/ubuntu-text theme dirs, no symlinks or `update-alternatives --set/--install` targeting ubuntu-text, no desktop-base wallpaper *values* in xml/conf | prose mentions (docs, plan, comments) — artifacts and live values only, by design |
| `wallpaper-reachability` | every `last-image`/`background=` in shipped xml/greeter confs resolves to a repo art file; every wallpaper source file is Meta-named (`meta-*`, `greeter-*`, `loop-*`) or allowlisted | that the installer actually copies them (that's the image build's job) |
| `brand-identity` | no `ID_LIKE=ubuntu`, `ID=ubuntu`, `NAME=Ubuntu`, `PRETTY_NAME="Ubuntu…`, `DISTRIB_ID=Ubuntu`, `UBUNTU_CODENAME`, `Comment=…Xubuntu` at line start in machine-readable files, with a reason per hit | prose *about* these fields (matrix, inventory, READMEs) — line-anchored patterns skip sentences on purpose |
| `tree-refs` | shipped `.desktop` files have Name+Exec, absolute icons resolve | that Exec binaries exist (needs the image) |
| `no-ubuntu` | no case-insensitive `ubuntu` substring in shipped sources, minus allowlist paths | whole-word precision (that's `debrand-strings`); docs outside shipped scope |

Image-path map used by `wallpaper-reachability`
(`iso/theme/wallpaper/` holds the PNGs; the greeter `background=` values
point at `/usr/share/backgrounds/meta-ascii.png`, sourced from
`os-build/iso/payload-theme/wallpapers/`):

- `/usr/share/metaos/theme/*.png` → `iso/theme/wallpaper/<same basename>`
- `/usr/share/backgrounds/meta-*.png` → `os-build/iso/payload-theme/wallpapers/<same basename>`

## Known conditions (not bugs in the gate)

- The gate script itself appears in `debrand-strings` output: its `-e`
  patterns necessarily contain the banned words (as do lane 2/3's own
  checkers). Recognize them by path (`os-build/tools/verify_tree.sh`) and
  by content (pattern literals, not product claims). Lane 2 may allowlist
  the gate's pattern lines; until then they are documented noise.
- `check_strings.sh` and `test_tokens.sh` ship without +x, so their rows
  FAIL as "present but not executable" (run via `sh` directly, both
  underlying contents behave as reported: strings has 78 unsuppressed hits,
  tokens 18/18 pass). Lane 1/2: `chmod +x` both.
- `brand-identity` currently FAILs on 3 pre-existing artifact lines, none
  allowlisted on purpose: `os-build/iso/calamares/meta-branding.sh:33`
  (`ID_LIKE=ubuntu`, OS-2's file),
  `os-build/metaos1-base/dexubuntu/identity/os-release:7,12`
  (`ID_LIKE=ubuntu`, `UBUNTU_CODENAME=noble`). Requests filed in the lane
  report; the gate stays red until the owning lanes fix or lane 2
  allowlists them.

## Exact commands (all run from the repo root)

```
sh -n os-build/tools/verify_tree.sh
sh os-build/tools/verify_tree.sh
sh os-build/tools/verify_tree.sh --json | python3 -m json.tool
sh os-build/identity/check_strings.sh --explain   # reasons per hit
pgrep -f qemu-system                               # must print nothing
```
