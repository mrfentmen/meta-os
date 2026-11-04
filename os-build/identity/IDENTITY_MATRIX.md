# IDENTITY_MATRIX — every identity surface, its file, its lane, its state

Checked 2026-11-04 against the repo tree plus staged-root runs of
`debrand.sh --apply/--check` and `rename_user.sh` (no boot, no mount).
`PASS` = the file in this tree is contract-correct (and the staged-root run
proves the installer writes it). `not mine` = another lane owns the file:
named here, never edited here.

Contract reminder: `PRETTY_NAME="Meta OS 1.0 (Ribbon)"`, `NAME="Meta OS"`,
`VERSION="1.0 (Ribbon)"`, `ID=metaos`, `ID_LIKE=debian` (never `ubuntu`),
`VERSION_CODENAME=ribbon`, hostname `metaos`, user `meta`.

| surface | file that owns it | lane | today |
|---|---|---|---|
| /etc/os-release | `os-build/iso/payload-theme/identity/os-release` (installed by payload `apply.sh`; rewritten again by `debrand.sh` at provision) | OS-1 | PASS |
| /usr/lib/os-release | symlink target of the above on stock Ubuntu; `debrand.sh` writes through it, never replaces it (proven: `ls -l` before/after on staged root) | OS-1 | PASS |
| /etc/lsb-release | `os-build/iso/payload-theme/identity/lsb-release` (`DISTRIB_ID=MetaOS`, `DISTRIB_CODENAME=ribbon`, matching `debrand.sh`) | OS-1 | PASS |
| /etc/issue, /etc/issue.net | `os-build/iso/payload-theme/identity/issue{,.net}` (no `\s \r \m \v` hostname escapes; `issue.net` has none at all, correct for net) | OS-1 | PASS |
| motd: /etc/motd + update-motd.d/00-header | `os-build/iso/payload-theme/identity/motd` (honest 3-line banner) + `00-header` (title echo) | OS-1 | PASS |
| login motd scripts 10-help-text / 50-motd-news | disabled by rename to `*.metaos-disabled` (`debrand.sh`); `90-updates-available` deliberately kept (real security info) | OS-1 | PASS |
| hostname + 127.0.1.1 | `os-build/iso/payload-theme/identity/hostname` (`metaos`); hosts line written by `debrand.sh` + payload `apply.sh` + dexubuntu (all say `metaos`) | OS-1 | PASS |
| GECOS / display name of `meta` | `rename_user.sh` rewrites field 5 `[Uu]buntu` → `Meta` and `--check` asserts it (proven on staged root) | OS-1 | PASS |
| account rename ubuntu → meta | `rename_user.sh` (passwd/shadow/group, subuid/subgid, home move, lightdm, casper, home-path sweep) — pure file surgery, safe on an unbooted root | OS-1 | PASS (staged root) |
| desktop .desktop names | `debrand.sh` rewrites Xubuntu/Ubuntu → Meta OS under `usr/share/desktop-directories` + `usr/share/applications` (scoped, never packages); `--check` now covers them (`desktop names clean`) | OS-1 | PASS |
| plymouth theme dead weight | `debrand.sh` removes `usr/share/plymouth/themes/ubuntu*` (folded in from `debrand2.sh`); active theme stays `metaos` | OS-1 | PASS |
| stock wallpapers + every backdrop pointer | `debrand.sh` removes greybird/xfce assets (refuses if no Meta wallpaper) and repoints all `last-image` entries; `--check` covers all five sub-states | OS-1 | PASS |
| greeter (LightDM) | `os-build/iso/payload-theme/greeter/*` (10-metaos-live.conf, gschema override, lightdm confs) | Buffy (payload-theme/greeter) — `not mine` | PASS (comments only; `check_strings` clean) |
| login banner (what a person reads at login) | motd + issue fragments above | OS-1 | PASS |
| About page (`about.json`) | `os-build/face/session.sh` reads live `/etc/os-release` (`VERSION_CODENAME` → now `ribbon`, was `noble`) | Buffy (`os-build/face/`) — `not mine` | PASS (code is honest; data fixed this lane) |
| terminal prompt | `os-build/tools/fix_terminal_prompt.sh` repaints the prompt on the staged root | OS-4 (`os-build/tools/`) — `not mine` | PASS (tool exists; prompt reads renamed user) |
| /etc/skel prompt/banner files | no skel files in this repo; skel is populated from the base ISO and patched in place by OS-4's prompt fixer | OS-3 (defaults) / OS-4 (fixer) — `not mine` | no repo file to fix |
| installer-written os-release | `os-build/iso/calamares/meta-branding.sh` writes `ID_LIKE=ubuntu` + non-contract PRETTY/NAME and copies it over `/etc/os-release` on the INSTALLED system — last writer wins, so this defeats every fix above on install media | OS-2 (`os-build/iso/calamares/`) — `not mine` | FAIL (request filed below) |
| dexubuntu gap-fill os-release | `os-build/metaos1-base/dexubuntu/identity/os-release` ships `ID_LIKE=ubuntu` + `UBUNTU_CODENAME` + `MetaOS 1.0` (no Ribbon) | Pax / metaos1-base owner — `not mine` | FAIL (request filed below) |
| desktop entry Comments | `agent-layer/desktop-entries/atril.desktop`, `evince.desktop` show Xubuntu text in menus | OS-3 (`agent-layer/`) — `not mine` | FAIL (request filed below) |
| dock fallback home dir | `os-build/face/meta-desktop.sh` falls back to `/home/ubuntu` when `$HOME` is unset | Buffy (`os-build/face/`) — `not mine` | FAIL (request filed below) |
| payload `VERSION`/motd wording | fixed this lane (see report) | OS-1 | PASS |

Competing writers, last-wins order on a provisioned root: dexubuntu `apply-in-chroot.sh`
→ payload `apply.sh` → `debrand.sh` (+ `rename_user.sh`, `debrand2.sh`) → (install
media only) `meta-branding.sh` overwrites `/etc/os-release` again. The last row
above is why the installed system still ends Ubuntu despite every earlier fix.
