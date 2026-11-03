# OC2B autostart handoff to ISO lane (OC2B-047 / 048 / 049)

From: OC2 (agent-layer lane, branch opencode2/landwalls). No VM, no writes.
To: OC1 / ISO lane (Pax merges).

## Fileset (OC2B-047 — exact autostart fileset for the ISO provision step)

1. `OC2B-autostart-queue.desktop` — XDG autostart for the queue service.
   Source Exec: `agent-layer/units/oc2-queue.service` ExecStart.
2. `OC2B-autostart-patrol.desktop` — XDG autostart for the patrol daemon.
   Source Exec: `agent-layer/units/oc2-patrol.service` ExecStart.
3. `OC2B-autostart-tray.desktop` — XDG autostart for the agent status tray.
   Source Exec: Bond `iso/apps/desktop/meta-agent-status.desktop`
   (`Exec=meta-agent-status`, `Terminal=true` preserved).

## Install targets (OC2B-048)

- Per-user (preferred): `~/.config/autostart/<name>.desktop`.
- System-wide (alternative): `/etc/xdg/autostart/<name>.desktop`.
- Recommendation: per-user `~/.config/autostart/`, matching the
  `meta-first-login.desktop` pattern (`iso/base/autostart/`,
  TryExec + NoDisplay=true + `X-GNOME-Autostart-enabled=true`).
- Verify: `ls ~/.config/autostart/OC2B-*.desktop` (or `/etc/xdg/...`)
  + `desktop-file-validate` if available. All three degrade-off.

## Dependency note (OC2B-049 — owned by another lane, recorded)

- Tray binary + canonical `.desktop` owned by DESKTOP lane (Bond):
  canonical `iso/apps/desktop/meta-agent-status.desktop`; OC2 copy
  `agent-layer/desktop-entries/meta-agent-status.desktop` (byte-copy,
  validator-enforced). OC2 does NOT duplicate-install the tray app entry —
  this handoff is autostart-only. See `OC2B-tray-handoff.md` for the
  accept/ship decision (OPEN for OC1).
- Queue/patrol scripts land via the §1 install manifest (OC2B-003); the
  autostart entries assume them (see TryExec caveats in
  `OC2B-tryexec-check.txt`).
- Style precedent: `agent-layer/desktop-entries/README.md` +
  `agent-layer/desktop-entries/INSTALL-OC1.md` (copy by sha, never push).
