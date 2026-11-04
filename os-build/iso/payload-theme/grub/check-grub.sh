#!/bin/sh
# check-grub.sh — brand gate for a generated grub.cfg (live tree or installed).
# Usage: check-grub.sh <grub.cfg>
# FAILs on base-flavour brand strings in boot-visible text. The casper seed
# path (file=.../preseed/xubuntu.seed) is owned by the base ISO lane and is
# NOT boot-visible prose, so it is stripped before matching; renaming that
# file would break boot. A grub.cfg with no MetaOS title also fails.
# Exit 0 = PASS, 1 = FAIL. Static check, no boot needed.
set -eu
f=${1:?usage: check-grub.sh <grub.cfg>}
[ -f "$f" ] || { echo "FAIL grub-brand: no such file: $f"; exit 1; }
body=$(sed -E 's#file=[^ ]*/preseed/[^ ]*##g' "$f")
rc=0
if printf '%s\n' "$body" | grep -qi 'ubuntu\|xubuntu'; then
  echo "FAIL grub-brand: base-flavour string in $f:"
  printf '%s\n' "$body" | grep -in 'ubuntu\|xubuntu' | head -n 10
  rc=1
else
  echo "PASS grub-brand: no ubuntu/xubuntu in boot-visible text ($f)"
fi
if grep -q 'MetaOS' "$f"; then
  echo "PASS grub-brand: MetaOS title present ($f)"
else
  echo "FAIL grub-brand: no MetaOS title in $f"
  rc=1
fi
exit $rc
