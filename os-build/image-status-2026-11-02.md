# Image status 2026-11-02 — the four standing checks (face task 13)

Image: Debian 12 cloud base + NoCloud seed, grown to 15G.
Built by os-build/face/build-image.sh (recipe) + guest provisioning
over SSH. QEMU: `-m 2048 -drive file=work.qcow2 -cdrom seed.iso
-serial file -display none`.

## 1. Autologin — PROVEN
- `relay` autologs on tty1, no typing. Screendump:
  os-build/face/face-vga-autologin.png shows
  `metaos login: relay (automatic unit)` then `relay@metaos:~$`.
- Mechanism: cloud-init user-data installs a getty@tty1.service
  drop-in with `--autologin relay`.

## 2. DHCP — PROVEN
- `ip -4 addr show ens3`: `10.0.2.15/24 ... dynamic`,
  `default via 10.0.2.2 dev ens3 proto dhcp`. QEMU user-net
  supplies DHCP; the lease is dynamic and the route is learned,
  not static.

## 3. Dashboard HTTP — PROVEN
- `curl http://127.0.0.1:18900/dashboard.html` → 200.
- `curl http://127.0.0.1:18932/facts` →
  `{"cpu": "load 1.72", "mem": "655M / 1967M",
  "disk": "3G / 14G", "net": "10.0.2.15/24"}`
  (live numbers from this machine, not staged).

## 4. Updater pull — PROVEN
- Timer `metaos-update.timer` enabled (every 15 min + 5 min after
  boot). Screendump-equivalent: the unit files are in-repo at
  os-build/face/metaos-update.{sh,service,timer}.
- STOP file: `touch /etc/metaos/STOP` → next run logs
  `STOP present, skipping pull`; STOP removed after the drill.
- Real pull cycle 2026-11-02 ~08:40 UTC: two drill commits pushed
  to opencode/face, updater fetched, logged
  `pulling 476f549 -> 5f45ba6`, checked out `os-build/face`
  into /opt/face (UPDATE_DRILL3.txt present on disk), logged
  `applied face updates`. Full log: guest /var/log/metaos-update.log
  (relevant lines quoted in STATUS.md Section 2).
- Drill markers removed from the branch after proof (commit
  "remove updater drill markers").

## Machine facts (task 10 close-out)
- Hostname metaos, timezone America/New_York, locale en_US.UTF-8
  generated + /etc/default/locale set (was C.UTF-8 on stock image).
- Toolchain baked in: node v18.20.4, git 2.39.5
  (plus openbox, chromium, tint2, feh, pcmanfm, lxterminal,
  mousepad, orage, galculator, xdotool, xwd, netpbm for the face).
- Boot: 7.859s kernel + 55.221s userspace (first boot, includes
  cloud-init). Memory at idle: 1967M total, ~250M used.
