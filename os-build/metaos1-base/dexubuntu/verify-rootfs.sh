#!/bin/sh
# Verify a rootfs (mounted or chroot path $1) carries MetaOS identity and
# no Xubuntu identity in the files a user actually sees. Prints one line
# per check: PASS or FAIL. Exit 1 if any FAIL. Read-only.
ROOT=${1:-/}
FAIL=0
chk() { # chk <label> <ok:0/1>
  if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; FAIL=1; fi
}
grep -q '^PRETTY_NAME="MetaOS 1.0"' "$ROOT/etc/os-release" 2>/dev/null; chk "os-release PRETTY_NAME is MetaOS 1.0" $?
grep -q '^NAME="MetaOS"' "$ROOT/etc/os-release" 2>/dev/null; chk "os-release NAME is MetaOS" $?
if grep -qi 'xubuntu' "$ROOT/etc/os-release" 2>/dev/null; then chk "os-release has no xubuntu string" 1; else chk "os-release has no xubuntu string" 0; fi
grep -q '^DISTRIB_ID=MetaOS' "$ROOT/etc/lsb-release" 2>/dev/null; chk "lsb-release DISTRIB_ID is MetaOS" $?
[ "$(cat "$ROOT/etc/hostname" 2>/dev/null)" = "metaos" ]; chk "hostname is metaos" $?
head -1 "$ROOT/etc/issue" 2>/dev/null | grep -q '^MetaOS 1.0'; chk "issue banner is MetaOS 1.0" $?
if [ -e "$ROOT/usr/share/xubuntu-docs" ] || [ -e "$ROOT/usr/share/backgrounds/xubuntu" ]; then chk "xubuntu asset dirs absent" 1; else chk "xubuntu asset dirs absent" 0; fi
exit $FAIL
