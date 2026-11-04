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
# Meta titles for every entry (live + installed): the base flavour ships
# "Try or Install Xubuntu" / "Xubuntu (safe graphics)", and a post-install
# grub-mkconfig emits "Ubuntu", "Advanced options for Ubuntu" and
# "Ubuntu, with Linux ... (recovery mode)". str.replace is idempotent, so a
# second run is a no-op. The casper seed path (preseed/*.seed) is left alone:
# renaming it would break boot, not brand it. --class values ARE rewritten
# (theme.txt ships no icons, so the class selects nothing visible).
for old, new in [
    ('Try or Install Xubuntu', 'Try or Install MetaOS'),
    ('Xubuntu (safe graphics)', 'MetaOS (safe graphics)'),
    ('Advanced options for Ubuntu', 'Advanced options for MetaOS'),
    ('Ubuntu, with Linux', 'MetaOS, with Linux'),
    ("menuentry 'Ubuntu'", "menuentry 'MetaOS'"),
    ('menuentry "Ubuntu"', 'menuentry "MetaOS"'),
    ('--class ubuntu', '--class metaos'),
    ('--class xubuntu', '--class metaos'),
    ('Xubuntu', 'MetaOS'),
]:
    s = s.replace(old, new)
open(p, 'w').write(s)
print('grub fixed:', s.count('layerfs-path='), 'layerfs,', s.count('console=ttyS0'), 'console')
PYEOF
