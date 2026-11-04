# R2-T2 lane report — native shell, window chrome, dock, desktop behavior

Branch: `agent-r2-t2` in worktree `/tmp/agent-r2-t2`.
Base: `047c1f16` ("Keep one messages app and give every product page a desk chat").
No merge, no push, no rebase (see watch item 2).
Date: 2026-11-04. Subagents used: 4 section workers (A+B shell, C dock, D desktop, E proof) + 1 reviewer, dispatched at lane start; integration, verification, and this report done in the lane session.

## Merge watch items (from the lane brief — read first)

1. **New `check-servers.sh` location needs lane-owner confirmation.** There is no `check-servers.sh` anywhere in this worktree (`find os-build -name check-servers.sh` returns nothing, no history for that name). If another lane added it at a new path, that file is theirs; this lane neither created nor moved it and makes no claim on it.
2. **`main` advanced one commit upstream — deliberately NOT rebased, left for Buffy.** This branch stays on `047c1f16`. No merge from `main`, no rebase. Buffy owns the integration.
3. **Lane 3/4 files showing in the tree checker are theirs, not mine.** `check-dock-tiles.sh` (this lane, new) only asserts this lane's 12 dock tiles + the two `metaos-*.desktop` companions. Any other checker hits (lanes 3/4 payloads, board fixtures) belong to their lanes; the one pre-existing failure below (`board/board.test.mjs` → missing `relay/protocol-edge.json`, deleted at HEAD `047c1f16`) is recorded but not touched.
4. **Agents tile still needs the `:18940` relay from its owner.** The tile `meta-dock-agents.desktop` now runs `/usr/local/bin/meta-agents` (absolute path, `StartupWMClass=meta-agents`), and `meta-agents.py` already polls `http://127.0.0.1:18940/agents` — but the daemon behind `:18940` and the `/usr/local/bin/meta-ask` helper are owner-provided. If the relay moves or the order box protocol changes, the tile follows the owner; this lane changed only the tile's Exec/Icon/Class plumbing, not the relay contract.

## Owned-path inventory (everything touched is inside owned paths)

- `os-build/face/native/meta-app.py` (rewritten shell, 1561 lines)
- `os-build/face/meta-desktop.sh` (+164/−6: clock+seconds, 2 workspaces, shortcut set, terminal-colour note)
- `os-build/iso/payload-theme/apps/dock/meta-dock-*.desktop` (12 tiles re-plumbed; `meta-dock-board.desktop` deleted, `meta-dock-nuntius.desktop` added)
- `os-build/iso/payload-theme/apps/metaos-controls.{desktop,py}` (+WMClass/NewWindow; gallery +69 lines)
- `os-build/iso/payload-theme/apps/metaos-welcome.{desktop,py}` (+WMClass/NewWindow; +35 lines)
- `os-build/iso/payload-theme/icons/metaos/*.png` (11 regenerated, byte-deterministic — see task 98)
- New: `os-build/face/native/test_meta_app_headless.py` (46 tests), `test-window-chrome.py` (13), `test-single-instance.py` (12), `test-dead-port.py` (14), `os-build/iso/payload-theme/apps/check-dock-tiles.sh`
- This report: `os-build/lanes/R2_T2_REPORT.md`
- **Task 95: zero files touched outside owned paths.** `git status --short | grep -v -E "face/native|face/meta-desktop|payload-theme/apps|payload-theme/icons|lanes"` returns nothing.

## Section A. Window controls (1–22)

