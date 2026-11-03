#!/bin/sh
# Re-apply MetaOS grub edits after any tree export (exports clobber these).
f="$1"; [ -z "$f" ] && f=/tmp/isowork/isowork/boot/grub/grub.cfg
python3 - "$f" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p).read()
if 'layerfs-path=' not in s:
    s = s.replace('/casper/vmlinuz ', '/casper/vmlinuz layerfs-path=filesystem.squashfs ')
    s = s.replace('/casper/vmlinuz nomodeset ', '/casper/vmlinuz layerfs-path=filesystem.squashfs nomodeset ')
if 'console=ttyS0' not in s:
    s = s.replace(' --- quiet splash', ' console=ttyS0 --- quiet splash')
open(p, 'w').write(s)
print('grub fixed:', s.count('layerfs-path='), 'layerfs,', s.count('console=ttyS0'), 'console')
PYEOF
