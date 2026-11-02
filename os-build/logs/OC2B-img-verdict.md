# OC2B-img verdict table — Section 6 (OC2B-143)

Source PARTIALs: `os-build/image-status-2026-11-02.md` names NO partial items (all four checks
PROVEN there); `os-build/face/image/JOIN.note` names none either. This table therefore verdicts
each §6 check against the FRESH rebuild (`f7d8581e…`, `OC2B-img-status.md`).

| Task | Check | Verdict on fresh build output | Evidence |
|---|---|---|---|
| 129 | Boot + serial log | PROVEN | `OC2B-img-boot1.md` (840-line serial, cloud-init finished Up 93.20s) |
| 130 | Desktop/login screendump | PROVEN | `OC2B-img-desktop.png` (relay autologin → shell) |
| 131 | Autologin | PROVEN (yes) | getty drop-in + `who` + active; no typing |
| 132 | DHCP | PROVEN (10.0.2.15/24 dynamic) | `ip -4 addr show ens3` + default via 10.0.2.2 |
| 133 | HTTPS egress | PROVEN (200) | example.com 200/0.83s; cloud.debian.org 301 |
| 134 | Dashboard HTTP (guest) | PROVEN (200 + live facts) | lane files staged to `~/oc2b-face/`; 18900/18932 answer |
| 135 | Dashboard from host | PROVEN (200 via :18909) | startup hostfwd; QMP runtime-add unsupported (noted) |
| 136 | Steady-state boot | PROVEN (64s vs ~178s first) | SSH-ready timings boot 2 vs boot 3 |
| 137 | Idle mem | PROVEN (1967M/212M used) | `free -m` |
| 138 | node/git/chromium | PARTIAL → install in flight | all absent from build output; lane ref quoted, not re-verified |
| 139 | Face in chromium | UNPROVEN at write time | chromium absent; apt install running — outcome in `OC2B-oc-verify.md` or gap list |
| 140 | Clock sync | PROVEN (0s by boot 3) | 36s fast at 1-min uptime → converged via NTP |
| 141 | Clean shutdown | PROVEN (7s) | `sudo poweroff` → process gone, clean serial tail |
| 142 | 2nd-boot autologin | PROVEN (yes) | boot 3 `who` + active |
| 144 | Build-script failure | NO FAILURE | nothing to flag for Pax |
| 148 | Fresh-shasum match | MATCH | `f7d8581ebb…3167c3` == recorded `f7d8581e…` prefix; byte-identical to 06:47 build |

UNPROVEN carried out of §6: OC2B-139 (face-in-chromium on the fresh build) pending the guest
apt install; OC2B-138 toolchain versions only quoted from the lane STATUS, not re-measured
on pristine output (by design — the lane script does not bake them in).