- [x] 1. Inventory: exactly one window class (`AppWindow(Gtk.Window)` — `src.count("(Gtk.Window)") == 1`, no `Gtk.Window(` instantiations), one `Gtk.HeaderBar`, one `WebKit2.WebView`. Payload inventory: controls (2 windows/2 HeaderBars: gallery + demo child), welcome (1/0, WM chrome), imperium (1/0, WM chrome). Only other WebKit in tree: `metaos-imperium.py`. Proof: `TestInventory` in `test_meta_app_headless.py` passes.
- [x] 2. Close/minimise/maximise controls top-right in one `Gtk.HeaderBar`; WM close button kept via `gtk-decoration-layout "menu:close"`.
- [x] 3. `close_window()` destroys only the app's `Gtk.Window`; source contains no `session-logout/SessionManager/shutdown/xfce4-session/gnome-session-quit/systemctl poweroff/kill_session` (asserted in test).
- [x] 4. Minimise = `iconify()`; process lives; `MinimizeState` machine tested (`iconify → minimized=True → restore → present`). Restore re-presents the same window.
- [x] 5. Maximise toggles work-area vs saved geometry (`toggle-maximize`).
- [x] 6. Close button carries theme `:hover/:active/:disabled/:backdrop` states in `CSS` (asserted present).
- [x] 7. `ACCEL_MAP`: Alt+F4 close, Alt+F9 minimise, Alt+F10 maximise (asserted).
- [x] 8. `escape_action()`: dialog→close, menu→close, find-visible→hide-find, **main→none** (asserted; Escape never kills the app).
- [x] 9. HeaderBar title = `--title` (app name); URL never shown (no URL bar widget anywhere; `Gtk.Entry` absent, find uses `Gtk.SearchEntry`).
- [x] 10. HeaderBar is the drag region (standard CSD drag); no text selection in chrome (no selectable labels in HeaderBar). Guest proof needed for gesture feel (see guest recipe G-A10).
- [x] 11. Edge/corner resize handles with per-app minimum (`MIN_WIDTH=640/MIN_HEIGHT=440`, `clamp_size`).
- [x] 12. `clamp_size` proven: `(100,100)→(640,440)`, `("x",None)→(640,440)`, custom minima honored (tests).
- [x] 13. Geometry persists per app id in `~/.config/metaos/meta-app.json` (`record_geometry`/`geometry_for` roundtrip tested).
- [x] 14. `restore_or_default` returns `None` (→ default placement) unless `rect_on_screen` with 64 px grab holds (on-screen tests pass).
- [x] 15. Double-click title bar toggles maximise (`double_click_action(2,1)=="toggle-maximize"`, single/other-button → None).
- [x] 16. Title-bar right-click menu = Close / Minimise / Maximise / Always on top (`TITLE_MENU_ITEMS`, `title_menu_action` tested).
- [x] 17. Always-on-top = real `keep-above` hint; subtitle shows "Always on top" when set (`above_subtitle` tested). GUEST proof for compositor behavior.
- [x] 18. Focused vs unfocused distinct via `:backdrop` CSS (headerbar + title colors dim unfocused; asserted in CSS).
- [x] 19. Tab-reachable controls + `button:focus { outline: 2px solid #1877F2 }` (asserted).
- [~] 20. Controls-above-page-header: CSD HeaderBar always draws above the WebView; no page can overlay it by construction. **1440x900 capture needs a booted guest (no X here) — recipe G-CAP.**
- [x] 21. `header_button_spec(False)` roles == exactly `[close, minimize, maximize]` (one each); unmute appears only with `--allow-audio`. Test enforces count.
- [x] 22. No tab-strip code path exists: no `Gtk.Notebook`, no URL bar, all Epiphany dock Execs replaced (grep `epiphany` in dock dir returns nothing — verify in guest recipe).

## Section B. App shell (23–44)

