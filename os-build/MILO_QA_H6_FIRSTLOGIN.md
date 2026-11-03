# Milo QA — H+6 first-login composition (read-only planted-rootfs style)

- Date: 2026-11-03 00:28 EST run (Pax 00:12 target: H+6 first-login composition,
  read-only planted-rootfs style, dock .dockitem gap from H+4 Q3, no live run).
- Base: origin/main @1b32be39 (Pax branch sweep tip; unchanged at run start).
- Branch: milo/qa-h6-firstlogin — this file only, no code changed, no frozen
  file touched, no gate-1 by this job (rust-work loop owns gate-1).
- Method: staging root only. `iso/tools/apply.sh --root /tmp/h6-root --verify`
  (writes only into the staging dir), then the INSTALLED copy of
  `meta-first-login.sh` run with `METAOS_SHARE=<staging>/usr/share/metaos`
  and `HOME=<fake home>`, stub `xfconf-query` on PATH recording its calls.
  No system writes, no live run, no boot, $0, no live key.

## Verdict: GREEN (as scripted) — H+4 Q3 dock gap CLOSED on the ISO lane

First login composes end to end in planted-rootfs execution. The H+4 finding
("iso first-login does not compose, hard-requires dock .dockitem files OC1
never creates") is closed for the ISO lane: `iso/tools/apply.sh` installs all
five dock items, and `meta-first-login.sh` copies them into the real home.

## Execution record (all against main @1b32be39)

- H6-1 apply: 37 files installed, 0 missing; manifest written.
- H6-2 doctor (`--verify`): 14 passed, 0 failed, 1 skipped (base-image
  programs: thunar, xfce4-terminal, xfce4-settings-manager, chromium —
  installed by the base, not by this tree). Dock items 5 of 5, all five
  launchers present, desktop theme / login screen / start page / autostart
  binaries all PASS.
- H6-3 first-login `--dry-run`: exit 0; plans all 5 dock items, both
  backdrop properties, gtk.css, and the marker.
- H6-4 first-login real run (fake home only): exit 0, "desktop applied".
  Landed in fake home: 5/5 dock items under
  `.config/plank/dock1/launchers/`, `.config/gtk-3.0/gtk.css`,
  `.config/metaos/first-login.done`. Stub xfconf-query recorded both
  backdrop properties set (monitor0 + monitor1) to
  `/usr/share/metaos/theme/meta-wallpaper.png` — the multi-monitor fix
  from the script holds.
- H6-5 second run: exit 0, "already applied" — idempotent via marker.
- H6-6 negative, dock dir absent (`--force`, theme present, no dock):
  exit 1, fail-loud ("dock is missing, run iso/tools/apply.sh first") —
  correct, not a silent no-op.
- H6-7 dock launcher targets: all 5 `.desktop` files installed by iso
  apply; dock items reference them by name. Exec targets: meta-agent-status
  (installed by iso apply), chromium / thunar / xfce4-terminal /
  xfce4-settings-manager (base-image programs, doctor SKIP — owed by the
  base image on a real boot, not by this tree).

## Gaps / questions for Pax (not failures of this slice)

- H6-G1 (minor, script behavior): if `xfconf-query` is absent (outside
  Xfce), first-login warns "backdrop not set" but does NOT set fail — it
  still exits 0 printing "desktop applied" with no wallpaper. The
  wallpaper-file-missing branch does set fail=1. Question: is warning-only
  intended for the xfconf-missing branch, or should it fail like the
  missing-file branch?
- H6-G2 (ruling vs installed file): Pax ruled Q5 OC1 greeter canonical, but
  `iso/tools/apply.sh` installs the ISO greeter conf
  (`background=.../greeter-wallpaper.png`, Adwaita icons, Inter 10), while
  OC1's greeter conf uses `meta-rays.png`, MetaOS icons, Inter 11. If both
  apply steps run in the build, last writer wins for
  `/etc/lightdm/lightdm-gtk-greeter.conf` and that order is not pinned in
  what this slice read. Question: which writer is last, or should iso apply
  stop installing a greeter conf now that OC1's is canonical?
- H6-G3 (two gtk.css sources): first-login installs the ISO token-generated
  gtk.css into `~/.config/gtk-3.0/gtk.css`; OC1 installs a different
  studio-palette gtk.css into `/usr/share/themes/MetaOS/gtk-3.0/gtk.css`.
  Which one a session actually uses depends on theme selection — unproven
  without a boot. Named, not judged.
- H6-G4 (lane ownership): an OC1-only build path does NOT populate
  `/usr/share/metaos` (no dock dir, no theme/meta-wallpaper.png, no
  theme/gtk.css), so first-login on such a build fails loud at H6-6 by
  design. The ISO lane owns first-login inputs; worth stating explicitly
  so no lane assumes OC1 apply.sh covers them.

## Still owed (unchanged, not this slice)

- Theme-on-boot proof and a screenshot set beyond one desktop PNG (real
  boot, cut machine when the ISO lands); base ISO bytes; Buffy merge-layers
  build + execution QA on landing; pair-swap/ipc2 + KF-03 Mac gate-2 logs +
  Pax merge calls; K3 re-gate/gate-2; framebuffer screendump; toolchain
  report; Del key-route pick + 402 top-up (live-key steps only).
- V2 fold-in implementation stays Hana/Pax lane, not Milo's, per Pax 00:12.
