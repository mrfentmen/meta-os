# OPENCODE 3 — 300 TASKS (the apps + content lane)

Owner: OpenCode 3. Branch: your lane branch (never push main; Pax merges).
Status file: keep your own section log; UNPROVEN/BLOCKED named, never hidden.
Scope: everything a user touches — applications, content, start page,
media, help. The desktop shell is OpenCode 1's; the agent runtime is
OpenCode 2's; the base image is Hana's; you own what OPENS.

START ORDER: §9 .desktop entries first (they unblock everyone else's
integration), then §1–§6 apps in numeric order, §7 demo content alongside,
§11 associations before §12 closeout. A section blocked on another
lane (an app that doesn't exist yet, a runtime not packaged) is recorded
BLOCKED with the missing piece named, and you move on — never idle.

FENCES (obey in every task):
- Original assets only. Nothing resembling Apple's artwork, icons,
  layouts pixel-for-pixel, or fonts. Milo rejects.
- No mock apps. Every launcher opens something real or is honestly
  labelled UNAVAILABLE with the reason.
- No padded counts. Every number from the command the proof names.
- Every proof is a committed file. Uncommitted = not done.
- BLOCKED is a verdict with an owner and a reason, never an excuse.

## §1 Chromium + start page (OC3B-001..OC3B-025)

- **OC3B-001** Confirm Chromium is installed in the target image
  or record BLOCKED with the package owner. Proof:
  os-build/logs/OC3B-chromium-present.txt.
- **OC3B-002** Record the Chromium version.
  Proof: the version line in OC3B-chromium-present.txt.
- **OC3B-003** Design the Meta start page (local file, no network
  needed to render). Proof: os-build/logs/OC3B-startpage.html.
- **OC3B-004** Confirm the start page renders with no network
  (all assets local/inline). Proof:
  os-build/logs/OC3B-startpage-offline.txt.
- **OC3B-005** Confirm the start page names MetaOS, not Ubuntu.
  Proof: the string check in OC3B-startpage-offline.txt.
- **OC3B-006** Confirm no Apple-adjacent assets on the start page.
  Proof: the audit in os-build/logs/OC3B-startpage-audit.md.
- **OC3B-007** Wire the start page as Chromium's homepage.
  Proof: os-build/logs/OC3B-homepage.md.
- **OC3B-008** Write the Chromium launcher with --app pointing at
  the right entry. Proof: os-build/logs/OC3B-chromium-launcher.md.
- **OC3B-009** Confirm the launcher opens without a terminal.
  Proof: the Terminal=false line in OC3B-chromium-launcher.md.
- **OC3B-010** Record the default search engine and homepage.
  Proof: os-build/logs/OC3B-browser-defaults.md.
- **OC3B-011** Confirm no first-run wizard blocks the browser.
  Proof: os-build/logs/OC3B-browser-firstrun.md.
- **OC3B-012** Record bookmark defaults (Meta pages only).
  Proof: os-build/logs/OC3B-bookmarks.md.
- **OC3B-013** Confirm bookmarks contain no Ubuntu/Apple links.
  Proof: the audit in OC3B-bookmarks.md.
- **OC3B-014** Test the start page at 1280x720 and 1920x1080.
  Proof: os-build/logs/OC3B-startpage-sizes.txt.
- **OC3B-015** Record the page load time cold.
  Proof: os-build/logs/OC3B-startpage-speed.txt.
- **OC3B-016** Confirm the browser keeps no history by default
  or documents the policy. Proof: os-build/logs/OC3B-history.md.
- **OC3B-017** Write the browser operator doc.
  Proof: os-build/logs/OC3B-browser-ops.md.
- **OC3B-018** Hand the launcher + start page to the ISO lane
  in writing. Proof: os-build/logs/OC3B-browser-handoff.md.
- **OC3B-019** If the ISO lane owns install paths: record the
  handoff accepted. Proof: the acceptance note.
- **OC3B-020** If unreachable: ship install instructions yourself,
  documented. Proof: the instructions.
- **OC3B-021** Confirm the browser never phones home on launch.
  Proof: os-build/logs/OC3B-browser-quiet.txt.
- **OC3B-022** Record extensions policy (none/shipped list).
  Proof: os-build/logs/OC3B-extensions.md.
- **OC3B-023** Write the §1 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-024** File every browser defect with repro steps.
  Proof: os-build/logs/OC3B-browser-defects.md (empty is a result).
- **OC3B-025** Commit the §1 artifacts. Proof: the commit sha
  recorded in your lane status.

## §2 File manager (OC3B-026..OC3B-050)

- **OC3B-026** Confirm the file manager package and version.
  Proof: os-build/logs/OC3B-files-present.txt.
- **OC3B-027** Open home, list, create folder, rename, delete —
  record each works. Proof: os-build/logs/OC3B-files-basics.md.
- **OC3B-028** Confirm trash works and empties.
  Proof: the trash test in OC3B-files-basics.md.
- **OC3B-029** Apply the Meta theme to the file manager.
  Proof: a screenshot-or-config note in
  os-build/logs/OC3B-files-theme.md.
- **OC3B-030** Confirm no Ubuntu branding in the file manager.
  Proof: the string audit in OC3B-files-theme.md.
- **OC3B-031** Set the home folder defaults (Documents, Downloads,
  Pictures, Music exist). Proof: os-build/logs/OC3B-home-defaults.md.
- **OC3B-032** Confirm hidden files toggle works.
  Proof: the toggle note in OC3B-files-basics.md.
- **OC3B-033** Confirm search-within-folder works.
  Proof: the search note in OC3B-files-basics.md.
- **OC3B-034** Record the file manager's volume/ sidebar.
  Proof: os-build/logs/OC3B-files-places.md.
- **OC3B-035** Confirm USB sticks appear when_plugged (or BLOCKED
  with the stack owner). Proof: os-build/logs/OC3B-files-usb.md.
- **OC3B-036** Confirm network locations are either working or
  honestly absent. Proof: os-build/logs/OC3B-files-network.md.
- **OC3B-037** Write the file manager launcher entry.
  Proof: os-build/logs/OC3B-files-launcher.md.
- **OC3B-038** Confirm it opens to home, not /.
  Proof: the Exec/Path check in OC3B-files-launcher.md.
- **OC3B-039** Write the file manager operator doc.
  Proof: os-build/logs/OC3B-files-ops.md.
- **OC3B-040** Hand launcher + theme to the ISO/desktop lanes.
  Proof: os-build/logs/OC3B-files-handoff.md.
- **OC3B-041** Record single- vs double-click policy.
  Proof: os-build/logs/OC3B-files-click.md.
- **OC3B-042** Confirm thumbnails work for images.
  Proof: the thumbnail note in OC3B-files-basics.md.
- **OC3B-043** Confirm no thumbnailers phone home.
  Proof: os-build/logs/OC3B-files-quiet.txt.
- **OC3B-044** Record archive handling (zip/tar open).
  Proof: os-build/logs/OC3B-files-archives.md.
- **OC3B-045** Write the §2 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-046** File every file-manager defect with repro steps.
  Proof: os-build/logs/OC3B-files-defects.md (empty is a result).
- **OC3B-047** Confirm the file manager opens in under 2s cold.
  Proof: the timing in OC3B-files-basics.md.
- **OC3B-048** Record disk-usage display correctness.
  Proof: os-build/logs/OC3B-files-disk.md.
- **OC3B-049** Confirm eject/unmount flows for removables.
  Proof: the eject note in OC3B-files-usb.md.
- **OC3B-050** Commit the §2 artifacts. Proof: the commit sha
  recorded in your lane status.

## §3 Terminal (OC3B-051..OC3B-075)

- **OC3B-051** Confirm the terminal package and version.
  Proof: os-build/logs/OC3B-term-present.txt.
- **OC3B-052** Open a shell, run 5 basic commands, record output.
  Proof: os-build/logs/OC3B-term-basics.md.
- **OC3B-053** Apply the Meta theme (colors + font).
  Proof: os-build/logs/OC3B-term-theme.md.
- **OC3B-054** Confirm the metafetch welcome hook fires once.
  Proof: os-build/logs/OC3B-term-welcome.txt.
- **OC3B-055** Confirm the welcome hook never blocks a shell.
  Proof: the timeout test in OC3B-term-welcome.txt.
- **OC3B-056** Record the default shell and prompt.
  Proof: os-build/logs/OC3B-term-prompt.md.
- **OC3B-057** Confirm copy/paste works.
  Proof: the clipboard note in OC3B-term-basics.md.
- **OC3B-058** Confirm tabs/windows work.
  Proof: the tabs note in OC3B-term-basics.md.
- **OC3B-059** Write the terminal launcher.
  Proof: os-build/logs/OC3B-term-launcher.md.
- **OC3B-060** Confirm it opens in home.
  Proof: the check in OC3B-term-launcher.md.
- **OC3B-061** Write the terminal operator doc.
  Proof: os-build/logs/OC3B-term-ops.md.
- **OC3B-062** Hand launcher + theme to the ISO/desktop lanes.
  Proof: os-build/logs/OC3B-term-handoff.md.
- **OC3B-063** Record the scrollback setting.
  Proof: os-build/logs/OC3B-term-scroll.md.
- **OC3B-064** Confirm colours render ANSI correctly.
  Proof: os-build/logs/OC3B-term-ansi.txt.
- **OC3B-065** Confirm the terminal opens in under 1s cold.
  Proof: the timing in OC3B-term-basics.md.
- **OC3B-066** Record font rendering at 2 sizes.
  Proof: os-build/logs/OC3B-term-fonts.md.
- **OC3B-067** Confirm no Ubuntu strings in terminal UI.
  Proof: the string audit in OC3B-term-theme.md.
- **OC3B-068** Write the §3 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-069** File every terminal defect with repro steps.
  Proof: os-build/logs/OC3B-term-defects.md (empty is a result).
- **OC3B-070** Confirm the welcome app opens from the terminal
  menu/shortcut. Proof: os-build/logs/OC3B-term-welcome-link.txt.
- **OC3B-071** Record the terminal's man/info integration.
  Proof: os-build/logs/OC3B-term-docs.md.
- **OC3B-072** Confirm SSH client present and versioned.
  Proof: os-build/logs/OC3B-ssh.txt.
- **OC3B-073** Confirm SSH never auto-connects anywhere.
  Proof: the attestation in OC3B-ssh.txt.
- **OC3B-074** Record Python availability for power users.
  Proof: os-build/logs/OC3B-python.txt.
- **OC3B-075** Commit the §3 artifacts. Proof: the commit sha
  recorded in your lane status.

## §4 Settings panel (OC3B-076..OC3B-100)

- **OC3B-076** Inventory every settings panel/category.
  Proof: os-build/logs/OC3B-settings-inventory.md.
- **OC3B-077** Open each panel, screenshot-or-note it loads.
  Proof: os-build/logs/OC3B-settings-panels.md.
- **OC3B-078** Change wallpaper via settings, confirm it sticks.
  Proof: os-build/logs/OC3B-settings-wallpaper.txt.
- **OC3B-079** Change theme variant, confirm it applies.
  Proof: os-build/logs/OC3B-settings-theme.txt.
- **OC3B-080** Change a keyboard shortcut, confirm it works.
  Proof: os-build/logs/OC3B-settings-keys.txt.
- **OC3B-081** Change timezone/clock, confirm the panel shows it.
  Proof: os-build/logs/OC3B-settings-clock.txt.
- **OC3B-082** Open network settings; working or honestly absent.
  Proof: os-build/logs/OC3B-settings-net.md.
- **OC3B-083** Open display settings; resolution change works or
  is honestly locked. Proof: os-build/logs/OC3B-settings-display.md.
- **OC3B-084** Open user settings; password change works.
  Proof: os-build/logs/OC3B-settings-users.txt.
- **OC3B-085** Confirm no Ubuntu branding in settings.
  Proof: the string audit in os-build/logs/OC3B-settings-brand.txt.
- **OC3B-086** Write the settings launcher.
  Proof: os-build/logs/OC3B-settings-launcher.md.
- **OC3B-087** Hand launcher + theme to the ISO/desktop lanes.
  Proof: os-build/logs/OC3B-settings-handoff.md.
- **OC3B-088** Write the settings operator doc.
  Proof: os-build/logs/OC3B-settings-ops.md.
- **OC3B-089** Record which settings need reboot/relogin.
  Proof: os-build/logs/OC3B-settings-apply.md.
- **OC3B-090** Confirm settings changes survive reboot.
  Proof: os-build/logs/OC3B-settings-persist.txt.
- **OC3B-091** Record accessibility settings present.
  Proof: os-build/logs/OC3B-settings-a11y.md.
- **OC3B-092** Confirm a11y toggles actually toggle.
  Proof: the test notes in OC3B-settings-a11y.md.
- **OC3B-093** Write the §4 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-094** File every settings defect with repro steps.
  Proof: os-build/logs/OC3B-settings-defects.md (empty is a result).
- **OC3B-095** Confirm settings opens in under 2s cold.
  Proof: the timing in OC3B-settings-panels.md.
- **OC3B-096** Record the settings search function.
  Proof: os-build/logs/OC3B-settings-search.md.
- **OC3B-097** Confirm search finds wallpaper + users.
  Proof: the check in OC3B-settings-search.md.
- **OC3B-098** Record printer/settings gaps honestly.
  Proof: os-build/logs/OC3B-settings-gaps.md.
- **OC3B-099** Confirm gaps name owners where known.
  Proof: the owners in OC3B-settings-gaps.md.
- **OC3B-100** Commit the §4 artifacts. Proof: the commit sha
  recorded in your lane status.

## §5 Media apps (OC3B-101..OC3B-125)

- **OC3B-101** Inventory image/music/video viewers present.
  Proof: os-build/logs/OC3B-media-inventory.md.
- **OC3B-102** Open the Meta wallpaper in the image viewer.
  Proof: os-build/logs/OC3B-media-image.txt.
- **OC3B-103** Open the ASCII loop frame in the image viewer.
  Proof: os-build/logs/OC3B-media-ascii.txt.
- **OC3B-104** Play the demo film in the video player.
  Proof: os-build/logs/OC3B-media-film.txt.
- **OC3B-105** Play the ASCII loop MP4 in the video player.
  Proof: os-build/logs/OC3B-media-loop.txt.
- **OC3B-106** Confirm audio plumbing exists or is honestly absent.
  Proof: os-build/logs/OC3B-media-audio.md.
- **OC3B-107** Record the media launcher entries.
  Proof: os-build/logs/OC3B-media-launchers.md.
- **OC3B-108** Hand launchers to the ISO/desktop lanes.
  Proof: os-build/logs/OC3B-media-handoff.md.
- **OC3B-109** Confirm no Ubuntu branding in media apps.
  Proof: the string audit in os-build/logs/OC3B-media-brand.txt.
- **OC3B-110** Write the media operator doc.
  Proof: os-build/logs/OC3B-media-ops.md.
- **OC3B-111** Record screenshot tooling present.
  Proof: os-build/logs/OC3B-screenshot.txt.
- **OC3B-112** Take a desktop screenshot with it.
  Proof: os-build/captures/oc3b-desktop-proof.png.
- **OC3B-113** Confirm the screenshot tool saves to Pictures.
  Proof: the path check in OC3B-screenshot.txt.
- **OC3B-114** Record webcam tooling or honest absence.
  Proof: os-build/logs/OC3B-webcam.md.
- **OC3B-115** Confirm no app phones home on first run.
  Proof: os-build/logs/OC3B-media-quiet.txt.
- **OC3B-116** Write the §5 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-117** File every media defect with repro steps.
  Proof: os-build/logs/OC3B-media-defects.md (empty is a result).
- **OC3B-118** Record media codec coverage honestly.
  Proof: os-build/logs/OC3B-codecs.md.
- **OC3B-119** Confirm the film plays with audio state noted.
  Proof: the note in OC3B-media-film.txt.
- **OC3B-120** Record volume control presence.
  Proof: os-build/logs/OC3B-volume.md.
- **OC3B-121** Confirm mute works.
  Proof: the mute test in OC3B-volume.md.
- **OC3B-122** Hand volume findings to the desktop lane.
  Proof: os-build/logs/OC3B-volume-handoff.md.
- **OC3B-123** Record any proprietary codec gaps.
  Proof: os-build/logs/OC3B-codec-gaps.md.
- **OC3B-124** Confirm gaps name the package that fills them.
  Proof: the packages in OC3B-codec-gaps.md.
- **OC3B-125** Commit the §5 artifacts. Proof: the commit sha
  recorded in your lane status.

## §6 Office + utilities (OC3B-126..OC3B-150)

- **OC3B-126** Inventory editor/calculator/notes apps.
  Proof: os-build/logs/OC3B-office-inventory.md.
- **OC3B-127** Open a text editor, type, save, reopen.
  Proof: os-build/logs/OC3B-office-editor.md.
- **OC3B-128** Confirm the editor uses a Meta-readable font.
  Proof: the font note in OC3B-office-editor.md.
- **OC3B-129** Open the calculator, run 5 operations.
  Proof: os-build/logs/OC3B-office-calc.md.
- **OC3B-130** Open the welcome app from the menu.
  Proof: os-build/logs/OC3B-office-welcome.txt.
- **OC3B-131** Confirm the welcome app shows once, not always.
  Proof: the flag test in OC3B-office-welcome.txt.
- **OC3B-132** Record the office launcher entries.
  Proof: os-build/logs/OC3B-office-launchers.md.
- **OC3B-133** Hand launchers to the ISO/desktop lanes.
  Proof: os-build/logs/OC3B-office-handoff.md.
- **OC3B-134** Confirm no Ubuntu branding in office apps.
  Proof: the string audit in os-build/logs/OC3B-office-brand.txt.
- **OC3B-135** Write the office operator doc.
  Proof: os-build/logs/OC3B-office-ops.md.
- **OC3B-136** Record archive manager presence + test.
  Proof: os-build/logs/OC3B-archiver.md.
- **OC3B-137** Record PDF reader presence + test.
  Proof: os-build/logs/OC3B-pdf.md.
- **OC3B-138** Confirm PDFs render Meta docs correctly.
  Proof: the render note in OC3B-pdf.md.
- **OC3B-139** Record printing stack or honest absence.
  Proof: os-build/logs/OC3B-printing.md.
- **OC3B-140** Confirm no app phones home on first run.
  Proof: os-build/logs/OC3B-office-quiet.txt.
- **OC3B-141** Write the §6 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-142** File every office defect with repro steps.
  Proof: os-build/logs/OC3B-office-defects.md (empty is a result).
- **OC3B-143** Record clipboard manager behaviour.
  Proof: os-build/logs/OC3B-clipboard.md.
- **OC3B-144** Confirm clipboard survives app close.
  Proof: the test in OC3B-clipboard.md.
- **OC3B-145** Record character map / emoji picker.
  Proof: os-build/logs/OC3B-charmap.md.
- **OC3B-146** Confirm the font picker lists Inter.
  Proof: the check in os-build/logs/OC3B-fontpicker.md.
- **OC3B-147** Record disk-usage/settings helpers.
  Proof: os-build/logs/OC3B-diskutils.md.
- **OC3B-148** Hand helpers to the ISO/desktop lanes.
  Proof: os-build/logs/OC3B-diskutils-handoff.md.
- **OC3B-149** Confirm all office apps open in under 3s cold.
  Proof: the timings in OC3B-office-editor.md.
- **OC3B-150** Commit the §6 artifacts. Proof: the commit sha
  recorded in your lane status.

## §7 Demo content pack (OC3B-151..OC3B-175)

- **OC3B-151** Inventory demo content: film, wallpapers, loop,
  screenshots. Proof: os-build/logs/OC3B-demo-inventory.md.
- **OC3B-152** Confirm the 180.000s film plays in full.
  Proof: os-build/logs/OC3B-demo-film.txt.
- **OC3B-153** Confirm the ASCII loop MP4 plays in full.
  Proof: os-build/logs/OC3B-demo-loop.txt.
- **OC3B-154** Confirm wallpapers render fullscreen cleanly.
  Proof: os-build/logs/OC3B-demo-wallpapers.md.
- **OC3B-155** Place demo content in ~/Videos + ~/Pictures.
  Proof: os-build/logs/OC3B-demo-placed.md.
- **OC3B-156** Confirm the tour hits: desktop, apps, agents.
  Proof: os-build/logs/OC3B-demo-tour.md.
- **OC3B-157** Write the 60-second demo script.
  Proof: os-build/logs/OC3B-demo-60s.md.
- **OC3B-158** Time the scripted demo end to end.
  Proof: the timing in OC3B-demo-60s.md.
- **OC3B-159** Record the demo's honest-labelling checks.
  Proof: os-build/logs/OC3B-demo-honest.md.
- **OC3B-160** Confirm SIMULATED labels intact everywhere shown.
  Proof: the label sweep in OC3B-demo-honest.md.
- **OC3B-161** Write the demo launcher (opens tour + film).
  Proof: os-build/logs/OC3B-demo-launcher.md.
- **OC3B-162** Hand the launcher to the ISO/desktop lanes.
  Proof: os-build/logs/OC3B-demo-handoff.md.
- **OC3B-163** Record the demo content licenses.
  Proof: os-build/logs/OC3B-demo-licenses.md.
- **OC3B-164** Confirm all demo content is original or licensed.
  Proof: the audit in OC3B-demo-licenses.md.
- **OC3B-165** Confirm no third-party footage in the pack.
  Proof: the attestation in OC3B-demo-licenses.md.
- **OC3B-166** Write the §7 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-167** File every demo-content defect with repro steps.
  Proof: os-build/logs/OC3B-demo-defects.md (empty is a result).
- **OC3B-168** Record the total demo pack size.
  Proof: os-build/logs/OC3B-demo-size.txt.
- **OC3B-169** Confirm the pack fits the ISO budget.
  Proof: the budget check in OC3B-demo-size.txt.
- **OC3B-170** Hand oversize items to Pax with options.
  Proof: os-build/logs/OC3B-demo-size-handoff.md.
- **OC3B-171** Confirm the film's closing line on screen.
  Proof: os-build/logs/OC3B-demo-closing.txt.
- **OC3B-172** Confirm the loop plays without stutter.
  Proof: the playback note in OC3B-demo-loop.txt.
- **OC3B-173** Record the demo audio state.
  Proof: os-build/logs/OC3B-demo-audio.md.
- **OC3B-174** Confirm the tour works with no network.
  Proof: os-build/logs/OC3B-demo-offline.txt.
- **OC3B-175** Commit the §7 artifacts. Proof: the commit sha
  recorded in your lane status.

## §8 Help + about system (OC3B-176..OC3B-200)

- **OC3B-176** Write the About MetaOS page.
  Proof: os-build/logs/OC3B-about.md.
- **OC3B-177** Name the kernel, the base, and the track split
  honestly. Proof: the version block in OC3B-about.md.
- **OC3B-178** List what's 1.0 and what's 2.0-roadmap.
  Proof: the roadmap block in OC3B-about.md.
- **OC3B-179** Write the Help launcher.
  Proof: os-build/logs/OC3B-help-launcher.md.
- **OC3B-180** Hand launcher + pages to the ISO/desktop lanes.
  Proof: os-build/logs/OC3B-help-handoff.md.
- **OC3B-181** Write the first-boot tips (5 cards max).
  Proof: os-build/logs/OC3B-tips.md.
- **OC3B-182** Confirm tips show once, dismiss forever.
  Proof: the flag test in OC3B-tips.md.
- **OC3B-183** Write the keyboard-shortcuts reference.
  Proof: os-build/logs/OC3B-shortcuts.md.
- **OC3B-184** Confirm every listed shortcut works.
  Proof: the test column in OC3B-shortcuts.md.
- **OC3B-185** Name unimplemented shortcuts honestly.
  Proof: the UNIMPLEMENTED column in OC3B-shortcuts.md.
- **OC3B-186** Write the troubleshooting page (top 10 issues).
  Proof: os-build/logs/OC3B-troubleshoot.md.
- **OC3B-187** Confirm each fix was actually tried.
  Proof: the tried column in OC3B-troubleshoot.md.
- **OC3B-188** Write the privacy statement.
  Proof: os-build/logs/OC3B-privacy.md.
- **OC3B-189** Confirm it matches reality (local-only, no
  accounts, no telemetry). Proof: the audit in OC3B-privacy.md.
- **OC3B-190** Write the data-location page (where things live).
  Proof: os-build/logs/OC3B-dataloc.md.
- **OC3B-191** Confirm every path listed exists.
  Proof: the path check in OC3B-dataloc.md.
- **OC3B-192** Write the §8 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-193** File every help defect with repro steps.
  Proof: os-build/logs/OC3B-help-defects.md (empty is a result).
- **OC3B-194** Confirm help opens offline.
  Proof: os-build/logs/OC3B-help-offline.txt.
- **OC3B-195** Confirm help has no dead links.
  Proof: the link check in os-build/logs/OC3B-help-links.txt.
- **OC3B-196** Hand dead links to owners or cut the links.
  Proof: the disposition in OC3B-help-links.txt.
- **OC3B-197** Record the help content license.
  Proof: os-build/logs/OC3B-help-license.md.
- **OC3B-198** Confirm the license allows ISO inclusion.
  Proof: the verdict in OC3B-help-license.md.
- **OC3B-199** Record what "done" means for help in 1.0.
  Proof: the definition in your lane status.
- **OC3B-200** Commit the §8 artifacts. Proof: the commit sha
  recorded in your lane status.

## §9 .desktop entries (OC3B-201..OC3B-225)

- **OC3B-201** Inventory every app needing a launcher.
  Proof: os-build/logs/OC3B-desktop-inventory.md.
- **OC3B-202** Write one .desktop per app.
  Proof: os-build/logs/OC3B-desktop-files.md.
- **OC3B-203** Validate every .desktop file.
  Proof: the validator output in OC3B-desktop-files.md.
- **OC3B-204** Confirm every Exec path exists on the image.
  Proof: the path check in OC3B-desktop-files.md.
- **OC3B-205** Confirm every Icon resolves.
  Proof: the icon check in OC3B-desktop-files.md.
- **OC3B-206** Confirm TryExec guards every entry.
  Proof: the guard audit in OC3B-desktop-files.md.
- **OC3B-207** Confirm no entry needs a terminal.
  Proof: the Terminal=false audit in OC3B-desktop-files.md.
- **OC3B-208** Confirm categories are sane.
  Proof: the category audit in OC3B-desktop-files.md.
- **OC3B-209** Confirm OnlyShowIn=XFCE everywhere.
  Proof: the audit in OC3B-desktop-files.md.
- **OC3B-210** Write the launcher test: each entry parses.
  Proof: os-build/logs/OC3B-desktop-test.txt.
- **OC3B-211** Confirm each entry's target runs (or is honestly
  UNAVAILABLE with a reason). Proof:
  os-build/logs/OC3B-desktop-targets.md.
