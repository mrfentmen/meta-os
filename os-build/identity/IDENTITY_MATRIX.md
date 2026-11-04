# IDENTITY_MATRIX — every identity surface, its file, its lane, its state

Checked 2026-11-04 against the repo tree plus staged-root runs of
`debrand.sh --apply/--check` (regular + symlink root) and the payload files
in `os-build/iso/payload-theme/identity/`. No boot, no mount: `hostnamectl`
and `lsb_release` rows trace which files those tools read instead of running
them. `PASS` = this tree is contract-correct. `not mine` = another lane owns
the file: named, never edited.

Contract: `PRETTY_NAME="Meta OS 1.0 (Ribbon)"`, `NAME="Meta OS"`,
`VERSION="1.0 (Ribbon)"`, `VERSION_ID="1.0"`, `VERSION_CODENAME=ribbon`,
`ID=metaos`, `ID_LIKE=debian` (never `ubuntu`, no `UBUNTU_CODENAME`),
`DOCUMENTATION_URL="https://metaos.local/docs"` (plus HOME/SUPPORT/BUG
`https://metaos.local*`), hostname `metaos`, user `meta`, product `Meta OS`.

| surface | file that owns it | lane that owns it | state today |
|---|---|---|---|
| os-release (installed) | `/etc/os-release` ← `debrand.sh` (primary writer; `identity/os-release` payloads are copies) | OS-1 | PASS — `ID_LIKE=debian`, `VERSION_CODENAME=ribbon`, no `UBUNTU_CODENAME`, `DOCUMENTATION_URL` stamped; payload `payload-theme/identity/os-release` lags by that one key (request to theme lane) and provision-all.sh step 4c re-runs debrand last, so the lag never survives |
| /usr/lib/os-release | symlink target of the above on stock Ubuntu; `debrand.sh` writes through it, never replaces it (proven: `ls -l` before/after on staged root) | OS-1 | PASS |
| lsb-release | `/etc/lsb-release` ← payload `identity/lsb-release` + `debrand.sh` | OS-1 | PASS — `DISTRIB_ID=MetaOS`, `CODENAME=ribbon`; `lsb_release -a` reads these files, so it prints Meta |
| login banner (local) | `/etc/issue` ← payload `identity/issue` + `debrand.sh` (`\n \l` escapes, no hostname baked in) | OS-1 | PASS |
| login banner (remote) | `/etc/issue.net` ← payload `identity/issue.net` + `debrand.sh` | OS-1 | PASS |
| motd | static `/etc/motd` (Meta title + pointer) + `/etc/update-motd.d/00-header` (3-line banner); `10-help-text` + `50-motd-news` disabled, `90-updates-available` kept (real info) | OS-1 | PASS (`debrand.sh` writes `/etc/motd` too since R2; payload `identity/motd` still names the base — request to theme lane, harmless: debrand runs last) |
| hostname | `/etc/hostname` = `metaos`, `/etc/hosts` `127.0.1.1 metaos` (payload `identity/hostname` + `apply.sh` + `debrand.sh`) | OS-1 | PASS |
| `hostnamectl` | reads `/etc/hostname` (static hostname) and `/etc/os-release` (`Operating System:` line); no machine-info in payload, so no pretty-name override | OS-1 (files) | PASS by trace — prints `metaos` / `Meta OS 1.0 (Ribbon)` |
| account rename ubuntu → meta | `rename_user.sh` (passwd/shadow/group, subuid/subgid, home move, lightdm, casper, home-path sweep) — pure file surgery, safe on an unbooted root | OS-1 | PASS (staged root in prior lane work; GECOS covered below) |
| GECOS display name | `usermod -c "Meta" meta` on the live system (or the `passwd` 5th field on a staged root); `rename_user.sh --check` asserts it is not Ubuntu | OS-1 | PASS (check exists; command is `usermod -c "Meta" meta`) |
| distro lookups in shipped code | `os-build/face/facts.py:19-25` reads `PRETTY_NAME` from `/etc/os-release` and returns it — prints Meta after debrand, Ubuntu before; no other `platform.`/`distro.`/`lsb_release` consumers in `os-build/face/*.py` or `os-build/iso/payload-apps/` | Buffy (`os-build/face/`) — `not mine` | PASS by trace, no edit needed |
| desktop .desktop names | `debrand.sh` rewrites Xubuntu/Ubuntu → Meta OS under `usr/share/desktop-directories` + `usr/share/applications` (scoped, never packages); payload greeter drop-in already Meta | OS-1 | PASS (staged root) |
| plymouth theme dead weight | `debrand.sh` removes `usr/share/plymouth/themes/ubuntu*` (folded in from `debrand2.sh`); active theme stays `metaos` | OS-1 | PASS (staged root) |
| stock wallpapers + backdrops | `debrand.sh` removes `greybird.svg` + `backgrounds/xfce/`, repoints every `last-image` at `meta-wallpaper.png` (all monitor names, not just today's) | OS-1 | PASS (staged root) |
| terminal prompt + skel | `/etc/skel/.bashrc`, `/home/meta/.bashrc` prompt color/prefix; `payload-theme/terminal/` profile (font `Ubuntu Mono` = compat) | OS-3 (`payload-theme/terminal/`) — `not mine` | see OS-3 |
| greeter / login screen | lightdm greeter configs, background, logo | OS-2 (`os-build/iso/{plymouth,splash,calamares}`, greeter) — `not mine` | see OS-2 |
| About page | version panel (agent-4's `about.html`) | agent-4/Buffy (`os-build/face/`) — `not mine` | see owner |
| installer-written os-release | `os-build/iso/calamares/meta-branding.sh` re-stamps the exact debrand contract (`ID_LIKE=debian`, ribbon, Meta URLs) over `/etc/os-release` on the INSTALLED system — last writer wins, and the winner is now contract-correct | OS-1 (gated this lane, R2) | PASS by trace: settings.conf exec order runs meta-branding after unpackfs + bootloader, before umount; contract values verified byte-identical to `debrand.sh` output |
| dexubuntu gap-fill os-release | `os-build/metaos1-base/dexubuntu/identity/os-release` = debrand contract (`ID_LIKE=debian`, `VERSION_CODENAME=ribbon`, no `UBUNTU_CODENAME`); `apply-in-chroot.sh` gates the payload and refuses a fork | OS-1 (fixed this lane, R2) | PASS — payload diffed byte-identical to `debrand.sh` output |
| dock fallback home dir | `os-build/face/meta-desktop.sh` falls back to `/home/ubuntu` when `$HOME` is unset | Buffy (`os-build/face/`) — `not mine` | FAIL (request filed below) |
| desktop-entry Comments | `agent-layer/desktop-entries/{atril,evince}.desktop` `Comment=` names the Xubuntu base (user-visible in menus) | OS-3 (`agent-layer/desktop-entries/`) — `not mine` | FAIL (request filed below) |

Requests: `payload-theme/apply.sh` must stop writing identity files or route
through `debrand.sh` (theme lane — `test_single_writer.sh` names its
file:lines); `payload-theme/identity/os-release` needs the added
`DOCUMENTATION_URL` key and `payload-theme/identity/motd` must stop naming
the base (theme lane); the dock fallback is fixed in-tree (getent first);
the two `Comment=` lines are already clean (verified read-only, no request).
`build_iso.sh` replays the base ISO without `-volid`, so the mastered ISO
keeps the base volume id — request to the boot lane: add
`-volid "METAOS_1_0"` to the xorriso invocation (`os-build/iso/build_iso.sh`
near line 292; precedent already exists in `os-build/iso/repack-iso.sh:61`).
`os/os/build-image.sh:56` and `crates/os-boot/assets/os/build-image.sh:56`
write `etc/hostname` (already the contract value — request to their owners
to route through debrand or mark gated).
The `casper.conf` transplant (`os-build/iso/merge-layers.sh:102`) still
carries the base live-user name into the image — request to the boot lane to
rewrite `USERNAME=` at transplant time (rename covers the installed system,
not the live squashfs seed).
