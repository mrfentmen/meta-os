# UBUNTU INVENTORY — every place the base distro still shows its name

Checked 2026-11-03 20:5x UTC against the booted image `/tmp/metaos.ext4` (read
only) and the repo payloads that build it. Two different things are listed
separately on purpose:

- **identity** — what a person reads: files, screens, prompts, fonts, icons.
  This is what we remove.
- **compatibility** — what a package manager reads: codenames, `ID_LIKE`,
  package names, font package names. This stays, or installs break.

---

## 1. Visible identity — checked and clean

| Surface | Result | How it was checked |
|---|---|---|
| `/etc/os-release` | `NAME="Meta OS"`, `VERSION="1.0 (Ribbon)"`, `ID=metaos`, `ID_LIKE=debian`, 0 Ubuntu strings | `cat` on the image |
| `/usr/lib/os-release` | same file content (symlinked) | `cat` |
| `/etc/lsb-release` | `DISTRIB_ID=MetaOS`, `DISTRIB_CODENAME=ribbon` | `cat` |
| `lsb_release -a` | `Description: Meta OS 1.0 (Ribbon)`, `Release 1.0`, `Codename ribbon` | `chroot lsb_release -a` |
| `/etc/issue` | `Meta OS 1.0 (Ribbon) \n \l` | `cat` |
| `/etc/motd` | `Meta OS 1.0 (Ribbon)`; `10-help-text` and `50-motd-news` disabled | `cat`, `ls /etc/update-motd.d` |
| Boot splash | `Theme=metaos` in `/etc/plymouth/plymouthd.conf`; no `ubuntu-text` theme on disk | `cat`, `ls /usr/share/plymouth/themes` |
| Wallpapers | only `meta-*.png`; stock Ubuntu/Xubuntu wallpaper sets removed | `ls /usr/share/backgrounds` |
| Dock/panel icons | Meta icon set present; Ubuntu icon themes not used by the session | repo payload + image |
| Shell prompt | `PS1` says `metaos` in Meta blue | `/etc/skel/.bashrc` |
| Account name | `meta` (uid 1000), no `ubuntu` account, `/home/ubuntu` gone | `/etc/passwd`, `--check` |
| Autologin | `autologin-user=meta` in both lightdm drop-ins | `/etc/lightdm/lightdm.conf.d/*.conf` |
| GRUB | no GRUB config on this image at all — nothing to rename | `ls /boot/grub/grub.cfg` |

`sh os-build/identity/debrand.sh /mnt --check` → PASS, and
`rename_user.sh /mnt --check` → PASS.

## 2. Fixed today (were real, not cosmetic)

**The account's display name still said Ubuntu.** `/etc/passwd` read
`meta:x:1000:1000:Ubuntu:/home/meta:/bin/bash`. The GECOS field is what a greeter,
`getent passwd`, `finger` and any full-name display prints. The rename script
rewrote the login name, the home path and the group lists, and never touched this
field — so the OS called the user "Ubuntu" on any screen that shows a full name.

`rename_user.sh` now rewrites it to `Meta` and its `--check` fails when it is
still `Ubuntu`. Proven on a synthetic root under Linux:

```
PASS passwd has meta
FAIL display name -- passwd still gives meta the full name Ubuntu
rename_user --check: FAIL
--- after apply ---
PASS display name
rename_user --check: PASS
```

**A rebuild would have produced an image with no account to log into.** The
payload greeter drop-in still said `autologin-user=ubuntu` while the account is
`meta`, and both `build_iso.sh` and `theme_proof.sh` asserted `ubuntu` — so the
build's own check would have passed a broken image. All four places now say
`meta` (`payload-theme/greeter/10-metaos-live.conf`, `build_iso.sh`,
`theme_proof.sh`, `payload-theme/README.md`).

**Still to apply to the live image:** the GECOS fix. It is a one-line
`usermod`-equivalent on `/etc/passwd`, and the image is in use by other agents
right now, so it is queued rather than risked. A rebuild picks it up
automatically because `rename_user.sh` is wired into `os-build/iso/provision.sh`.

## 3. Comments in code — harmless, left on purpose

These are read by a programmer, never by a user of the OS. Removing them would
make the code worse at explaining why the base is Debian.

| File | Why it says Ubuntu |
|---|---|
| `os-build/face/launcher.py:5,12` | documents which base version the allow-list was verified against |
| ~~`/etc/skel/.bashrc:120`~~ | **fixed in the source, not yet on the image.** The appended block now reads "wins over the base image's `\u@\h` prompt", and `tools/fix_terminal_prompt.sh` also patches `/home/meta/.bashrc` (it only knew `/home/ubuntu`, which no longer exists, and its receipt grep errored on the missing path). Re-run that tool against the image to rewrite the line that is on there now. |
| `payload-theme/panel/xfce4-panel.xml:6` | geometry copied from the Xubuntu panel |
| `payload-theme/apply.sh:133,158-166` | font fallbacks and the `os-release` symlink note |
| `payload-theme/theme_proof.sh` | the proof's own allow-lists |
| `identity/rename_user.sh`, `identity/debrand.sh` | explains the rename itself |

## 4. Must keep saying Ubuntu or Debian — compatibility

| Thing | Why it stays |
|---|---|
| `ID_LIKE=debian` in os-release | drives package behaviour; removing it breaks `apt` |
| `UBUNTU_CODENAME` in os-release | read by tools that compute the apt suite |
| `/etc/apt/sources.list.d/*` with `noble` | package installs resolve against noble |
| Package names (`libwebkit2gtk-4.1`, `python3-gi`, …) | renaming them is a fork, not a rebrand |
| `/usr/share/fonts/truetype/ubuntu/UbuntuMono*` | the terminal profile asks for Ubuntu Mono; it is a **font**, not branding |
| `Humanity` icon theme's `ubuntuone-*` emblems | never drawn by our dock or panel; removing them only risks breaking the theme |

The rule, same as `debrand.sh`'s header: **rewrite identity, keep
compatibility**, and say which is which when a judge asks.

## 5. Cosmetic wart, documented rather than hacked

`lsb_release -a` prints `Distributor ID: Metaos`, even though `/etc/lsb-release`
says `DISTRIB_ID=MetaOS` — Ubuntu's own `lsb_release` script title-cases the
string. The only fix is patching a system script, which is worse than the wart.
If a judge notices, the honest answer is "Ubuntu's `lsb_release` capitalises it;
the file itself says MetaOS."

## 6. Re-verify after any rebuild

```sh
sh os-build/identity/debrand.sh   /mnt --check   # expect PASS
sh os-build/identity/rename_user.sh /mnt --check # expect PASS, incl. display name
bash os-build/iso/payload-theme/theme_proof.sh   # brand-tree + autologin rows
```

If `theme_proof.sh` still reports `autologin: ubuntu`, the payload and the
account have drifted apart again — that is the failure that costs a demo.