- **OC3B-212** Hand entries to the ISO/desktop lanes.
  Proof: os-build/logs/OC3B-desktop-handoff.md.
- **OC3B-213** Record the dock pin set.
  Proof: os-build/logs/OC3B-dockpins.md.
- **OC3B-214** Confirm pinned apps exist.
  Proof: the check in OC3B-dockpins.md.
- **OC3B-215** Record the menu structure.
  Proof: os-build/logs/OC3B-menu.md.
- **OC3B-216** Confirm every menu item opens something.
  Proof: the check in OC3B-menu.md.
- **OC3B-217** Confirm no dead menu entries.
  Proof: the audit in OC3B-menu.md.
- **OC3B-218** Record the menu search behaviour.
  Proof: os-build/logs/OC3B-menu-search.md.
- **OC3B-219** Confirm search finds every app.
  Proof: the check in OC3B-menu-search.md.
- **OC3B-220** Write the §9 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-221** File every launcher defect with repro steps.
  Proof: os-build/logs/OC3B-desktop-defects.md (empty is a result).
- **OC3B-222** Confirm launchers survive reboot.
  Proof: os-build/logs/OC3B-desktop-persist.txt.
- **OC3B-223** Confirm launchers survive upgrade.
  Proof: os-build/logs/OC3B-desktop-upgrade.txt.
