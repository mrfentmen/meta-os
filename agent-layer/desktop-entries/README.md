# OC2 desktop-entries drop-in (NO VM, for OC1 to copy by sha)

One-directory handoff per `os-build/OC123_DEMO_4H.md`: OC1 copies this
directory, records shas, installs to `/usr/share/applications/` (desktop
files) + `/etc/xdg/mimeapps.list` or `~/.config/mimeapps.list` (mimeapps).

Provenance (copy-only, no forks):
- `meta-agent-status.desktop`: byte-copy of Bond's
  `iso/apps/desktop/meta-agent-status.desktop` (Exec=meta-agent-status).
  If Bond updates theirs, re-copy — never diverge.
- `thunar.desktop`: Exec mirrors Bond's `iso/apps/desktop/meta-files.desktop`
  (`Exec=thunar %U`) under a package-named filename so the MIME/packaging
  check (`validate.py` desktop->package map) resolves.
- `mousepad.desktop` / `ristretto.desktop`: authored from KEEP
  (`os-build/metaos1-base/packages.txt`) + Hana MIME map. No source .desktop
  exists in repo — these are net-new, package-named.
- `atril.desktop` (active) vs `evince.desktop` (NoDisplay=true, degraded-off):
  Xubuntu 24.04.5 base ships atril where KEEP lists evince. OC2 does NOT edit
  Hana's `packages.txt` or `defaults/mimeapps.list`. This pack ships both and
  maps PDF to atril in the drop-in `mimeapps.list` with a comment. If Hana
  records evince present, OC1 flips one line to evince.desktop — no repack.
- `mimeapps.list`: drop-in proposal only. Covers exactly text/plain,
  image/png, image/jpeg, application/pdf. Leaves http/https unmapped (Bond).

Install targets (OC1):
- `*.desktop` → `/usr/share/applications/`
- `mimeapps.list` → `/etc/xdg/mimeapps.list` (system) or console
  `~/.config/mimeapps.list` via firstboot (see
  `os-build/metaos1-base/firstboot/metaos1-firstboot.sh`)

Proof: `tests/agent-layer/test_desktop_entries.py` green.
