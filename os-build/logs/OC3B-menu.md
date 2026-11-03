# OC3B-215/216/217 — menu structure (Xfce, category-driven)

Xfce builds the menu from Categories fields, so structure follows from
the committed entries (OC2 six + ISO-lane four + this lane's eight):

- System: Files, Task Manager, Agent Status, Terminal, Settings Manager
- Network: Web
- AudioVideo: Media Player, Volume Control
- Utility: Calculator, Screenshot, Mousepad, Files(also), Task Manager(also)
- Graphics: Ristretto
- Office: Atril, Evince
- Settings: Settings Manager, Display, Appearance

OC3B-216/217 (every item opens something; no dead entries): STATIC
portion done — every item above names a TryExec-guarded Exec whose
binary is an Xfce/Xubuntu default. The opens-on-click half is an OC1
boot check per item, explicitly deferred, not claimed.
