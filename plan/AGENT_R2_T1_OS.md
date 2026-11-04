# Agent R2-T1 lane: offline type, identity, boot surface, image build

## Tree changes after this lane file (2026-11-04, Buffy) — read before starting

These are merged into `main` already. Nothing below is a task; it is the map.

- **One messaging system: `board/`.** `relay/` (Nuntius relay + viewer) and
  `os-build/face/board.py` / `board.html` are deleted. `board/board.mjs` runs on
  18935: `GET /rooms/<room>/messages?since=<n>`, `POST {nick,text}`,
  `POST /rooms/<room>/notify`. The dock's Messages tile opens it; the shell bell
  (`notify.js`) polls its `general` room. Do not add a second transport.
- **`index.html` (repo root) is deleted.** It was the app hub; the dock lists
  apps. The site root is `surfaces.html`, and `server/server.mjs` serves it for
  `/`. `bus.html` stays: it is the dashboard page the DSH tests cover.
- **`imperium/index.html` is archived**, not in the product: no dock tile, not
  copied into the image. The tests read it as a fixture — leave the file alone
  and do not wire a tile to it. The three divisions (`trio/vigiles.html`,
  `ignis.html`, `medicus.html`) are the product.
- **Both logo studio pages are deleted** (`logo-studio.html`,
  `design/meta-ascii-logo-studio.html`), and with them the
  `design/agent-budget-dashboard.html` mock. The spinning loop is
  `js/logo-background.js` / `os-build/face/logo-background.js`; the studio-only
  tests were removed with the pages.
- **Shared chat box: `js/site-chat.js`.** `<script src="js/site-chat.js"
  data-room="..." data-label="...">` gives a page the Board rooms (surfaces.html,
  labs/molecules, labs/music3d, labs/science-lab-review, Custos, Officina,
  face/musica.html). On surfaces.html the room follows `#board-<room>`.

Paste this whole file to the agent. Work on branch `agent-r2-t1` in worktree
`/tmp/agent-r2-t1`. Commit there. Do not merge. Do not push. Do not switch any
other worktree's branch.

## Mission

The OS boots, but it still looks like a themed Ubuntu to anyone who opens a
terminal, the greeter, GRUB, or the installer. Round 2 makes Meta's type and
identity physical in the image: real font files installed offline, one identity
writer, a boot surface with no Ubuntu words, and a build that proves all of it
without booting QEMU.

Buffy owns page typography (`font-family`, `@font-face`, `vendor/fonts/` in the
served pages). You own **installing fonts into the image** and the system
surfaces that consume them. Do not edit app HTML or its CSS.

## Owned paths (only these)

- `os-build/identity/`
- `os-build/iso/payload-theme/fonts/` (new) and any font install script you add
- `os-build/iso/payload-theme/plymouth/`, `grub/`, `lightdm/`, `panel/`,
  `dock/`, `xfwm4/`, `gtk/`, `wallpapers/`
- `os-build/iso/payload-theme/apply.sh`
- `os-build/iso/provision.sh`, `os-build/iso/provision-all.sh`
- `os-build/iso/plymouth/`, `os-build/iso/splash/`, `os-build/iso/grub-fix.sh`
- `os-build/calamares/`
- `os-build/metaos1-base/dexubuntu/`
- `os-build/lanes/R2_T1_REPORT.md` (yours to write)

Request anything else in the report. Never edit `trio/`, `design/`, `labs/`,
`aegis-page/`, `agents/`, `agent-layer/`, `server/`, or `os-build/face/*.html`.

## Rules

- **No QEMU.** Not once, not with a flag. No `METAOS_ALLOW_QEMU`.
- No `sudo`, no `mount`, no docker unless the report says you tried and why.
  Use staged roots, `debugfs` reads, and static traces.
- Call subagents. Use at least four, one per section, and one reviewer that
  hunts for unproven claims. Give each subagent its section and proof command.
- Every claim needs the command and its pasted output in the report.
- A skipped task gets a reason, not a silent checkmark.

## Section A. Fonts in the image (1-18)

