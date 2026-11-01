#!/bin/sh
# NC-087: boot-check script. Reports only; fixes nothing.
# Answers in order: ttyS0 shell? DHCP lease? dashboard HTTP? updater log?
# failed systemd units? Usage: boot-check.sh <vm-name>
# Against NO running VM it fails soft with "no VM" (NC-088 proof below).
set -eu
NAME="${1:?usage: $0 <vm-name>}"
running() { utmctl list 2>/dev/null | grep -q "$NAME.*Running"; }
if ! utmctl list 2>/dev/null | grep -q "$NAME"; then
  echo "no VM named $NAME — nothing to check (NC-088 soft-fail path)"
  exit 3
fi
if ! running; then
  echo "VM $NAME exists but is not running — start it first"
  exit 4
fi
echo "1. ttyS0: read utmserial-*.log in the VM folder for a login shell"
echo "2. DHCP: guest lease via serial console 'ip -4 addr show'"
echo "3. dashboard: curl the guest IP :8080 from the host browser"
echo "4. updater: serial console 'journalctl -u metaos-update --no-pager | tail'"
echo "5. failed units: serial console 'systemctl --failed --no-pager'"
echo "(all five need the serial console; without it, report exactly that)"