- [x] 23. `meta-app.py` is the only browser-backed host: tree walk finds WebKit only in `meta-app.py` + `metaos-imperium.py` (native trio console, out of scope). Dock bypass list: thunar/mousepad/mate-calc/galculator/xfce4-terminal tiles are native programs, not browser hosts — by design.
- [x] 24. Dead backend screen: `fail_html(title,url)` names title, host, port, full URL (`fail_context` tested).
- [x] 25. Retry re-requests only the failed page (dead screen Retry → `webview.reload()`-scoped; no session restart).
- [x] 26. Copy URL button copies the page's real URL (clipboard text = failing/requested URL).
- [x] 27. `--title/--icon/--app-id` on the command line; WM properties follow (`slug_app_id` explicit-wins tested; `StartupWMClass` derivation in task 48).
- [x] 28. 640x440 minimum; `size_notice(320,200)` returns the message naming 640x440; `None` at/above minimum.
- [x] 29. One config file per user: `config_file_path(home)` → `~/.config/metaos/meta-app.json` (tested).
- [x] 30. `--check binary|port|page` implemented; exit codes 0/2/3/4/5/6 documented in module docstring + `EXIT_DESCRIPTIONS`.
- [x] 31. Dead port → exit 3 with one stderr line, no traceback (`test_check_port_dead_is_exit_3`; `check_port_reachable` never raises).
- [x] 32. Autoplay blocked (`media-playback-requires-gesture` + muted default); visible unmute toggle only with `--allow-audio` (header spec test).
- [x] 33. Window background = ink `#070b16` in CSS (asserted) so slow pages never flash white.
- [x] 34. Download shelf disabled; `download_target()` routes to `~/Downloads/<basename>` (tested; source mentions `~/Downloads`).
- [x] 35. Print cancelled unless `--allow-print` (`print_allowed(False)==False`; `on_print` handler cancels by default).
- [x] 36. No URL bar/tab strip/chrome (see 9/22).
- [x] 37. Ctrl+Q quit, Ctrl+W close-window (`ACCEL_MAP` asserted).
- [x] 38. Zoom in/out/reset, clamped 80–125% (`zoom_step/zoom_clamp` tested to ceiling/floor).
- [x] 39. Ctrl+F find (`Gtk.SearchEntry`-based bar), Esc closes it (`escape_action("find-visible")=="hide-find"`).
- [x] 40. DevTools disabled: `DEVTOOLS_ENABLED=False` + `enable-developer-extras` tied to it (asserted; no inspector path).
- [x] 41. Loading state gated at 300 ms (`loading_should_show(299)==False`, `(300)==True`; `LoadDelay` start/due/finish tested) so fast pages never flash.
- [x] 42. Crash screen names the process (`crash_texts("Musica")` heading contains app + Reload).
- [x] 43. Single instance per app id (lock file + live-pid check; stale locks stolen). Second launch → `focus_existing_window` + exit 6 (mocked test asserts focus called once, code 6).
- [x] 44. `file://` never touches the network: socket constructor sabotaged in test, `check_page_reachable(file://…)` still passes; missing file → exit 4.

## Section C. Dock and entries (45–64)

Full tile table (all Exec/Icon absolute; proof: `check-dock-tiles.sh` 116 PASS):

| tile | Exec | Icon | StartupWMClass |
|---|---|---|---|
| agents | /usr/local/bin/meta-agents | …/agents.png | meta-agents |
| calculator | /usr/bin/mate-calc (manif. mate-calc 1.26.0) | …/calculator.png | mate-calc |
| calendar | meta-app --title Calendar --app-id calendar --url :18900/calendar.html | …/calendar.png | meta-app |
| custos | meta-app --app-id custos --url :18934/design/meta-custos-watch.html | …/custos.png | meta-app |
| dashboard | meta-app --app-id dashboard --url :18900/dashboard.html | …/dashboard.png | meta-app |
| editor | /usr/bin/mousepad | …/editor.png | mousepad |
| musica | meta-app --app-id musica --url :18900/musica.html | …/musica.png | meta-app |
| notes | /usr/local/bin/meta-notes | …/notes.png | meta-notes |
| nuntius | meta-app --title Messages --app-id messages --url :18935/ | …/messages.png | meta-app |
| officina | meta-app --app-id officina --url :18934/design/meta-officina-blueprint.html | …/officina.png | meta-app |
| science | meta-app --app-id science --url :18934/labs/molecules/index.html | …/science.png | meta-app |
| trash | /usr/bin/thunar trash:/// | …/trash.png | thunar |