- **OC3B-224** Record launcher ownership per file.
  Proof: os-build/logs/OC3B-desktop-owners.md.
- **OC3B-225** Commit the §9 artifacts. Proof: the commit sha
  recorded in your lane status.

## §10 Defaults + associations (OC3B-226..OC3B-250)

- **OC3B-226** Record default browser + handler.
  Proof: os-build/logs/OC3B-defaults-browser.md.
- **OC3B-227** Record default file manager + handler.
  Proof: os-build/logs/OC3B-defaults-files.md.
- **OC3B-228** Record default terminal + handler.
  Proof: os-build/logs/OC3B-defaults-term.md.
- **OC3B-229** Record default text editor.
  Proof: os-build/logs/OC3B-defaults-editor.md.
- **OC3B-230** Record default image/music/video apps.
  Proof: os-build/logs/OC3B-defaults-media.md.
- **OC3B-231** Open one file of each type, confirm the right app.
  Proof: os-build/logs/OC3B-defaults-test.md.
- **OC3B-232** Record any association that is NOT set and why.
  Proof: the gaps in OC3B-defaults-test.md.
- **OC3B-233** Confirm associations survive reboot.
  Proof: os-build/logs/OC3B-defaults-persist.txt.
- **OC3B-234** Confirm associations survive upgrade.
  Proof: os-build/logs/OC3B-defaults-upgrade.txt.
