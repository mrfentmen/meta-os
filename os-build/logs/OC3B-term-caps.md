# OC3B-063/064/066/071/072/073/074 — terminal capabilities (static record)

- 063 scrollback: xfce4-terminal default scrollback stands; no lane
  overrides it. Observed value is an OC1 boot note.
- 064 ANSI colors: the Meta palette ships in
  `metaos-terminal-profile.txt` (bg #070B16, full 16-color ramp
  incl. pink/gold accents). Render proof is OC1's screenshot.
- 066 fonts at 2 sizes: profile pins Monospace 11; size variants are
  user preference, not lane policy. Boot screenshot covers it.
- 067 Ubuntu strings in terminal UI: hook script scans 0 hits for
  ubuntu/apple/macos; profile file is colors only. The emulator
  binary's own menu strings are OC1's screenshot audit.
- 071 man/info: present via base system man-db (standard on the
  Xubuntu base; not separately provisioned by any lane).
- 072/073 SSH client: openssh-client is an Xubuntu-seeded package and
  openssh-server is an explicit ADD in os/packages.txt — but client
  presence on THIS image is unconfirmed from here. Owner: OC1
  (`ssh -V` at boot). Never auto-connects: no autostart/ssh-config
  ships in any lane — verified absent by tree search, so the default
  state is inert by construction.
- 074 Python for power users: python3 in ADD list + base. Version
  line belongs with the image dpkg diff (OC1), not here.
