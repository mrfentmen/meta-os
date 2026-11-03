# OPENCODE 1 — 300 TASKS (the ISO closeout lane)

Owner: OpenCode 1. Branch: opencode1/boot-installer + opencode1/metaos-1.0
(merge as the work lands; Pax merges to main). Status: this file's
sections, proof lines per task, UNPROVEN named.

This list starts where the 500-task closeout and the 12-hour plan left
off: the single-squashfs pipeline exists and is gated; the remaining work
is rebuild → boot → brand-verify → install → hand over.

START ORDER: §1 pipeline hardening first (it is DONE — verify, don't
redo), §2 rebuild, §3 first boot of the new ISO, §4–§8 verification in
numeric order, §9 installer, §10–§12 closeout. A task blocked on another
lane (an app that doesn't exist, a fix only Rowan/Buffy can land) is
recorded BLOCKED with the missing piece named, and you move on — never
idle, never padded, never a silent skip.

FENCES (obey in every task):
- No VM boots except one at a time on the big Mac, and only at a
  declared milestone (see BOOT_POLICY.md). TCG boots prove function,
  never performance.
- Every number from the command and run that produced it.
- Every proof is a committed file. Uncommitted = not done.
- No real emergency services, no non-loopback dispatch, ever.
- No Apple/Ubuntu trademarked assets or strings in anything shipped.

## §1 Pipeline — verify, don't redo (OC1C-001..OC1C-025)

- **OC1C-001** Re-run the lane gate (run_checks.sh) on the current
  tree and record the result. Proof:
  os-build/logs/OC1C-lane-gate.txt.
- **OC1C-002** Confirm 0 fail before any rebuild.
  Proof: the count line in OC1C-lane-gate.txt.
- **OC1C-003** Verify merge-layers.sh contains all 6 gates.
  Proof: os-build/logs/OC1C-gates-present.txt.
- **OC1C-004** Verify the UUID-sync GATE 6 logic reads the built
  initrd, not a stale file. Proof:
  os-build/logs/OC1C-gate6-source.md.
- **OC1C-005** Verify finalize-iso-tree.sh is still idempotent
  (grub edits applied exactly once). Proof:
  os-build/logs/OC1C-finalize-idempotent.txt.
- **OC1C-006** Verify the Calamares config this pipeline consumes
  is the merged one. Proof: os-build/logs/OC1C-calamares-src.md.
- **OC1C-007** Verify the Imperium payload dir is complete
  (index, js, vendor, styles, icon, manifest, server, wrapper).
  Proof: os-build/logs/OC1C-payload-imperium.md.
- **OC1C-008** Verify the theme payload is current vs
  opencode1/metaos-1.0 tip. Proof:
  os-build/logs/OC1C-payload-theme-fresh.md.
- **OC1C-009** If the theme payload is stale: re-vendor and note
  what changed. Proof: the re-vendor commit or the "current" note.
- **OC1C-010** Verify the welcome app in the payload passes its
  own 30 tests from the vendored copy. Proof:
  os-build/logs/OC1C-welcome-retest.txt.
- **OC1C-011** Verify the splash theme files are the validated
  set (meta-m, background, progress, .plymouth, .script).
  Proof: os-build/logs/OC1C-splash-set.txt.
- **OC1C-012** Verify no Ubuntu/XFCE default branding survives
  in the payload dirs. Proof: the grep in
  os-build/logs/OC1C-payload-brand.txt.
- **OC1C-013** Confirm every payload file's license allows ISO
  inclusion. Proof: os-build/logs/OC1C-payload-licenses.md.
- **OC1C-014** Record the payload total size.
  Proof: os-build/logs/OC1C-payload-size.txt.
- **OC1C-015** Confirm the payload fits the ISO budget.
  Proof: the budget check in OC1C-payload-size.txt.
- **OC1C-016** If oversized: cut list with Pax's call, not yours.
  Proof: os-build/logs/OC1C-payload-cut.md or "fits".
- **OC1C-017** Verify docker daemon + 15 GB free before build.
  Proof: os-build/logs/OC1C-build-ready.txt.
- **OC1C-018** Verify the base ISO checksum matches the pinned
  value. Proof: os-build/logs/OC1C-base-hash.txt.
- **OC1C-019** Verify mergebox/container pathing for the run.
  Proof: os-build/logs/OC1C-build-env.md.
- **OC1C-020** Record the exact pipeline commit being built.
  Proof: the sha in os-build/logs/OC1C-build-commit.txt.
- **OC1C-021** Dry-run the pipeline's argument parsing only.
  Proof: os-build/logs/OC1C-arg-parse.txt.
- **OC1C-022** Confirm no VM is running before the heavy build.
  Proof: the pgrep output in OC1C-build-env.md.
- **OC1C-023** Write the pre-build checklist sign-off.
  Proof: os-build/logs/OC1C-prebuild.md.
- **OC1C-024** If any pre-build check fails: fix it, do NOT
  start the build. Proof: the fix or the green checklist.
- **OC1C-025** Commit the §1 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §2 Rebuild (OC1C-026..OC1C-050)

- **OC1C-026** Run the full merge-layers.sh pipeline.
  Proof: os-build/logs/OC1C-merge-console.log.
- **OC1C-027** Confirm exit 0 with no GATE-FAIL.
  Proof: the tail of OC1C-merge-console.log.
- **OC1C-028** Record the new filesystem.squashfs size.
  Proof: os-build/logs/OC1C-squashfs-size.txt.
- **OC1C-029** Confirm casper file count >= 40 in the new initrd.
  Proof: os-build/logs/OC1C-casper-count.txt.
- **OC1C-030** Confirm initrd UUID == tree casper-uuid.
  Proof: os-build/logs/OC1C-uuid-match.txt.
- **OC1C-031** Confirm live user tooling present (user-setup).
  Proof: os-build/logs/OC1C-usersetup.txt.
- **OC1C-032** Confirm kernel modules dir present.
  Proof: os-build/logs/OC1C-modules.txt.
- **OC1C-033** Confirm Plymouth theme + greeter conf + welcome
  app + Imperium payload landed in the rootfs. Proof:
  os-build/logs/OC1C-payload-landed.txt.
- **OC1C-034** Rebuild the ISO with the pinned xorriso recipe.
  Proof: os-build/logs/OC1C-iso-build.log.
- **OC1C-035** Record the ISO sha256 + size.
  Proof: os-build/logs/OC1C-iso-sha.txt.
- **OC1C-036** Verify El Torito has exactly BIOS+UEFI entries.
  Proof: os-build/logs/OC1C-eltorito.txt.
- **OC1C-037** Verify grub carries layerfs-path + console.
  Proof: os-build/logs/OC1C-grub-flags.txt.
- **OC1C-038** Verify .disk/info says MetaOS.
  Proof: os-build/logs/OC1C-disk-info.txt.
- **OC1C-039** Verify install-sources.yaml is single-source.
  Proof: os-build/logs/OC1C-sources.txt.
- **OC1C-040** Verify filesystem.manifest regenerated.
  Proof: the line count in os-build/logs/OC1C-manifest.txt.
- **OC1C-041** Record the full file list of the ISO tree.
  Proof: os-build/logs/OC1C-iso-tree.txt.
- **OC1C-042** Confirm no layered squashfs remains on the ISO.
  Proof: the check in os-build/logs/OC1C-nolayers.txt.
- **OC1C-043** Confirm tmp/scratch cleaned, no strays committed.
  Proof: git status clean note in OC1C-nolayers.txt.
- **OC1C-044** Write the build record: inputs, outputs, hashes,
  duration. Proof: os-build/logs/OC1C-build-record.md.
- **OC1C-045** Tag the build inputs in git (no tag on output).
  Proof: the input tree sha in OC1C-build-record.md.
- **OC1C-046** If any gate failed: fix, rebuild, never ship a
  red build. Proof: the green re-run or the BLOCKED note.
- **OC1C-047** Confirm the ISO boots no other lane's unmerged
  work. Proof: the branch-tip check in OC1C-build-record.md.
- **OC1C-048** Hand the ISO + sha to the boot milestone.
  Proof: os-build/logs/OC1C-iso-handoff.md.
- **OC1C-049** Mark the previous ISO superseded in writing.
  Proof: the supersede line in OC1C-iso-handoff.md.
- **OC1C-050** Commit the §2 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §3 First boot of the new ISO (OC1C-051..OC1C-075)

- **OC1C-051** Declare the boot milestone in writing.
  Proof: os-build/logs/OC1C-milestone.md.
- **OC1C-052** Confirm no other VM is running.
  Proof: the pgrep output in OC1C-milestone.md.
- **OC1C-053** Boot: reach the bootloader.
  Proof: os-build/logs/OC1C-boot-grub.txt.
- **OC1C-054** Boot: kernel starts, no panic.
  Proof: the serial excerpt in os-build/logs/OC1C-boot-kernel.txt.
- **OC1C-055** Boot: casper finds the medium.
  Proof: the find_livefs lines in OC1C-boot-kernel.txt.
- **OC1C-056** Boot: single squashfs mounts.
  Proof: the mount lines in OC1C-boot-kernel.txt.
- **OC1C-057** Boot: switch_root succeeds.
  Proof: the systemd lines in OC1C-boot-kernel.txt.
- **OC1C-058** Confirm zero "layers are missing" lines.
  Proof: the grep count in OC1C-boot-kernel.txt.
- **OC1C-059** Confirm zero "no live file system" lines.
  Proof: the grep count in OC1C-boot-kernel.txt.
- **OC1C-060** Screenshot the greeter.
  Proof: os-build/captures/oc1c-greeter.png.
- **OC1C-061** Confirm the greeter shows Meta branding.
  Proof: the visual check note in
  os-build/logs/OC1C-greeter-check.md.
- **OC1C-062** Log in as the live user.
  Proof: os-build/logs/OC1C-login.txt.
- **OC1C-063** Screenshot the desktop.
  Proof: os-build/captures/oc1c-desktop.png.
- **OC1C-064** Confirm the ASCII wallpaper is live.
  Proof: the visual check in os-build/logs/OC1C-wallpaper-check.md.
- **OC1C-065** Open the terminal, run the welcome hook.
  Proof: os-build/logs/OC1C-term-check.txt.
- **OC1C-066** Open the Imperium app from the dock/menu.
  Proof: os-build/logs/OC1C-imperium-open.txt.
- **OC1C-067** Screenshot the Imperium app open.
  Proof: os-build/captures/oc1c-imperium.png.
- **OC1C-068** Confirm its backend runs on localhost only.
  Proof: os-build/logs/OC1C-imperium-net.txt.
- **OC1C-069** Open files, settings, browser once each.
  Proof: os-build/logs/OC1C-apps-open.md.
- **OC1C-070** Screenshot the open apps.
  Proof: os-build/captures/oc1c-apps.png.
- **OC1C-071** Record every failure seen, with serial lines.
  Proof: os-build/logs/OC1C-boot-failures.md (empty is a result).
- **OC1C-072** Shut the VM down cleanly afterwards.
  Proof: the shutdown note in OC1C-boot-failures.md.
- **OC1C-073** Write the boot verdict: BOOTED or the exact
  failure. Proof: os-build/logs/OC1C-boot-verdict.md.
- **OC1C-074** If BOOTED: list what worked vs what is stub.
  Proof: the inventory in OC1C-boot-verdict.md.
- **OC1C-075** Commit the §3 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §4 Greeter + login + session (OC1C-076..OC1C-100)

- **OC1C-076** Confirm greeter background is the ASCII art.
  Proof: os-build/logs/OC1C-greeter-bg.md.
- **OC1C-077** Confirm greeter shows MetaOS, no Xubuntu.
  Proof: the string check in OC1C-greeter-bg.md.
- **OC1C-078** Confirm the login password flow works.
  Proof: os-build/logs/OC1C-login-flow.txt.
- **OC1C-079** Confirm autologin state matches design.
  Proof: os-build/logs/OC1C-autologin.md.
- **OC1C-080** Confirm the session is Xfce.
  Proof: os-build/logs/OC1C-session.md.
- **OC1C-081** Confirm the top panel loads.
  Proof: the screenshot reference in OC1C-session.md.
- **OC1C-082** Confirm the dock loads with pinned apps.
  Proof: os-build/logs/OC1C-dock.md.
- **OC1C-083** Confirm pinned apps all exist.
  Proof: the check in OC1C-dock.md.
- **OC1C-084** Confirm the clock/menu/tray appear.
  Proof: os-build/logs/OC1C-panel.md.
- **OC1C-085** Confirm no Ubuntu strings in the session.
  Proof: the sweep in os-build/logs/OC1C-no-ubuntu.txt.
- **OC1C-086** Record remaining Ubuntu strings if any, with
  owner + fix. Proof: OC1C-no-ubuntu.txt.
- **OC1C-087** Confirm hostname is MetaOS-flavoured.
  Proof: os-build/logs/OC1C-hostname.txt.
- **OC1C-088** Confirm os-release says MetaOS.
  Proof: os-build/logs/OC1C-osrelease.txt.
- **OC1C-089** Open a terminal, confirm the prompt.
  Proof: os-build/logs/OC1C-term-prompt.txt.
- **OC1C-090** Confirm lock screen works.
  Proof: os-build/logs/OC1C-lockscreen.txt.
- **OC1C-091** Confirm unlock returns to the session.
  Proof: the check in OC1C-lockscreen.txt.
- **OC1C-092** Confirm logout/login cycle keeps settings.
  Proof: os-build/logs/OC1C-relologin.txt.
- **OC1C-093** Write the §4 verdict. Proof: the verdict block
  in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-094** File every session defect with repro steps.
  Proof: os-build/logs/OC1C-session-defects.md (empty is a result).
- **OC1C-095** Confirm the greeter is keyboard-navigable.
  Proof: os-build/logs/OC1C-greeter-kbd.md.
- **OC1C-096** Confirm greeter contrast is readable.
  Proof: os-build/logs/OC1C-greeter-contrast.md.
- **OC1C-097** Record greeter load time.
  Proof: os-build/logs/OC1C-greeter-time.txt.
- **OC1C-098** Confirm no greeter console errors.
  Proof: the console log in OC1C-greeter-time.txt.
- **OC1C-099** Hand session issues to the desktop/theme lane.
  Proof: os-build/logs/OC1C-session-handoff.md.
- **OC1C-100** Commit the §4 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §5 Splash + boot visuals (OC1C-101..OC1C-125)

- **OC1C-101** Screenshot the Plymouth splash.
  Proof: os-build/captures/oc1c-splash.png.
- **OC1C-102** Confirm “Loading into MetaOS” is legible.
  Proof: the visual check in os-build/logs/OC1C-splash-check.md.
- **OC1C-103** Confirm the progress bar advances.
  Proof: the frame comparison in OC1C-splash-check.md.
- **OC1C-104** Confirm the M mark renders, not a fallback.
  Proof: the visual check in OC1C-splash-check.md.
- **OC1C-105** Confirm brand colors only (no orange/purple
  stock). Proof: the palette check in OC1C-splash-check.md.
- **OC1C-106** Record splash show duration.
  Proof: os-build/logs/OC1C-splash-time.txt.
- **OC1C-107** Confirm splash hands off to greeter cleanly.
  Proof: the transition note in OC1C-splash-time.txt.
- **OC1C-108** Confirm no Plymouth errors in the log.
  Proof: the log grep in OC1C-splash-time.txt.
- **OC1C-109** Compare against the mockup render.
  Proof: os-build/logs/OC1C-splash-vs-mock.md.
- **OC1C-110** File deviations with severity.
  Proof: the list in OC1C-splash-vs-mock.md.
- **OC1C-111** Confirm the greeter background matches the
  desktop wallpaper family. Proof:
  os-build/logs/OC1C-bg-family.md.
- **OC1C-112** Record the wallpaper set shipped.
  Proof: os-build/logs/OC1C-wallpapers.md.
- **OC1C-113** Confirm the live ASCII background moves.
  Proof: os-build/logs/OC1C-livebg.md.
- **OC1C-114** Confirm the live background costs <5% CPU.
  Proof: the measurement in OC1C-livebg.md.
- **OC1C-115** Confirm the fallback static wallpaper works
  when the live one is off. Proof:
  os-build/logs/OC1C-wallpaper-fallback.txt.
- **OC1C-116** Write the §5 verdict. Proof: the verdict block
  in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-117** File every splash defect with repro steps.
  Proof: os-build/logs/OC1C-splash-defects.md (empty is a result).
- **OC1C-118** Record the splash theme file inventory.
  Proof: os-build/logs/OC1C-splash-files.md.
- **OC1C-119** Confirm all splash assets are original.
  Proof: the provenance audit in OC1C-splash-files.md.
- **OC1C-120** Hand splash issues to the theme lane.
  Proof: os-build/logs/OC1C-splash-handoff.md.
- **OC1C-121** Confirm the boot menu shows MetaOS entries.
  Proof: os-build/logs/OC1C-grub-menu.md.
- **OC1C-122** Confirm no "Xubuntu" in the boot menu.
  Proof: the string check in OC1C-grub-menu.md.
- **OC1C-123** Confirm the .disk/info says MetaOS.
  Proof: os-build/logs/OC1C-diskinfo.txt.
- **OC1C-124** Confirm the volume label is Meta.
  Proof: os-build/logs/OC1C-vollabel.txt.
- **OC1C-125** Commit the §5 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §6 Theme completion verification (OC1C-126..OC1C-150)

- **OC1C-126** Verify Plank theme loads with Meta colors.
  Proof: os-build/logs/OC1C-plank.md.
- **OC1C-127** Verify GTK theme applies to apps.
  Proof: os-build/logs/OC1C-gtk.md.
- **OC1C-128** Verify the icon recolor landed.
  Proof: os-build/logs/OC1C-icons.md.
- **OC1C-129** Spot-check 10 icons for the recolor.
  Proof: the checklist in OC1C-icons.md.
- **OC1C-130** Confirm no un-recolored blue folders.
  Proof: the sweep in OC1C-icons.md.
- **OC1C-131** Verify the terminal profile + welcome hook.
  Proof: os-build/logs/OC1C-term-theme.md.
- **OC1C-132** Verify the Inter font is default.
  Proof: os-build/logs/OC1C-fonts.md.
- **OC1C-133** Verify the desktop layout matches the plan.
  Proof: os-build/captures/oc1c-desktop-final.png.
- **OC1C-134** Confirm panel, dock, launcher all themed.
  Proof: the visual checklist in
  os-build/logs/OC1C-desktop-check.md.
- **OC1C-135** Confirm no unstyled default widgets.
  Proof the sweep in OC1C-desktop-check.md.
- **OC1C-136** Write the §6 verdict. Proof: the verdict block
  in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-137** File every theme defect with repro steps.
  Proof: os-build/logs/OC1C-theme-defects.md (empty is a result).
- **OC1C-138** Hand theme issues to the theme lane.
  Proof: os-build/logs/OC1C-theme-handoff.md.
- **OC1C-139** Confirm greeter matches desktop theme.
  Proof: os-build/logs/OC1C-theme-match.md.
- **OC1C-140** Confirm lock screen matches too.
  Proof: the check in OC1C-theme-match.md.
- **OC1C-141** Record the theme file inventory.
  Proof: os-build/logs/OC1C-theme-files.md.
- **OC1C-142** Confirm all theme assets are original.
  Proof: the provenance audit in OC1C-theme-files.md.
- **OC1C-143** Record the wallpaper cycler behaviour.
  Proof: os-build/logs/OC1C-wallpaper-cycle.md.
- **OC1C-144** Confirm static fallback works.
  Proof: the fallback test in OC1C-wallpaper-cycle.md.
- **OC1C-145** Record font rendering verdict.
  Proof: os-build/logs/OC1C-font-render.md.
- **OC1C-146** Confirm no tofu/missing glyphs in UI.
  Proof: the sweep in OC1C-font-render.md.
- **OC1C-147** Write the desktop readiness verdict.
  Proof: os-build/logs/OC1C-desktop-ready.md.
- **OC1C-148** List desktop gaps with owners.
  Proof: the gaps in OC1C-desktop-ready.md.
- **OC1C-149** Confirm the desktop is usable for 10 minutes
  straight. Proof: os-build/logs/OC1C-desktop-10min.md.
- **OC1C-150** Commit the §6 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §7 Welcome app verification (OC1C-151..OC1C-175)

- **OC1C-151** Confirm the welcome app autostarts once.
  Proof: os-build/logs/OC1C-welcome-autostart.txt.
- **OC1C-152** Confirm it does NOT autostart twice.
  Proof: the flag check in OC1C-welcome-autostart.txt.
- **OC1C-153** Open it from the menu and confirm it runs.
  Proof: os-build/logs/OC1C-welcome-open.md.
- **OC1C-154** Screenshot the welcome window.
  Proof: os-build/captures/oc1c-welcome.png.
- **OC1C-155** Confirm Meta branding, no foreign assets.
  Proof: the visual check in OC1C-welcome-open.md.
- **OC1C-156** Click each of the 4 quick-launch buttons.
  Proof: os-build/logs/OC1C-welcome-launch.md.
- **OC1C-157** Confirm each opens the right app.
  Proof: the results in OC1C-welcome-launch.md.
- **OC1C-158** Confirm metafetch output shows when available.
  Proof: os-build/logs/OC1C-welcome-metafetch.txt.
- **OC1C-159** Confirm graceful behaviour without node.
  Proof: the missing-node test in OC1C-welcome-metafetch.txt.
- **OC1C-160** Confirm no traceback in any path.
  Proof: the log sweep in OC1C-welcome-metafetch.txt.
- **OC1C-161** Write the §7 verdict. Proof: the verdict block
  in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-162** File every welcome-app defect with repro steps.
  Proof: os-build/logs/OC1C-welcome-defects.md (empty is a result).
- **OC1C-163** Hand welcome-app issues to its owner.
  Proof: os-build/logs/OC1C-welcome-handoff.md.
- **OC1C-164** Confirm the welcome app closes cleanly.
  Proof: os-build/logs/OC1C-welcome-close.txt.
- **OC1C-165** Confirm closing it doesn't kill the session.
  Proof: the check in OC1C-welcome-close.txt.
- **OC1C-166** Confirm it respects dark theme.
  Proof: os-build/logs/OC1C-welcome-theme.txt.
- **OC1C-167** Confirm its text is honest (no overclaim).
  Proof: the copy audit in os-build/logs/OC1C-welcome-copy.md.
- **OC1C-168** Fix or file any overclaim found.
  Proof: the disposition in OC1C-welcome-copy.md.
- **OC1C-169** Confirm the .desktop entry validates.
  Proof: os-build/logs/OC1C-welcome-desktop.txt.
- **OC1C-170** Confirm TryExec guards the entry.
  Proof: the check in OC1C-welcome-desktop.txt.
- **OC1C-171** Re-run its 30 unit tests on the live system.
  Proof: os-build/logs/OC1C-welcome-unittests.txt.
- **OC1C-172** Confirm all 30 still pass.
  Proof: the count line in OC1C-welcome-unittests.txt.
- **OC1C-173** Hand unit-test failures to its owner.
  Proof: os-build/logs/OC1C-welcome-unittests-handoff.md.
- **OC1C-174** Record welcome-app resource use.
  Proof: os-build/logs/OC1C-welcome-resources.txt.
- **OC1C-175** Commit the §7 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §8 Imperium app verification (OC1C-176..OC1C-200)

- **OC1C-176** Launch Imperium from the dock/menu.
  Proof: os-build/logs/OC1C-app-launch.txt.
- **OC1C-177** Confirm its window opens with the command view.
  Proof: os-build/captures/oc1c-app-open.png.
- **OC1C-178** Confirm the backend spawned on 127.0.0.1.
  Proof: os-build/logs/OC1C-app-backend.txt.
- **OC1C-179** Confirm NOTHING listens on non-loopback for it.
  Proof: the ss output in OC1C-app-backend.txt.
- **OC1C-180** Confirm no browser chrome/user-data prompts.
  Proof: the visual check in OC1C-app-launch.txt.
- **OC1C-181** Run 'status' in the app's backend log.
  Proof: os-build/logs/OC1C-app-status.txt.
- **OC1C-182** Assess one staged frame.
  Proof: os-build/logs/OC1C-app-assess.json.
- **OC1C-183** Confirm the receipt is loopback-only.
  Proof: the dispatch URL in OC1C-app-assess.json.
- **OC1C-184** Confirm the 975-list loads in-app.
  Proof: os-build/logs/OC1C-app-list.txt.
- **OC1C-185** Confirm a file:// quirk breaks nothing.
  Proof: os-build/logs/OC1C-app-fileurl.md.
- **OC1C-186** List every file:// deviation found.
  Proof: the list in OC1C-app-fileurl.md.
- **OC1C-187** Fix or file each deviation.
  Proof: the dispositions in OC1C-app-fileurl.md.
- **OC1C-188** Confirm the app survives backend restart.
  Proof: os-build/logs/OC1C-app-restart.txt.
- **OC1C-189** Confirm closing the app stops its backend.
  Proof: os-build/logs/OC1C-app-close.txt.
- **OC1C-190** Confirm no orphan node processes remain.
  Proof: the ps check in OC1C-app-close.txt.
- **OC1C-191** Re-run the app's server unit tests.
  Proof: os-build/logs/OC1C-app-unittests.txt.
- **OC1C-192** Confirm all still pass.
  Proof: the count in OC1C-app-unittests.txt.
- **OC1C-193** Write the §8 verdict. Proof: the verdict block
  in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-194** File every Imperium-app defect with repro steps.
  Proof: os-build/logs/OC1C-app-defects.md (empty is a result).
- **OC1C-195** Hand app-code defects to their owners.
  Proof: os-build/logs/OC1C-app-handoff.md.
- **OC1C-196** Confirm the app icon renders in dock+menu.
  Proof: os-build/logs/OC1C-app-icon.txt.
- **OC1C-197** Confirm the app window is resizable.
  Proof: os-build/logs/OC1C-app-window.md.
- **OC1C-198** Confirm the app survives display sleep/wake.
  Proof: os-build/logs/OC1C-app-sleep.md.
- **OC1C-199** Record app resource use.
  Proof: os-build/logs/OC1C-app-resources.txt.
- **OC1C-200** Commit the §8 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §9 Installer verification (OC1C-201..OC1C-225)

- **OC1C-201** Boot the installer entry.
  Proof: os-build/logs/OC1C-inst-boot.txt.
- **OC1C-202** Screenshot the installer welcome.
  Proof: os-build/captures/oc1c-inst-welcome.png.
- **OC1C-203** Walk every installer page.
  Proof: os-build/logs/OC1C-inst-walk.md.
- **OC1C-204** Confirm Calamares branding is Meta throughout.
  Proof: the string check in OC1C-inst-walk.md.
- **OC1C-205** Confirm the slideshow renders.
  Proof: os-build/captures/oc1c-inst-slideshow.png.
- **OC1C-206** Confirm all 5 slides advance.
  Proof: the slide check in OC1C-inst-slideshow.png's log.
- **OC1C-207** Confirm no Ubuntu strings in the installer.
  Proof: the string sweep in os-build/logs/OC1C-inst-brand.txt.
- **OC1C-208** Record remaining strings with owners/fixes.
  Proof: the list in OC1C-inst-brand.txt.
- **OC1C-209** Run a full install to a blank virtual disk.
  Proof: os-build/logs/OC1C-inst-run.txt.
- **OC1C-210** Record install duration.
  Proof: the timing in OC1C-inst-run.txt.
- **OC1C-211** Confirm install completes with 0 errors.
  Proof: the result line in OC1C-inst-run.txt.
- **OC1C-212** Boot the installed system.
  Proof: os-build/logs/OC1C-installed-boot.txt.
- **OC1C-213** Screenshot the installed desktop.
  Proof: os-build/captures/oc1c-installed.png.
- **OC1C-214** Confirm autologin/users per install choices.
  Proof: os-build/logs/OC1C-installed-users.txt.
- **OC1C-215** Confirm apps present on the installed system.
  Proof: os-build/logs/OC1C-installed-apps.md.
- **OC1C-216** Confirm settings persist across the install.
  Proof: os-build/logs/OC1C-installed-persist.txt.
- **OC1C-217** Write the installer verdict: WORKS or BLOCKED.
  Proof: os-build/logs/OC1C-inst-verdict.md.
- **OC1C-218** If BLOCKED: name the exact failing step.
  Proof: the step in OC1C-inst-verdict.md.
- **OC1C-219** If BLOCKED: name the owner of the fix.
  Proof: the owner in OC1C-inst-verdict.md.
- **OC1C-220** Confirm the installed system updates cleanly.
  Proof: os-build/logs/OC1C-installed-update.txt.
- **OC1C-221** Write the §9 verdict. Proof: the verdict block
  in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-222** File every installer defect with repro steps.
  Proof: os-build/logs/OC1C-inst-defects.md.
- **OC1C-223** Hand installer defects to Buffy in writing.
  Proof: os-build/logs/OC1C-inst-handoff.md.
- **OC1C-224** Confirm the installed system shuts down clean.
  Proof: os-build/logs/OC1C-installed-shutdown.txt.
- **OC1C-225** Commit the §9 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §10 Post-boot system checks (OC1C-226..OC1C-250)

- **OC1C-226** Confirm network comes up (or honest absence).
  Proof: os-build/logs/OC1C-net.md.
- **OC1C-227** Confirm sound stack state.
  Proof: os-build/logs/OC1C-audio.md.
- **OC1C-228** Confirm USB/removable media handling.
  Proof: os-build/logs/OC1C-usb.md.
- **OC1C-229** Run the closeout node suite on the ISO tree.
  Proof: os-build/logs/OC1C-closeout-node.txt.
- **OC1C-230** Confirm 2071/2015/56 matches the settled set.
  Proof: the count line in OC1C-closeout-node.txt.
- **OC1C-231** Run the queue suite on the ISO tree.
  Proof: os-build/logs/OC1C-closeout-queue.txt.
- **OC1C-232** Confirm 296/296.
  Proof: the count line in OC1C-closeout-queue.txt.
- **OC1C-233** Run the lane gate one final time.
  Proof: os-build/logs/OC1C-closeout-gate.log.
- **OC1C-234** Confirm GATE GREEN.
  Proof: the GREEN line in OC1C-closeout-gate.log.
- **OC1C-235** Index every proof this 300-list committed.
  Proof: os-build/logs/OC1C-proof-index.md.
- **OC1C-236** Verify every proof path resolves.
  Proof: the check in OC1C-proof-index.md.
- **OC1C-237** Confirm no secrets anywhere in the branch.
  Proof: os-build/logs/OC1C-closeout-secrets.txt.
- **OC1C-238** Confirm os-release/inxi say MetaOS.
  Proof: os-build/logs/OC1C-identity.txt.
- **OC1C-239** Grep the live system for "Xubuntu" remnants.
  Proof: os-build/logs/OC1C-noxubuntu.txt.
- **OC1C-240** File remnants with owners/fixes.
  Proof: the list in OC1C-noxubuntu.txt.
- **OC1C-241** Grep for Ubuntu trademark strings.
  Proof: os-build/logs/OC1C-notm.txt.
- **OC1C-242** Grep for Apple strings.
  Proof: os-build/logs/OC1C-noapple.txt.
- **OC1C-243** Confirm all greps are clean or named.
  Proof: the verdicts in the three sweep files.
- **OC1C-244** Record uptime/stability of the test session.
  Proof: os-build/logs/OC1C-uptime.txt.
- **OC1C-245** Record memory/disk headroom.
  Proof: os-build/logs/OC1C-headroom.txt.
- **OC1C-246** Confirm logs rotate and don't fill disk.
  Proof: os-build/logs/OC1C-logrotate.txt.
- **OC1C-247** Write the §10 verdict. Proof: the verdict block
  in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-248** File every system defect with repro steps.
  Proof: os-build/logs/OC1C-system-defects.md (empty is a result).
- **OC1C-249** Confirm one reboot keeps everything working.
  Proof: os-build/logs/OC1C-reboot.txt.
- **OC1C-250** Commit the §10 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §11 Release packaging (OC1C-251..OC1C-275)

- **OC1C-251** Write the release notes.
  Proof: os-build/logs/OC1C-release-notes.md.
- **OC1C-252** List known issues honestly.
  Proof: the issues in OC1C-release-notes.md.
- **OC1C-253** Record the ISO sha256 + size.
  Proof: os-build/logs/OC1C-release-sha.txt.
- **OC1C-254** Record the build inputs (tree + pipeline commit).
  Proof: os-build/logs/OC1C-release-inputs.md.
- **OC1C-255** Write the install guide (USB + VM).
  Proof: os-build/logs/OC1C-install-guide.md.
- **OC1C-256** Write the 60-second demo script.
  Proof: os-build/logs/OC1C-demo-60s.md.
- **OC1C-257** Record the boot video proof.
  Proof: os-build/logs/OC1C-bootvideo.md.
- **OC1C-258** Confirm the video shows login→desktop→app.
  Proof: the shot list in OC1C-bootvideo.md.
- **OC1C-259** Assemble the DEL-ONLY list.
  Proof: os-build/logs/OC1C-delonly.md.
- **OC1C-260** Write the timeline to the deadline.
  Proof: os-build/logs/OC1C-timeline.md.
- **OC1C-261** Record the claim-clause map.
  Proof: os-build/logs/OC1C-clauses.md.
- **OC1C-262** For every UNPROVEN clause: one-line reason.
  Proof: the reasons in OC1C-clauses.md.
- **OC1C-263** Assemble the Pax merge request.
  Proof: os-build/logs/OC1C-pr.md.
- **OC1C-264** List what merges and in what order.
  Proof: the list in OC1C-pr.md.
- **OC1C-265** List what must NOT merge.
  Proof: the exclusions in OC1C-pr.md.
- **OC1C-266** Confirm nothing in this lane touches main.
  Proof: the branch attestation in OC1C-pr.md.
- **OC1C-267** Post build status to room 1 as things land.
  Proof: the post log in OC1C-pr.md.
- **OC1C-268** Record where spare time went.
  Proof: the note in OC1C-pr.md.
- **OC1C-269** Record the honest readiness verdict.
  Proof: os-build/logs/OC1C-readiness.md.
- **OC1C-270** If NOT READY: named rows + owners.
  Proof: the rows in OC1C-readiness.md.
- **OC1C-271** Confirm the readiness matches Milo's audit.
  Proof: the cross-check in OC1C-readiness.md.
- **OC1C-272** Record the submission-day state.
  Proof: os-build/logs/OC1C-submit-state.md.
- **OC1C-273** Confirm Del-adopts-only items are marked.
  Proof: the marks in OC1C-submit-state.md.
- **OC1C-274** Write the §11 verdict. Proof: the verdict block
  in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-275** Commit the §11 artifacts. Proof: the commit sha
  recorded in os-build/OPENCODE1_ISO_STATUS.md.

## §12 Closeout (OC1C-276..OC1C-300)

- **OC1C-276** Final status-file pass: every section DONE or
  UNPROVEN with its reason — no silent gaps.
  Proof: the completed os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-277** Verify every proof path resolves.
  Proof: the check output in os-build/logs/OC1C-paths-ok.txt.
- **OC1C-278** Confirm the branch pushes clean.
  Proof: the push receipt in OC1C-paths-ok.txt.
- **OC1C-279** Record the list's total live spend.
  Proof: os-build/logs/OC1C-spend.md.
- **OC1C-280** Record total lane wall-clock by section.
  Proof: os-build/logs/OC1C-time.md.
- **OC1C-281** Confirm no mock presented as live.
  Proof: os-build/logs/OC1C-honest.md.
- **OC1C-282** Confirm no Apple/Ubuntu trademarks shipped.
  Proof: os-build/logs/OC1C-trademark.md.
- **OC1C-283** Confirm no secrets committed.
  Proof: os-build/logs/OC1C-nosecrets.txt.
- **OC1C-284** Confirm every BLOCKED has an owner.
  Proof: the audit in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-285** Confirm every UNPROVEN has a reason.
  Proof: the audit in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-286** Write the handoff to Pax.
  Proof: os-build/logs/OC1C-handoff.md.
- **OC1C-287** Write the handoff to the other lanes.
  Proof: os-build/logs/OC1C-handoff-lanes.md.
- **OC1C-288** Post final build status to room 1.
  Proof: the post log in OC1C-handoff.md.
- **OC1C-289** Record what remains unproven in plain words.
  Proof: os-build/logs/OC1C-remaining.md.
- **OC1C-290** Confirm the ISO boots from a cold start.
  Proof: os-build/logs/OC1C-coldboot.txt.
- **OC1C-291** Confirm the installed system boots.
  Proof: os-build/logs/OC1C-coldboot-installed.txt.
- **OC1C-292** Record the final gate state.
  Proof: os-build/logs/OC1C-final-gate.txt.
- **OC1C-293** Record the final suite states.
  Proof: os-build/logs/OC1C-final-suites.txt.
- **OC1C-294** Assemble the DEL-ONLY list.
  Proof: os-build/logs/OC1C-delonly.md.
- **OC1C-295** Final commit on opencode1/boot-installer.
  Proof: the commit sha in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-296** The last line of the status file: one line on
  what this 300 proved. Proof: the final line.
- **OC1C-297** Confirm the theme branch merged its part.
  Proof: the merge sha in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-298** Confirm OC2/OC3 lanes filed their verdicts.
  Proof: the refs in os-build/OPENCODE1_ISO_STATUS.md.
- **OC1C-299** Confirm Pax's merge order in writing.
  Proof: os-build/logs/OC1C-merge-order.md.
- **OC1C-300** Close the lane. Proof: the word DONE with the
  date in os-build/OPENCODE1_ISO_STATUS.md.