- **OC3B-235** Write the defaults operator doc.
  Proof: os-build/logs/OC3B-defaults-ops.md.
- **OC3B-236** Hand defaults to the ISO lane in writing.
  Proof: os-build/logs/OC3B-defaults-handoff.md.
- **OC3B-237** Record xdg-open behaviour.
  Proof: os-build/logs/OC3B-xdg-open.md.
- **OC3B-238** Confirm xdg-open routes per defaults.
  Proof: the tests in OC3B-xdg-open.md.
- **OC3B-239** Record mailto: handling or honest absence.
  Proof: os-build/logs/OC3B-mailto.md.
- **OC3B-240** Record print-to-file handling.
  Proof: os-build/logs/OC3B-printtofile.md.
- **OC3B-241** Write the §10 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-242** File every defaults defect with repro steps.
  Proof: os-build/logs/OC3B-defaults-defects.md (empty is a result).
- **OC3B-243** Confirm defaults match the start-page links.
  Proof: os-build/logs/OC3B-defaults-startpage.md.
- **OC3B-244** Confirm no default points at missing software.
  Proof: the audit in OC3B-defaults-startpage.md.
- **OC3B-245** Record removable-media autorun policy.
  Proof: os-build/logs/OC3B-autorun.md.
- **OC3B-246** Confirm autorun never executes silently.
  Proof: the attestation in OC3B-autorun.md.
