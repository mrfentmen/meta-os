# OC3B-201 — launcher inventory: every app needing a launcher

Branch: `opencode/agent3-oc3`. Status of each row is VERIFIED (file read
on main @c38c6187 or landwalls tip) or CODE-INSPECTED (reasoned from
package manifests, needs OC1 boot check). Nothing here invents an app.

## A. Owned by other lanes — reference only, never rewrite here

| App | Entry (canonical path) | Owner | Note |
|---|---|---|---|
| Mousepad | `agent-layer/desktop-entries/mousepad.desktop` @landwalls | OC2 drop-in pack | TryExec present |
| Ristretto | `agent-layer/desktop-entries/ristretto.desktop` @landwalls | OC2 | TryExec present |
| Atril | `agent-layer/desktop-entries/atril.desktop` @landwalls | OC2 | TryExec present |
| Evince | `agent-layer/desktop-entries/evince.desktop` @landwalls | OC2 | dupes Atril's role; OC2's call, recorded not judged |
| Files (Thunar) | `agent-layer/desktop-entries/thunar.desktop` @landwalls | OC2 | TryExec present |
| Agent Status | `agent-layer/desktop-entries/meta-agent-status.desktop` @landwalls | OC2 | NO TryExec, Terminal=true — as-shipped by OC2, validator-green per their lane |
| Terminal | `iso/apps/desktop/meta-terminal.desktop` @main | ISO lane | Exec=xfce4-terminal, no TryExec |
| Web (Chromium) | `iso/apps/desktop/meta-browser.desktop` @main | ISO lane | Exec=chromium --no-first-run, no TryExec |
| Files (meta) | `iso/apps/desktop/meta-files.desktop` @main | ISO lane | dupes Thunar entry — ownership question for Pax, see §C |
| Settings | `iso/apps/desktop/meta-settings.desktop` @main | ISO lane | — |
| Welcome | `metaos-theme/apps/metaos-welcome.desktop` + `os-build/iso/payload-theme/apps/metaos-welcome.desktop` @main | Theme lane | identical twins — ownership question, see §C |
| Welcome backend | `metaos-welcome.py` + `test_welcome.py` alongside | Theme lane | — |
| Imperium | `os-build/iso/payload-theme/apps/metaos-imperium.desktop` @main | Theme lane | MERGE-EXCLUDED per 27fdb760 (provision.sh still installs both files — OC1 owns the fix, not OC3) |
| Ribbon wallpaper | `metaos-theme/wallpapers/live/metaos-livebg.desktop` + payload-theme twin @main | OC1 live-wallpaper pack | — |
| First login | `iso/base/autostart/meta-first-login.desktop` @main | ISO lane | autostart, not menu |

## B. OC3 scope — entries this lane authors (OC3B-202)

No .desktop on main covers these; all get TryExec guards; anything
unverifiable on-image ships `NoDisplay=true` with the reason stated
(the doc's own degraded pattern — honest, not mock):

| App | Exec target (expected) | Basis |
|---|---|---|
| Media player (Parole) | `parole %U` | Xubuntu default player; NOT in any package list — TryExec-guarded, boot check owned by OC1 |
| Volume control | `pavucontrol` | pairs with Parole; same guard |
| Archive handling | `xarchiver` / file-roller via Thunar | Xfce default; guard, no standalone entry unless missing |
| Calculator | `galculator` | Xubuntu default; guard |
| Task manager | `xfce4-taskmanager` | Xfce default; guard |
| Settings subpanels | `xfce4-settings-manager`, `xfce4-display-settings`, `xfce4-appearance-settings` | one launcher each or a manager root — validated statically, opens-on-boot owned by OC1 |
| Screenshots | `xfce4-screenshooter` | Xfce default; guard |

NOT authored: office suite (no LibreOffice/AbiWord anywhere in package
lists or base manifest — recording honestly absent would be a mock
claim either way; filed as OC3B-221 defect "office suite: no source
package named in any lane" with owner = whoever names the suite).

## C. Ownership questions for Pax (merge-time, not mine to resolve)

1. `meta-agent-status.desktop` exists in TWO places (OC2 pack +
   `iso/apps/desktop/`). One must win. OC2's is the maintained one.
2. `metaos-welcome.desktop` exists in TWO places (theme + payload-theme
   twins, byte-identical content). Same question.
3. `metaos-livebg.desktop` twins (theme + payload-theme). Same question.
4. `meta-files.desktop` vs Thunar entry — same app, two launchers.
5. `metaos-imperium.*` merge-excluded per 27fdb760: provision.sh still
   installs both files, so the ISO expects files the merge withheld.
   Owner per that commit message: OC1 (restore files or drop the two
   install lines). OC3 cannot fix from here — no shared-file edits.

## D. §1 cross-check (Chromium, feeds §9)

- `os/os/packages.txt` FROZEN set + `os-build/metaos1-base/packages.txt`
  KEEP list both name chromium/mousepad/ristretto/evince as shipped.
  No version pins exist anywhere (by design per the manifest header —
  versions come from a build-host dpkg diff, not from here).
- Start-page/homepage/first-run work is §1 (OC3B-001..025), not this
  file. No Ubuntu/Apple asset audit belongs here; that is §1's
  OC3B-006/013 with the Milo original-asset self-check.
