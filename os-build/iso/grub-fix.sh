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
    ('Try or Install Xubuntu', 'Try or Install Meta OS 1.0'),
    ('Xubuntu (safe graphics)', 'Meta OS 1.0 (safe graphics)'),
    ('Advanced options for Ubuntu', 'Advanced options for MetaOS'),
    ('Ubuntu, with Linux', 'MetaOS, with Linux'),
    ("menuentry 'Ubuntu'", "menuentry 'MetaOS'"),
    ('menuentry "Ubuntu"', 'menuentry "MetaOS"'),
    ('--class ubuntu', '--class metaos'),
    ('--class xubuntu', '--class metaos'),
    ('Xubuntu', 'MetaOS'),
]:
    s = s.replace(old, new)
# Default by name (a kernel update cannot reorder it) and a demo-friendly
# timeout that still allows recovery. Recovery prints: no quiet splash.
import re
before = s
s = re.sub(r'^set timeout=.*$', 'set timeout=10', s, flags=re.M)
s = re.sub(r'^set default=.*$', 'set default="Try or Install Meta OS 1.0"', s, flags=re.M)
if not re.search(r'^set default=', s, flags=re.M):
    s = 'set default="Try or Install Meta OS 1.0"\n' + s
n_rec = 0
def fix_recovery(m):
    global n_rec
    line = m.group(0)
    if 'quiet splash' in line:
        n_rec += 1
        line = line.replace(' quiet splash', '')
    return line
s = re.sub(r'^(\s*linux\s.*)$', fix_recovery, s, flags=re.M)
open(p, 'w').write(s)
titles = sum(s.count(t) for t in ['Try or Install Meta OS 1.0', 'Meta OS 1.0 (safe graphics)'])
print('grub fixed:', s.count('layerfs-path='), 'layerfs,', s.count('console=ttyS0'), 'console,', titles, 'titles,', n_rec, 'recovery-quiet-removed, timeout=10 default="Try or Install Meta OS 1.0"')
PYEOF
