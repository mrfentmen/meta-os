# MetaOS theme apps — what each one is

Install: `os-build/iso/payload-theme/apply.sh` copies `*.desktop` to
`/usr/share/applications/` and the two `.py` programs to
`/usr/share/metaos/apps/`. Twelve dock launchers are required by the
apply gate (`ndock == 12`); do not add or remove one without updating it.

## Dock launchers (`dock/`)

- `meta-dock-agents.desktop` — opens the Agents page in the kiosk browser.
- `meta-dock-board.desktop` — opens the Board page in the kiosk browser.
- `meta-dock-calculator.desktop` — opens the mate-calc calculator.
- `meta-dock-calendar.desktop` — opens the Calendar page in the kiosk browser.
- `meta-dock-custos.desktop` — opens the Custos page in the kiosk browser.
- `meta-dock-dashboard.desktop` — opens the Dashboard page in the kiosk browser.
- `meta-dock-editor.desktop` — opens the mousepad text editor.
- `meta-dock-musica.desktop` — opens the Musica page in the kiosk browser.
- `meta-dock-notes.desktop` — opens the Notes page in the kiosk browser.
- `meta-dock-officina.desktop` — opens the Officina page in the kiosk browser.
- `meta-dock-science.desktop` — opens the Science Lab page in the kiosk browser.
- `meta-dock-trash.desktop` — opens the Trash folder in the file manager.

Browser-backed tiles use `epiphany-browser` (kiosk browser, WebKitGTK;
confirmed in the image: guest session log shows an epiphany window,
`os-build/face/SESSION.md`). Native tiles use installed binaries
(`mate-calc` 1.26.0, `mousepad`, `thunar` — see `os-build/face/APP_MATRIX.md`).

## Session programs (top level)

- `metaos-welcome.py` (+ `.desktop`, autostart) — first-run welcome window.
- `metaos-imperium.py` (+ `.desktop`) — Trio/Imperium dispatch console.

No marketing: these are launcher records, not advertisements.
