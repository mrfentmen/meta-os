# OC3B-059/060 — terminal launcher (no new file; mirror check)

No new entry authored: ISO lane `meta-terminal.desktop`
(Exec=xfce4-terminal, Terminal=false) already covers it, and a dup
would be clutter. Mirror notes for that file's owner:
- Has Terminal=false (good). Has NO TryExec line — suggest adding
  `TryExec=xfce4-terminal` at merge; not edited here (their file).
- OC3B-060 opens-in-home: Exec carries no directory and xfce4-terminal
  defaults to $HOME. CODE-INSPECTED; observed-confirm is OC1's line.
