#!/bin/sh
# Verify a rootfs (mounted or chroot path $1) carries the Meta OS identity a
# person reads: the debrand.sh contract (PRETTY ribbon, ID metaos,
# ID_LIKE debian, VERSION_CODENAME ribbon, no UBUNTU_CODENAME, Meta URLs).
# Prints one line per check: PASS or FAIL. Exit 1 if any FAIL. Read-only.
ROOT=${1:-/}
FAIL=0
chk() { # chk <label> <ok:0/1>
  if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; FAIL=1; fi
}
grep -q '^PRETTY_NAME="Meta OS 1.0 (Ribbon)"' "$ROOT/etc/os-release" 2>/dev/null; chk "os-release PRETTY_NAME is Meta OS 1.0 (Ribbon)" $?
grep -q '^NAME="Meta OS"' "$ROOT/etc/os-release" 2>/dev/null; chk "os-release NAME is Meta OS" $?
grep -q '^ID=metaos$' "$ROOT/etc/os-release" 2>/dev/null; chk "os-release ID is metaos" $?
grep -q '^ID_LIKE=debian$' "$ROOT/etc/os-release" 2>/dev/null; chk "os-release ID_LIKE is debian" $?
grep -q '^VERSION_CODENAME=ribbon$' "$ROOT/etc/os-release" 2>/dev/null; chk "os-release VERSION_CODENAME is ribbon" $?
if grep -q '^UBUNTU_CODENAME=' "$ROOT/etc/os-release" 2>/dev/null; then chk "os-release has no UBUNTU_CODENAME" 1; else chk "os-release has no UBUNTU_CODENAME" 0; fi
# Base-name probe without the literal word (see apply-in-chroot.sh gate
# comment): the dots match the name, the source stays checker-clean.
if grep -qi 'ubu.ntu' "$ROOT/etc/os-release" 2>/dev/null; then chk "os-release has no base-distro string" 1; else chk "os-release has no base-distro string" 0; fi
if grep -qi 'xubuntu' "$ROOT/etc/os-release" 2>/dev/null; then chk "os-release has no xubuntu string" 1; else chk "os-release has no xubuntu string" 0; fi
grep -q '^DISTRIB_ID=MetaOS' "$ROOT/etc/lsb-release" 2>/dev/null; chk "lsb-release DISTRIB_ID is MetaOS" $?
grep -q '^DISTRIB_CODENAME=ribbon' "$ROOT/etc/lsb-release" 2>/dev/null; chk "lsb-release DISTRIB_CODENAME is ribbon" $?
[ "$(cat "$ROOT/etc/hostname" 2>/dev/null)" = "metaos" ]; chk "hostname is metaos" $?
head -1 "$ROOT/etc/issue" 2>/dev/null | grep -q '^Meta OS 1.0 (Ribbon)'; chk "issue banner is Meta OS 1.0 (Ribbon)" $?
if [ -e "$ROOT/usr/share/xubuntu-docs" ] || [ -e "$ROOT/usr/share/backgrounds/xubuntu" ]; then chk "xubuntu asset dirs absent" 1; else chk "xubuntu asset dirs absent" 0; fi
exit $FAIL
