# OC1B carrier checks (tasks 284-290, 296-297)

Image: /tmp/oc1b-carrier3/metaos-face.img (build-local, never git),
booted with the recipe's boot line (`-cpu max`, seed.iso, user-net,
hostfwd :2224). Boot log: os-build/logs/OC1B-carrier-boot.txt
(883 lines; cloud-init finished, datasource NoCloud).
SSH: build-local face-key, relay@127.0.0.1:2224.

## Standing check 1 — autologin on tty1 (OC1B-284): PASS

  ActiveState=active / SubState=running (getty@tty1.service)
  who: relay tty1 2026-11-02 12:26

## Standing check 2 — DHCP address in the guest (OC1B-285): PASS

  inet 10.0.2.15/24 metric 100 brd 10.0.2.255 scope global dynamic ens3

## Standing check 3 — dashboard HTTP 200 with live facts (OC1B-286): FAILED

No dashboard to curl. The rebuilt image carries no face stack:
  ls /opt/face -> ls: cannot access '/opt/face': No such file or directory
  systemctl is-active facts rooms trash -> inactive / inactive / inactive
  ss -ltn | grep 1893 -> (no listeners)
The face app lives only in the dev work.qcow2 guest; the recipe (before
and after this section) provisions the OS toolchain, not /opt/face.
Recorded as a named failure, not a skipped row.

## Standing check 4 — passive updater pull cycle (OC1B-287): FAILED

No updater exists in the rebuilt image (same cause as check 3: the
updater is part of the face deploy, not the recipe). Recorded as a named
failure, not a skipped row.

## Toolchain versions in the guest

OC1B-288: opencode --version -> opencode v2.2.0 (pinned, `command -v`
/usr/local/bin/opencode). PASS.
OC1B-289:
  node --version -> v18.20.4
  git --version -> git version 2.39.5
  chromium --version -> Chromium 156.0.8078.73 built on Debian GNU/Linux 12 (bookworm)
All three recorded verbatim from the guest. PASS.

## Kiosk/face starts (OC1B-290): NOT PRESENT

/opt/face does not exist in the rebuilt image, so no kiosk starts. This
checks the app's presence/startup and builds nothing on it — result: the
carrier ships the OS toolchain, not the face app. If a future recipe
deploys /opt/face, this check re-runs against it.

## Hardware/UTM boot (OC1B-296): UNPROVEN

`utmctl list` on this Mac: header only, zero VMs registered. No hardware
or UTM boot of this image was attempted; QEMU proof never stands in for
hardware. The recipe's boot line is QEMU-only.

## Failures block (OC1B-297)

- OC1B-286 dashboard check: FAILED (no /opt/face, no 1893 listeners).
- OC1B-287 updater check: FAILED (no updater in image).
- OC1B-290 kiosk starts: NOT PRESENT (no /opt/face).
- Recipe-iteration failures that drove fixes (all in build log):
  (a) v1 installer refused 2.2.0 -> switched to v2 installer URL;
  (b) installer target ~/.local/bin wrong (real: ~/.opencode/bin) ->
      detect-and-link + `command -v` verify;
  (c) SIGILL running opencode under default qemu64 CPU (needs AVX2) ->
      `-cpu max` on provision + documented boot lines, proven by
      opencode v2.2.0 rc=0 under -cpu max;
  (d) npm global without sudo -> EACCES -> sudo in recipe (freebuff then
      installed and ran: 0.2.35).
No check was silently skipped; passes and failures alike name their evidence.