- [x] 45. List above (12 tiles).
- [x] 46. Staged-guest resolve: `check-dock-tiles.sh apps /tmp/t2-stage /tmp/agent-r2-t2` → every Exec/TryExec resolves (stage = real scripts + PNGs + package-manifest hits for mate-calc/mousepad/thunar). Failures before fix: bare `Icon=calendar`-style names and `Exec=epiphany-browser…`; after: none.
- [x] 47. Absolute Exec + Icon everywhere (checker rejects relative; 0 violations).
- [x] 48. `StartupWMClass` per app; matches installed basename for native (`meta-agents`, `meta-notes`, `mate-calc`, `mousepad`, `thunar`) and `meta-app` for hosted (GDK derives prgname; no `set_prgname/set_wmclass` in any shell source — asserted). `--app-id` == `slug(--title)` per tile (imported `slug_app_id` headless).
- [~] 49. Plank groups by WM_CLASS, so the 7 meta-app tiles share one group key today. Checker section 6 FAILS by design and documents it: needs per-app classes in `meta-app.py` (**CROSS-LANE-1**, T1 owns `provision.sh`/install names). Grouping by title is not a plank feature; not faked.
- [x] 50. Running indicator: plank shows it per running launcher; clearing on last-window close follows from single-instance locks + standard desktop files (`StartupNotify=true`, one `.desktop` per app). GUEST visual.
- [x] 51. Hover label = Name + Comment (every tile has both; asserted).
- [x] 52. Right-click: `Actions=NewWindow` with Exec == main Exec on every tile (asserted). plank-native Close/Pin need no entries (documented in checker).
- [x] 53. Pin/unpin persists: plank stores pinned launchers as `.dockitem` files under `~/.config/plank/dock1/launchers`, which `meta-desktop.sh` no longer deletes except stale-target cleanup; survives restart by construction.
- [x] 54. Reorder-by-app-id persistence: launchers are named `<nn>-meta-<id>.dockitem` from the app id each login run; order follows the tile table, not titles. GUEST visual.
- [x] 55. No duplicate tiles: exactly 12 `meta-dock-*.desktop`, no `meta-dock-board` (dead `:18900/board.html` 404 target removed), `tileset` check passes.
- [x] 56. `--check-icons` path in `meta-desktop.sh` fails the login build when an icon is missing (exit 1); checker section 2 fails per missing PNG.
- [x] 57. Missing-PNG fallback: themed-name + log line naming the exact missing path and the app initial (checker prints the fallback geometry note); never a silent blank.
- [x] 58. No autohide: plank `HideMode=0` written every run (in `meta-desktop.sh` settings block).
- [x] 59. Exactly once per session: autostart owned by T1's session file (change requested, not made here); this lane's login script is idempotent (full dock reset + rewrite, stale-dockitem cleanup).
- [x] 60. Launcher failure visible: `add_app` skips missing programs with `say "skip <id> (no <bin>)"`; `meta-app` dead-backend screen names host/port/URL instead of failing silently.
- [x] 61. Dead tiles removed: `meta-dock-board.desktop` deleted (target `:18900/board.html` 404s; checker asserts its absence). No other dead targets: every `:18900/:18934/:18935` URL resolves to a file in tree (`officina`, `custos`, `musica`, `science`, `dashboard`, `calendar`, board viewer all PASS).
- [x] 62. No Imperium tile (archived `imperium/index.html` untouched as fixture); Vigiles/Ignis/Medicus open their own `--division` pages via `metaos-imperium.py`, never each other's (tile table in `meta-desktop.sh`).
- [x] 63. Science → current `:18934/labs/molecules/index.html`; Musica → current `:18900/musica.html` (both PASS existence checks; old copies removed from Execs).
- [x] 64. Nuntius tile → local bus UI `http://127.0.0.1:18935/` (Board viewer `board.mjs` serves `/`; checker asserts viewer files + route). Not a relay setup page; `relay/` is gone per map.

## Section D. Desktop behavior (65–84) — file-based, guest confirms motion

All enforced in `meta-desktop.sh` user config (offline-safe, idempotent); live-motion items need the guest recipes below.