1. Inventory every font family already installed by the Xubuntu base manifest; print the list.
2. Choose the six families the desktop needs (UI, document, mono, display, label) from modern neo-grotesque or geometric sans families plus a mono. No serifs, scripts, or decorative display faces; record why each.
3. Fetch only OFL/Apache-licensed files; record family, version, license, and source URL per file.
4. Vendor the `.woff2`/`.ttf` files under `os-build/iso/payload-theme/fonts/` with a `LICENSES/` directory.
5. Write `fonts/install.sh` that copies fonts to `/usr/share/fonts/truetype/meta/` and runs `fc-cache -f`.
6. Make the install idempotent: a second run changes zero bytes and prints zero copies.
7. Add a `--check` mode that fails when a declared font file is missing or zero-length.
8. Write a fontconfig file that aliases `sans-serif`, `serif`, and `monospace` to Meta's chosen families.
9. Prove with `fc-match` on a staged root that all three generic names resolve to Meta files, not Ubuntu or DejaVu.
10. Remove the Ubuntu font package from every install manifest that still pulls it.
11. Make the terminal profile use the chosen mono family by name; prove the profile file after the change.
12. Make the greeter's font config point at the chosen UI family; prove the drop-in.
13. Make the panel, window titles, and notifications use the same UI family; prove each config path.
14. Confirm no app page requests a remote font URL; grep the served tree and paste zero hits.
15. Add the font install step to `provision-all.sh` so a fresh image gets it without a manual command.
16. Add the font payload to `build_iso.sh --tree-only` output and prove the files are present.
17. Write a test that fails when an installed font family name contains `Ubuntu`.
18. Record the total added size and keep it under 3 MB.

## Section B. One identity writer (19-38)

19. Re-list every file that writes `/etc/os-release`; print paths and order of execution.
20. Make `debrand.sh` the only writer; gate or delete the second writer with a named reason.
21. Set `NAME`, `PRETTY_NAME`, `VERSION`, `VERSION_ID`, `ID`, `ID_LIKE`, `HOME_URL`, `SUPPORT_URL`, `BUG_REPORT_URL`, `DOCUMENTATION_URL` to Meta values.
22. Choose `ID_LIKE` deliberately and document which readers depend on it.
23. Set a Meta `VERSION_CODENAME`; grep every reader of that field first.
24. Handle the `/etc/os-release -> ../usr/lib/os-release` symlink without replacing it with a regular file.
25. Apply the same identity to `/etc/lsb-release`, `/etc/issue`, `/etc/issue.net`, and `/etc/motd`.
26. Make `/etc/hostname` and `/etc/hosts` say `metaos`; prove both after a staged apply.
27. Rename the default user to `meta` everywhere it is created, including the installer and skel.
28. Set the GECOS field so `getent passwd` and the greeter stop saying Ubuntu.
29. Remove the stock `ubuntu` user if the installer still creates it; prove its absence in the staged passwd.
30. Update the desktop-entry `Comment=` values that still name Xubuntu.
31. Make `check_strings.sh` exit 0 on the tree; allowlist only compat strings with a per-row reason.
32. Add a test that fails if two scripts write `os-release`.
33. Add the same guard for `hostname`, `lsb-release`, and `issue`.
34. Fix the `meta-branding.sh` last-writer-wins path and prove which file wins on install media.
35. Update the Calamares branding text, window title, and product name; paste the changed keys.
36. Make the installer's summary page say Meta OS and the disk label `METAOS`.
37. Re-run `debrand.sh --apply` twice on a staged root; prove the second pass changes zero bytes.
38. Paste `debrand.sh --check` PASS output for the whole tree.

## Section C. Boot surface (39-56)