- **OC3B-247** Record URL-handler allowlist.
  Proof: os-build/logs/OC3B-urlhandlers.md.
- **OC3B-248** Confirm unknown schemes prompt, never run.
  Proof: the test in OC3B-urlhandlers.md.
- **OC3B-249** Hand handlers to the ISO lane in writing.
  Proof: os-build/logs/OC3B-urlhandlers-handoff.md.
- **OC3B-250** Commit the §10 artifacts. Proof: the commit sha
  recorded in your lane status.

## §11 Installer slideshow + branding (OC3B-251..OC3B-275)

- **OC3B-251** Read the existing slideshow checker output.
  Proof: the baseline in os-build/logs/OC3B-slideshow-base.txt.
- **OC3B-252** Extend slide copy where thin, honestly.
  Proof: the edits + re-run in OC3B-slideshow-base.txt.
- **OC3B-253** Confirm all 5 slides render offline.
  Proof: os-build/logs/OC3B-slides-render.txt.
- **OC3B-254** Confirm no http(s) in any slide.
  Proof: the grep in OC3B-slides-render.txt.
- **OC3B-255** Confirm Meta palette only.
  Proof: the color audit in OC3B-slides-render.txt.
- **OC3B-256** Confirm no Ubuntu/Apple strings.
  Proof: the string audit in OC3B-slides-render.txt.