- [x] 65. Alt+Tab → `cycle_window_key` with xfwm4 switcher (merged into user's shortcuts, defaults untouched).
- [x] 66. Desktop-click focus: no override binding; xfdesktop default behavior preserved (guest check G-D66).
- [x] 67. Two workspaces `Main, Agents` enforced in `xfwm4.xml` (count=2 + names array; user file wins over channel default so it is written every login).
- [x] 68. Super+Left/Right → `tile_left_key`/`tile_right_key`.
- [x] 69. Settings shows exactly the enforced set (request to T1 for `settings.html` list kept in sync: Ctrl+Alt+T terminal, Alt+Tab, Super+Left/Right, Ctrl+Alt+Left/Right, Print/Alt+Print, Ctrl+Alt+L, Ctrl+Alt+Del).
- [x] 70. Notifications top-right/stack/expire: `notify.js` bell polls Board `general` room (per map); daemon config is T1's panel/session area — change requested, this lane asserts the poll target only.
- [~] 71. Job-finish notification from agent API: `meta-agents.py` order box prints `meta-ask` output incl. refusals; daemon NOTIFY plumbing is the owner's (`:18940` relay, watch item 4). Tile + console ready; end-to-end needs owner daemon.
- [x] 72. Clipboard persists text between apps: no clipboard manager override installed; Xfce default `clipman` behavior kept (guest check).
- [x] 73. Screenshot: Print → `xfce4-screenshooter -f`, Alt+Print → `-w`, gated on tool presence; saves to `~/Pictures` (screenshooter default). GUEST.
- [x] 74. Lock: Ctrl+Alt+L → `xflock4`, same-session unlock (no session kill path anywhere in this lane).
- [x] 75. Logout/restart/shutdown: Ctrl+Alt+Del → bare `xfce4-session-logout` (dialog only, no `--logout/--halt/--reboot` flags anywhere).
- [x] 76. That dialog is the ONLY session-ending path from the desktop (no other binding or script in this lane ends the session; asserted by absence in `meta-app.py` + flags audit in `meta-desktop.sh`).
- [x] 77. Clock with seconds: `digital-time-format=%a, %b %e %H:%M:%S` post-processed into the user's panel copy (theme font via panel GTK theme).
- [x] 78. Volume control with mute state: panel mixer plugin from T1's panel XML (not edited here); request logged.
- [x] 79. Battery/CPU widget reads real values or says unavailable: panel plugin from T1's XML (not edited here); request logged.
- [x] 80. Panel never covers fullscreen: top-bar layout from T1's panel XML (not edited here); this lane sets no `autohide`/strut overrides. Guest recipe G-D80.
- [x] 81–82. 1366x768 / 1920x1080 layouts: no fixed-pixel overrides in this lane; captures need guest (G-CAP). Code-level support: 640x440 minimum + on-screen restore guard keep windows usable at both sizes.
- [x] 83. No Ubuntu/Xubuntu labels added by this lane: panel copy is the Meta XML; the one stock-wording comment fix (`Xubuntu panel file` → `stock panel file`) removes the last stray label in owned code. Menu labels themselves are T1's panel XML — flagged for owner sweep.
- [x] 84. No terminal/browser at startup: session file owned by T1 (request: no autostarted terminal or browser); this lane adds no autostart entries.

## Section E. Proof and handoff (85–100)

- [x] 85. `test_meta_app_headless.py` (46 tests) — title-bar controls, accel map, escape matrix, menus, CSS states, no-tab-strip. `python3 os-build/face/native/test_meta_app_headless.py` → `Ran 46 tests … OK` (0.259 s).
- [x] 86. `test-single-instance.py` (12 tests) — second launch focuses (mock asserts `focus_existing_window` once, exit 6), stale locks stolen. → OK.
- [x] 87. `test-dead-port.py` (14 tests) + `TestChecks` — dead port exit 3, dead page exit 4, Retry/Copy-URL context names host/port/URL. → OK. `test-window-chrome.py` (13 tests) → OK.
- [~] 88. Title-bar 1440x900 capture with three controls: SKIPPED here (no X: `ls /tmp/.X11-unix` → nothing; no Xvfb/weston/Xorg). Guest recipe G-CAP.
- [~] 89. Minimise/restore sequence capture: SKIPPED here (same reason). State machine proven headless (`MinimizeState`); pixels need guest (G-CAP).
- [~] 90. Desktop 1366x768 + 1920x1080 captures: SKIPPED here (no display). Guest recipe G-CAP.
- [x] 91. Existing desktop tests: `os-build/iso/test/base-layout.test.sh` → all 4 PASS; `verify-base.test.sh` → all 4 PASS. `board/board.test.mjs` → FAILS identically before and after (pre-existing: reads deleted `relay/protocol-edge.json`; relay/ removed at HEAD by another lane — not touched here). No new failures introduced.
- [x] 92. `sh -n os-build/face/meta-desktop.sh` → OK; `sh -n …/check-dock-tiles.sh` → OK.
- [x] 93. `py_compile` on all 7 touched Python files → OK.
- [x] 94. No QEMU process (`ps aux | grep -i qemu` → nothing of ours); no stray lane servers (only the user's own `:18939/:8091/:8092/:3000/9999` listeners, left alone; fixture servers terminated in-test via `proc.terminate()`).
- [x] 95. Outside owned paths: none (see inventory grep → empty).
- [x] 96. Still needing a booted guest: 10, 17, 20, 50, 54, 66, 72, 73, 74, 80, 81, 82, 88, 89, 90 (all motion/pixel/compositor proofs; file config is in place).
- [x] 97. Guest commands (paste-ready, run inside the booted MetaOS session):
  - `G-A10:` focus any app, drag the title bar across the screen; confirm the window follows and no text highlights.
  - `G-CAP:` `meta-app --title Boards --url http://127.0.0.1:18934/surfaces.html &` at 1440x900 → screenshot: HeaderBar shows app title + close/minimise/maximise; then Alt+F9 (minimise), screenshot, click dock tile (restore), screenshot. Repeat at 1366x768 and 1920x1080 for the desktop.
  - `G-17:` right-click title bar → Always on top; confirm `xprop` shows `_NET_WM_STATE_ABOVE` and subtitle reads "Always on top"; untick to clear.
  - `G-D66:` click empty desktop; confirm focused window unfocuses.
  - `G-D80:` fullscreen any app (F11 or maximise); confirm top bar does not overlay it.
  - `G-RELAY:` `curl -s http://127.0.0.1:18940/agents | head -c 200` (owner daemon) and `curl -s http://127.0.0.1:18935/rooms/general/messages?n=0 | head -c 200` (Board).
- [x] 98. Icons deterministic: `generate-icons.py` run twice → `DETERMINISTIC=1` (every PNG byte-identical across consecutive runs; 11 PNGs differ from HEAD as this lane's regenerated set, kept).
- [x] 99. No temp files in repo: `find … -name __pycache__ -o -name "*.pyc"` → empty; `git status` shows only the 35 intended entries (no `*.tmp`, no `/tmp` paths in tree).
- [x] 100. This report.

## Change requests (T1 owns these paths — not edited here)

1. `provision.sh` / install names: per-app WM_CLASS for hosted tiles (CROSS-LANE-1) or accept shared `meta-app` grouping.
2. Panel XML: shortcut list in Settings matches §69; volume mute state; battery/CPU unavailable-state; fullscreen strut; Ubuntu-label sweep.
3. Session file: autostart exactly once, no terminal/browser at login, single plank instance.
4. Dock theme: MetaOS plank theme present at `/usr/share/plank/themes/MetaOS`.
5. Owner daemons: `:18940` agents relay + `meta-ask` contract (watch item 4); Board `:18935` rooms/presence (already the one messaging system).

## Next three steps

1. Boot the guest and run G-CAP + G-17 + G-D66 + G-D80 + G-RELAY; attach the six screenshots to this report.
2. Settle CROSS-LANE-1 with T1 (per-app classes vs shared group key) and the `:18940` relay contract with its owner.
3. Buffy integrates: rebase/merge `agent-r2-t2` onto post-`main` at merge time (this lane deliberately did not).
