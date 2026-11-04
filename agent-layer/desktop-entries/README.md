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
  check (`os-build/metaos1-base/validate.py` desktop->package map) resolves.
- `mousepad.desktop` / `ristretto.desktop`: authored from KEEP
  (`os-build/metaos1-base/packages.txt`) + Hana MIME map. No source .desktop
  exists in repo — these are net-new, package-named.
- `atril.desktop` (active) vs `evince.desktop` (NoDisplay=true, degraded-off):
  The base ISO ships atril where KEEP lists evince. OC2 does NOT edit
  Hana's `os-build/metaos1-base/packages.txt` or `os-build/metaos1-base/defaults/mimeapps.list`. This pack ships both and
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

## Why evince is hidden, and where that note now lives

The lane note used to sit inside `evince.desktop` as a comment. The entries
checker bans lane vocabulary in the entry files (a menu may read them, and
`Hana`/`KEEP` are not user-visible words), so the note moved here:

- `evince.desktop` is DEGRADED-OFF: KEEP lists evince, the base ships atril,
  so the entry is `NoDisplay=true` until the desktop owner acks it. Do not map
  MIME types to it from this lane. `Comment=` stays a plain description.
