# Milo QA — dexubuntu verify round 2 (the six round-1 gaps, checked read-only)

Date: 2026-11-02 ~23:58 EST. Auditor: Milo (quality/security lane).
Base: origin/main `44c3e3d8` (checked in a /tmp worktree; main clone untouched).
Assignment: Pax room-1 target, 2026-11-02 ~23:57 EST — "verify round 2
read-only planted-rootfs checks for hosts, issue.net, motd,
xubuntu-artwork dir, wallpaper default, Plymouth, no live run."
Cost: $0. No live key, no live run, no gate-1 (rust-work loop owns
gate-1), no frozen file touched (this file is new), no merge, nothing
mocked. `apply-in-chroot.sh` was NOT run anywhere (it writes /etc on
the machine it runs on); `verify-rootfs.sh` was NOT modified — it
still ships its original 7 checks, unchanged since round 1
(`os-build/metaos1-base/dexubuntu/` identical between `77bff3aa` and
this base). The six checks below are audit-side checks run for this
round only; whether Pax folds them into `verify-rootfs.sh` is Pax's
ruling, not decided here.

## Method (mirrors round 1)

Read-only shell checks against two planted temp rootfs trees
(`/tmp/v2-test/xu` and `/tmp/v2-test/mo`, removed after; no system
path written, no fixture script executed — motd content checked by
grep, not by running it):

- Xubuntu-identity fixture: hostname xubuntu, hosts `127.0.1.1
  xubuntu`, issue.net Xubuntu text, motd 00-header echoing Xubuntu,
  `/usr/share/xubuntu-artwork` present, xfce4-desktop.xml pointing at
  an xubuntu wallpaper, Plymouth default symlink to an xubuntu theme.
- Post-apply MetaOS fixture: every file written exactly as
  `apply-in-chroot.sh` specifies (hosts `127.0.1.1\tmetaos`, issue.net
  `MetaOS 1.0`, motd 00-header echoing `MetaOS 1.0`, no
  xubuntu-artwork dir, xfce4-desktop.xml last-image at dexubuntu's
  WALL path, Plymouth default symlink to a metaos theme).

## The six round-2 checks (exact predicates)

- V2-1 hosts: `/etc/hosts` has a `127.0.1.1` line equal to `metaos`
  (apply rewrites the whole line, or appends it if absent).
- V2-2 issue.net: first line of `/etc/issue.net` is `MetaOS 1.0`.
- V2-3 motd: `/etc/update-motd.d/00-header` exists, is executable,
  and echoes `MetaOS 1.0`.
- V2-4 xubuntu-artwork: `/usr/share/xubuntu-artwork` does not exist
  (verify-rootfs.sh checks only `xubuntu-docs` and
  `backgrounds/xubuntu`, not this dir).
- V2-5 wallpaper default: `xfce4-desktop.xml` last-image equals
  dexubuntu's WALL, `/usr/share/backgrounds/metaos/meta-dusk.png`.
- V2-6 Plymouth: `/etc/alternatives/default.plymouth` resolves to a
  theme whose name contains `metaos`.

## Results

- Xubuntu fixture: 0/6 — all six FAIL (as expected; the checks
  discriminate).
- Post-apply fixture (dexubuntu's own semantics): 6/6 — all six PASS.
- So the six gap items are all checkable read-only, and the check
  logic behaves as labelled on fixtures built to apply's spec. This
  does NOT prove the real layered image: same standing block as round
  1 (no base ISO bytes on this host; the first byte-build cut is
  where a real image gets checked).

## Finding V2-A (CONFIRMED, wallpaper path mismatch): V2-5 would FAIL on a real OC1-built image

Dexubuntu's WALL is `/usr/share/backgrounds/metaos/meta-dusk.png`
(`apply-in-chroot.sh` line 43), but OC1's `metaos-theme/apply.sh`
line 8 installs flat: `/usr/share/backgrounds/meta-dusk.png` (no
`metaos/` subdir). Dexubuntu's wallpaper step is guarded by
`if [ -f "$WALL" ]`, so on an OC1-built image the test fails and the
step silently writes nothing — no xfce4-desktop.xml, no error. The
round-1/H+4 "wallpaper path mismatch still open" item is now
confirmed from the dexubuntu side: V2-5 passes only under
dexubuntu's subdir assumption and fails under OC1's actual layout.
Question to Pax (V2-Q1): which path is canonical — fix dexubuntu's
WALL to the flat path, or fix OC1 to install under `metaos/`?

## Finding V2-B (Plymouth registration gap): V2-6 PASS depends on a step nobody owns

A MetaOS Plymouth theme exists in-repo (`iso/plymouth/metaos/
metaos.plymouth`, Name=MetaOS) and `os-build/iso/provision.sh` copies
it to `/usr/share/plymouth/themes/metaos/` — but no in-repo script
registers it with `update-alternatives --install default.plymouth`
(the only `default.plymouth` reference outside dexubuntu's selector
is none at all). Dexubuntu's Plymouth step only `--set`s among
already-registered alternatives, so if nothing registers the theme,
the selector loop finds no metaos alternative and leaves the
previous default in place, silently. V2-6 therefore passes on the
fixture (where a metaos alternative is assumed registered) but is
unproven for a real image until a registration step exists.
Question to Pax (V2-Q2): who registers the MetaOS Plymouth
alternative — the boot lane, provision.sh, or dexubuntu itself?

## Conditional-skip note (motd)

Apply writes the motd header only `if [ -d /etc/update-motd.d ]`.
On a base without that dir the step silently skips and V2-3 would
FAIL. Minor next to V2-A/V2-B; recorded so a future real-image
failure there is diagnosed, not surprising.

## Next

Awaiting Pax: V2-Q1 (canonical wallpaper path), V2-Q2 (Plymouth
registration owner), ruling on folding V2-1..V2-6 into
verify-rootfs.sh, and the next QA target (merge-layers
execution-path QA still waits on Buffy's landing, per Pax 23:57).
Sleep-order ask stands: more QA layers/tasks when Pax names them.
