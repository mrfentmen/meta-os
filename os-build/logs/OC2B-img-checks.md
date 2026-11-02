# OC2B-img checks — Section 6 verification evidence (OC2B-131–142)

Image under test: `/tmp/oc2b-img-build/metaos-face.img` rebuilt 2026-11-02 with lane script
`os-build/face/build-image.sh` (sha `f7d8581e…`, full in `OC2B-img-status.md`).
Boots below run on scratch copy `/tmp/oc2b-img/oc2b-work.qcow2` + test seed (`instance-id metaos-oc2b-02`,
relay `ssh_authorized_keys` nested under the user — top-level placement is ignored by cloud-init,
found during this lane).
QEMU: `qemu-system-x86_64 --version` → 11.1.3 (see `OC2B-img-section6.md` for full cmdline).

## OC2B-131 autologin — YES

- `/etc/systemd/system/getty@tty1.service.d/autologin.conf` contains
  `ExecStart=-/sbin/agetty --autologin relay --noclear %I $TERM`.
- `who` → `relay tty1 2026-11-02 11:14`; `systemctl is-active getty@tty1.service` → `active`.
- Screendump `OC2B-img-desktop.png` shows `metaos login: relay (automatic login)` then `relay@metaos:~$`.
- No credentials typed at any point (SSH key injected via seed).

## OC2B-132 DHCP — IP 10.0.2.15/24

Command: `ip -4 addr show ens3` (+ `ip route get 8.8.8.8`):
- `inet 10.0.2.15/24 metric 100 brd 10.0.2.255 scope global dynamic ens3` (`valid_lft 86346sec`).
- Default `8.8.8.8 via 10.0.2.2 dev ens3 src 10.0.2.15`. QEMU user-net supplies DHCP; lease is dynamic.

## OC2B-133 network egress — HTTP 200

- `curl https://example.com` → `http=200 time=0.83s`.
- `curl https://cloud.debian.org/` → `http=301 time=1.00s`.
- Egress works through QEMU user-net NAT with no guest proxy config.

## OC2B-134 dashboard HTTP from inside — HTTP 200

Pristine build output ships NO dashboard (it is a face-provisioned service, not part of
`build-image.sh`). Staged lane files `os-build/face/dashboard.html` + `os-build/face/facts.py`
to `~/oc2b-face/` and ran them (stdlib `http.server` 18900, facts 18932):
- `curl http://127.0.0.1:18900/dashboard.html` → `http=200`.
- `curl http://127.0.0.1:18932/facts` → `{"cpu": "load 1.10", "mem": "233M / 1967M", "disk": "1G / 12G", "net": "10.0.2.15/24"}` (live guest numbers).

## OC2B-135 dashboard from host browser — HTTP 200 via forwarded port

- QMP runtime `hostfwd_add`: `CommandNotFound` on QEMU 11.1.3 (recorded blocker for the
  no-reboot path — forwarding must be declared at startup).
- Rebooted with `-net user,hostfwd=tcp::2223-:22,hostfwd=tcp::18909-:18900`
  (`info usernet` confirms `TCP[HOST_FORWARD] * 18909 → 10.0.2.15 18900`).
  Lesson: slirp forwards to the guest IP, so the guest server must bind `0.0.0.0`, not loopback.
- `curl http://127.0.0.1:18909/dashboard.html` from the Mac → `http=200`, dashboard HTML body.
  (Host port 18901 was already taken by another lane's server; 18909 used instead.)

## OC2B-136 boot timing — first-boot ~178s, steady-state ~64s

- Boot 1 (seed v1, cloud-init full run): `cloud-init finished … Up 94.13 seconds`.
- Boot 2 (seed v2, new instance-id → cloud-init re-ran): power-on 11:11:23 EST,
  `cloud-init finished … Up 93.20 seconds` (11:14:21 EST) → wall ≈ 178s; SSH ready ≈ 170s.
- Boot 3 (same seed, steady-state): power-on 11:15:33 EST, SSH ready 11:16:37 EST → **64s**.
- Face-lane reference (`image-status-2026-11-02.md`): 7.859s kernel + 55.221s userspace first boot.

## OC2B-137 idle memory — `free -m`

Pristine, 1 min uptime: `Mem: 1967 total, 212 used, 1758 free, 135 buff/cache, 1755 available; Swap: 0`.
(Lane reference: 1967M total, ~250M used.)

## OC2B-138 node / git / chromium — ABSENT from lane build output

- `which node git chromium` → all `command not found` (verified on boot 2).
- Lane reference (provisioned image, `image-status-2026-11-02.md`): node v18.20.4, git 2.39.5,
  chromium present — quoted, NOT re-verified on this lane's pristine output.
- Remediation in progress at write time: `apt-get install -y git chromium` running in guest
  (see `OC2B-oc-*.md` for outcome; blocks OC2B-139/156 until done).

## OC2B-139 face in chromium — BLOCKED at write time

chromium is not in the lane build output (see 138). apt install running; headless
screenshot (`chromium --headless --screenshot=… http://127.0.0.1:18900/dashboard.html`)
to follow if the install completes in-session, else recorded UNPROVEN in the verdict doc.

## OC2B-140 clock sync — 36s delta, guest fast, no NTP yet

- Guest `date -u` 16:14:34Z vs host `date -u` 16:13:58Z (boot 2, 1-min uptime): **+36s guest**.
- Re-check boot 3: guest 16:16:44Z vs host 16:16:44Z → **0s** (converged; systemd-timesyncd
  reached `deb.debian.org` NTP over the NAT — see `info usernet` UDP/123 flows).
- Verdict: SYNCED (after ~2 min uptime).

## OC2B-141 clean shutdown — 7s

`sudo poweroff` over SSH at 11:15:2x EST → QEMU process gone in **7s wall**.
Serial tail shows clean `Reached target System Power Off`. No fs errors on next boot.

## OC2B-142 second-boot autologin repeat — YES

Boot 3: `who` → `relay tty1 2026-11-02 11:16`; getty `active`; no typing.
`/tmp/oc2b-face` did NOT survive reboot (Debian clears `/tmp` — re-staged to `~/oc2b-face/`).
