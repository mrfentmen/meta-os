# OC1 copy — ONE directory, sha-pinned (from opencode2/landwalls)

Source dir on OC2 branch: `agent-layer/desktop-entries/`
OC1 copies (never OC2 pushing):

```sh
mkdir -p /tmp/oc2-dropin
cp -r agent-layer/desktop-entries /tmp/oc2-dropin/
cd /tmp/oc2-dropin/desktop-entries
shasum -a 256 mousepad.desktop ristretto.desktop atril.desktop \
  evince.desktop thunar.desktop meta-agent-status.desktop mimeapps.list
```

Expected (from `agent-layer/MANIFEST.md`, tip a012558f):

- `11e146a7…3652b025fd0` mousepad.desktop
- `95b85d2a…bac49895` ristretto.desktop
- `0990716e…711f92` atril.desktop
- `a7ae673c…39fcb69` evince.desktop (degraded-off, NoDisplay=true)
- `2ae2d8c3…85e262c` thunar.desktop
- `68a373a0…17a3d1c` meta-agent-status.desktop (byte-copy of Bond's)
- `2d35dc75…581f5369a6` mimeapps.list (drop-in; PDF→atril)
- `0d69d215…16b53b84` README.md (docs, not installed)

Install (OC1 target):

```sh
sudo cp *.desktop /usr/share/applications/
sudo cp mimeapps.list /etc/xdg/mimeapps.list
sh agent-layer/verify-dropin-desktop.sh
# DESKTOP OK lines; SKIP only where the desktop lane is not installed.
```

Notes:

- Canonical PDF map stays Hana's
  `os-build/metaos1-base/defaults/mimeapps.list` (evince). This drop-in is
  proposal-only. If Hana acks evince present, OC1 flips one line to
  `evince.desktop` — no repack.
- `meta-agent-status.desktop` must stay a byte-copy of Bond's
  `iso/apps/desktop/meta-agent-status.desktop` (validator enforces it).
- No credentials anywhere (validator greps for them).