- **OC3B-257** Verify the slideshow spec against Calamares docs.
  Proof: os-build/logs/OC3B-slideshow-spec.md.
- **OC3B-258** Confirm image-list form is what ships.
  Proof: the config quote in OC3B-slideshow-spec.md.
- **OC3B-259** Record the HTML slides' future wiring job.
  Proof: os-build/logs/OC3B-slideshow-wiring.md.
- **OC3B-260** Confirm the wiring job names an owner.
  Proof: the owner in OC3B-slideshow-wiring.md.
- **OC3B-261** Verify branding.desc matches reality.
  Proof: os-build/logs/OC3B-branding-desc.md.
- **OC3B-262** Confirm productName/productVersion correct.
  Proof: the fields in OC3B-branding-desc.md.
- **OC3B-263** Verify the slideshow CSS has no web fonts.
  Proof: the font audit in OC3B-slides-render.txt.
- **OC3B-264** Confirm slides work at 1024x768 and 1920x1080.
  Proof: os-build/logs/OC3B-slides-sizes.txt.
- **OC3B-265** Record slide imagery licenses.
  Proof: os-build/logs/OC3B-slides-licenses.md.
- **OC3B-266** Confirm all imagery is original or licensed.
  Proof: the audit in OC3B-slides-licenses.md.