39. Render the plymouth theme at 1920x1080 and 1366x768; paste both file sizes and the darkest pixel.
40. Prove the shipped splash loads no `ubuntu-logo` file; grep the theme.
41. Set the splash background to the theme ink value; paste the hex.
42. Make the splash text read `Meta OS` and a Meta progress word.
43. Keep the splash under 40 decode frames; count them from the payload.
44. Prove the password prompt in the greeter uses Meta colours; paste the colour keys.
45. Make the text-plugin fallback print `Meta OS` on a console boot.
46. Prove the theme survives an initramfs rebuild; show the rebuilt config.
47. Confirm the splash is not shown twice on shutdown; trace the shutdown unit.
48. Dump every GRUB menu entry from the built tree; paste it.
49. Make every entry title Meta-branded, including recovery and advanced submenus.
50. Set the GRUB distributor string and palette; paste the generated `grub.cfg` lines.
51. Make `grub-fix.sh` idempotent; run it twice and diff.
52. Add a check that fails when `Ubuntu` appears in generated `grub.cfg`.
53. Make the greeter session name read `Meta OS` and keep autologin working.
54. Prove the session file lightdm loads is the Meta session, by absolute path.
55. Remove the guest session and any stock fallback session; make a missing Meta session fail loudly.
56. Set the greeter clock format and machine name to match the desktop.

## Section D. Desktop theme (57-76)

57. Make the panel height, padding, and font match the approved desktop reference; paste the before/after values.
58. Make the dock use the Meta icon theme and the approved indicator for running apps.
59. Prove every dock `.desktop` points at an icon file that exists in the payload.
60. Set the window border theme, title font, and button order to the approved layout.
61. Prove close/minimise/maximise buttons exist in the xfwm4 theme and are not the stock Ubuntu order.
62. Remove the green and white stock wallpaper from every theme path; grep the payload.
63. Set the default wallpaper to the Meta live wallpaper and prove the xfconf default.
64. Set the icon theme so no stock Xubuntu icon appears in the dock; list the mappings.
65. Install the Meta cursor theme and prove the default cursor setting.
66. Set the notification theme and font; prove the config path.
67. Set display scaling for 1920x1080 and 1366x768; record both.
68. Set the power profile so the demo VM does not spin fans at idle; prove the config.
69. Make the desktop start exactly one dock and one panel; prove the autostart list.
70. Remove the Ubuntu welcome dialog and any first-run Ubuntu prompt.
71. Make the terminal prompt say `metaos` in blue; prove the profile and shell rc.
72. Make the About/System panel read Meta values from `os-release`; prove the field list.
73. Remove stock Xubuntu wallpapers from the payload; list every removed file.
74. Set the login background to the Meta wallpaper; prove the lightdm greeter config.
75. Make the lock screen use the Meta wallpaper and UI font.
76. Record the theme's colour tokens in one file and prove the GTK, xfwm4, and panel configs read those values.

## Section E. Build and image (77-90)

77. Run `build_iso.sh --tree-only`; paste file count, size, and broken-symlink count.
78. Prove the tree has no baked host paths; grep for `/Users/`.
79. Make `provision-all.sh` run the font, identity, splash, GRUB, greeter, theme, and dock steps in order.
80. Make `provision-all.sh` fail on the first missing payload file, naming it.
81. Prove a staged fresh root gets every payload file; paste a manifest diff.
82. Make the image copy list include the new font directory and the Meta cursor theme.
83. Add a `--check` mode to the image sync path that reports drift per file.
84. Keep the ISO tree under the agreed size budget; record before/after.
85. Remove any build artifact from the tree that is not needed to build (no `.ppm`, logs, or caches).
86. Prove no network access is required by the install or provision scripts; grep for `curl`/`wget` and justify each.
87. Make every new script pass `sh -n`; paste the commands.
88. Make every new Python file pass `py_compile`; paste the commands.
89. Run `verify_tree.sh` and paste its table, including rows that belong to other lanes.
90. Write down every cross-lane request with file:line.

## Section F. Proof and handoff (91-100)

91. Re-run `debrand.sh --check` after all sections; paste PASS.
92. Re-run `check_strings.sh`; paste exit 0.
93. Re-run the font `--check`; paste PASS.
94. Re-run the splash and GRUB checks; paste PASS for both.
95. Paste the exact `fc-match` output for sans, serif, mono on the staged root.
96. State plainly what still needs a boot to prove, and why you did not boot.
97. List every Ubuntu string that remains, with the reason it stays.
98. List every file you touched outside the owned paths, with the request that approved it.
99. Confirm `pgrep -f qemu-system` is empty and no mount is left behind.
100. Write `os-build/lanes/R2_T1_REPORT.md` with task ticks, proofs, skips, and the next three steps.
