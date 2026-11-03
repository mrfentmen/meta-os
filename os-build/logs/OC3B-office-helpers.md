# OC3B-143/144/145/147 — clipboard, charmap, disk helpers (absent, listed)

- Clipboard manager + clipboard-persists-across-close: no clipman or
  equivalent in any package list, payload tree, or lane. ABSENT.
  Xfce's built-in clipboard covers copy/paste inside one session;
  persistence across close is not provided and not pretended.
- Character map / emoji picker: none named anywhere. ABSENT.
- Disk-usage helpers: no baobab/filelight anywhere. Present instead:
  `du` from coreutils on every image (standard tool, no lane owns
  it, no launcher needed). GUI gap recorded, CLI fallback named.
- All three: owner ISO lane if wanted, OC1 confirms. No mock
  launchers authored for missing programs — that rule holds.