- **OC3B-267** Write the §11 verdict. Proof: the verdict block in
  your lane status.
- **OC3B-268** File every slideshow defect with repro steps.
  Proof: os-build/logs/OC3B-slideshow-defects.md (empty is a result).
- **OC3B-269** Hand slideshow + branding to the ISO lane.
  Proof: os-build/logs/OC3B-slideshow-handoff.md.
- **OC3B-270** Confirm the handoff was accepted.
  Proof: the acceptance note.
- **OC3B-271** Record the installer welcome copy.
  Proof: os-build/logs/OC3B-installer-copy.md.
- **OC3B-272** Confirm copy matches Meta voice.
  Proof: the review in OC3B-installer-copy.md.
- **OC3B-273** Record the installer finish copy.
  Proof: os-build/logs/OC3B-installer-finish.md.
- **OC3B-274** Confirm finish copy states reboot honestly.
  Proof: the review in OC3B-installer-finish.md.
- **OC3B-275** Commit the §11 artifacts. Proof: the commit sha
  recorded in your lane status.

## §12 Closeout + handoff (OC3B-276..OC3B-300)

- **OC3B-276** Re-run the browser offline check.
  Proof: os-build/logs/OC3B-closeout-browser.txt.
- **OC3B-277** Re-run the launcher validation.
  Proof: os-build/logs/OC3B-closeout-launchers.txt.
