# OC2B tray .desktop handoff (OC2B-241 / 242 / 243)

From: OC2 (agent-layer lane). To: desktop lane (Bond) via OC1 / Pax.

## Ownership (OC2B-241)

- Bond owns the canonical tray entry:
  `iso/apps/desktop/meta-agent-status.desktop`
  (`Exec=meta-agent-status`, `Terminal=true`).
- OC2's copy `agent-layer/desktop-entries/meta-agent-status.desktop` is a
  BYTE-COPY (validator-enforced). OC2 never diverges from Bond's file.
- OC2's autostart entry `OC2B-autostart-tray.desktop` is autostart-only
  (NoDisplay=true, TryExec=meta-agent-status) and references — not
  replaces — Bond's entry.

## Handoff-accepted path (OC2B-242)

Accepted IFF Bond acks in writing (sha of accepted file + install target
`/usr/share/applications/meta-agent-status.desktop` confirmed). On ack:
OC2 records the acceptance note and ships nothing further for the tray
application entry. Autostart enablement follows the autostart handoff
(`~/.config/autostart/` per-user).

## Ship-ourselves path (OC2B-243)

If the desktop lane is unreachable (no ack within the agreed window): OC2
ships the tray entries itself, documented — byte-copy + autostart entry +
this note, shas recorded. No fork, no edits to Bond's file.

## OPEN for OC1 (not a unilateral OC2 call)

Which path: HANDOFF-ACCEPTED-IF-BOND-ACKS or SHIP-OURSELVES? Default until
answered: assume Bond owns the tray; OC2 holds byte-copy + autostart entry
ready and degraded-off so either outcome boots cleanly. OC1 rules: (a) ack
deadline, (b) per-user vs system autostart target, (c) who records the
acceptance sha.
