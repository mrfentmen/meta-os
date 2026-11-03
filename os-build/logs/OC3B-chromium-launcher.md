# OC3B-008/009 — Chromium launcher with --app

File: `oc3b-desktop/meta-browser-app.desktop` (this lane, committed).
Existing `iso/apps/desktop/meta-browser.desktop` (ISO lane) is the
plain-window entry and is NOT edited here.

- Exec runs `chromium --no-first-run
  --app=file:///usr/share/metaos/start/index.html %U`.
- TryExec=chromium: no binary, no entry (self-hiding, not an error box).
- OC3B-009: Terminal=false present (line-audited, see test output).
- Icon=chromium (upstream package icon; resolves at OC1 boot check).
- MimeType kept from the ISO-lane entry so links open here.
- Diff vs ISO-lane entry: +`--app=` start page, +TryExec, +OnlyShowIn.
  If Pax prefers one entry, drop this file and fold `--app` + TryExec
  into the ISO-lane file — flagged here, not merged silently.