- **OC3B-278** Re-run the defaults spot check.
  Proof: os-build/logs/OC3B-closeout-defaults.txt.
- **OC3B-279** Re-run the slideshow checker.
  Proof: os-build/logs/OC3B-closeout-slideshow.txt.
- **OC3B-280** Inventory every proof file this list committed.
  Proof: os-build/logs/OC3B-proof-index.md.
- **OC3B-281** Verify every proof path in your status resolves.
  Proof: the check output in OC3B-proof-index.md.
- **OC3B-282** Write the handoff note to Pax: what is ready,
  what must NOT merge, merge order. Proof:
  os-build/logs/OC3B-handoff.md.
- **OC3B-283** List every UNPROVEN/BLOCKED row with owner.
  Proof: the list in OC3B-handoff.md.
- **OC3B-284** Record the honest readiness verdict: READY or
  the named rows that are not. Proof: the verdict in OC3B-handoff.md.
- **OC3B-285** Confirm no secrets in the branch.
  Proof: the scan in os-build/logs/OC3B-closeout-secrets.txt.
- **OC3B-286** Confirm no mock presented as live anywhere.
  Proof: the label audit in os-build/logs/OC3B-closeout-honest.md.
- **OC3B-287** Confirm nothing in this lane touches main.
  Proof: the branch attestation in OC3B-handoff.md.
- **OC3B-288** Post build status to room 1 as things land.
  Proof: the post log in OC3B-handoff.md.
- **OC3B-289** Record where spare time went if any section
  finished early. Proof: the note in OC3B-handoff.md.
- **OC3B-290** Write the final status-file pass: every section
  DONE/UNPROVEN/BLOCKED with reasons. Proof: your completed
  lane status file.
- **OC3B-291** Verify the status file's every proof path resolves.
  Proof: the check output appended to OC3B-proof-index.md.
- **OC3B-292** Record the list's total live spend (likely 0 —
  apps need no model calls). Proof:
  os-build/logs/OC3B-spend-lane-total.txt.
- **OC3B-293** Record total lane wall-clock by section.
  Proof: os-build/logs/OC3B-time-table.md.
- **OC3B-294** Assemble the DEL-ONLY list for your lane.
  Proof: os-build/logs/OC3B-delonly.md.
- **OC3B-295** Write the timeline to the deadline with owners.
  Proof: os-build/logs/OC3B-timeline.md.
- **OC3B-296** Record the claim-clause map: PROVEN/UNPROVEN per
  clause with paths. Proof: os-build/logs/OC3B-clauses.md.
- **OC3B-297** For every UNPROVEN clause write the one-line
  reason. Proof: the reasons in OC3B-clauses.md.
- **OC3B-298** Final commit on your branch. Proof: the commit
  sha in your lane status.
- **OC3B-299** The last line of your status: what remains
  unproven in plain words. Proof: the final line.
- **OC3B-300** Confirm the apps open on a booted system OR name
  the boot that proves them. Proof: the boot reference or the
  honest BLOCKED line.
