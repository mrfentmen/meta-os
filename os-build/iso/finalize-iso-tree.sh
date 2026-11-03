#!/bin/sh
# Finalize ISO tree before xorriso: grub fixes + branding strings.
TREE=${1:?iso tree root (contains boot/grub/grub.cfg)}
python3 - "$TREE/boot/grub/grub.cfg" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p).read()
if 'layerfs-path=' not in s:
    s = s.replace('/casper/vmlinuz ', '/casper/vmlinuz layerfs-path=filesystem.squashfs ')
    s = s.replace('/casper/vmlinuz nomodeset ', '/casper/vmlinuz layerfs-path=filesystem.squashfs nomodeset ')
if 'console=ttyS0' not in s:
    s = s.replace(' --- quiet splash', ' console=ttyS0 --- quiet splash')
s = s.replace('Try or Install Xubuntu', 'Try or Install MetaOS')
s = s.replace('Xubuntu (safe graphics)', 'MetaOS (safe graphics)')
open(p, 'w').write(s)
print('grub: layerfs=%d console=%d' % (s.count('layerfs-path='), s.count('console=ttyS0')))
PYEOF
echo "MetaOS 1.0 LTS" > "$TREE/.disk/info" 2>/dev/null && echo "disk-info set" || echo "disk-info skipped"
