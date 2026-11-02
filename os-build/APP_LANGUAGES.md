# APP LANGUAGES — what each of our apps is written in
# (Pax map from the 7-layer doctrine, boss question 02:33 EST)

The stack is 3 languages. Apps split by layer, not by taste:

- **Lobster — the apps themselves (L6).** Terminal's shell,
  Dashboard, Settings, Board, Files, Notes, Calendar,
  Calculator, Trash, and the system views (Imperium, Science
  Lab, Musica, Custos, Officina). If the user touches it, it's
  Lobster. Hana's lane.
- **Goose — the services behind the apps (L4).** Session,
  settings store, wallpaper, dock state, dashboard feed,
  updater client, board client, notify. The apps ask; the
  services answer. Buffy's lane.
- **Rust — everything that touches the machine (L1–L3).** The
  kernel, drivers, and the plumbing the apps stand on: the
  framebuffer, the window/compositor drawing, the console the
  Terminal window hosts, keyboard/mouse. Rowan's lane.

Worked example — Terminal: the shell you type into is Lobster
(L6); the console plumbing and the window it sits in are Rust;
the status facts it prints come from a Goose service reading
the machine.

Carrier rule unchanged: packed packages (Chrome, the distro's
own terminal/files) are installed as-is and are NOT rewritten.
This map governs our apps — the kernel face's windows and the
systems — only.

Agents stay Lobster (L5, Milo's design lane) on top of Goose
services, per the layer doctrine.
