# Wave2 Section 4 — Tasks 31-40 Findings

Date (UTC): 2026-11-02
Host: darwin (/Users/test)

## 1. UTM availability (`utmctl list`)
- `utmctl` present at `/opt/homebrew/bin/utmctl`
- `utmctl list` output: header only (`UUID Status Name`), zero rows — no VMs registered/visible via utmctl.
- `utmctl status` without identifier errors as expected (requires UUID/name).
- Guest still reachable via SSH (see §2), so VM is running outside utmctl registry (likely direct qemu).

## 2. Guest services via `ssh -i /tmp/face-img/face-key -p 2222 relay@127.0.0.1`
- SSH: OK (ED25519 host key, `StrictHostKeyChecking=no`).
- `curl localhost:18932` (facts): OK → `{"cpu":"load 1.93","mem":"615M / 1967M","disk":"3G / 14G","net":"10.0.2.15/24"}`
- `curl localhost:18935` (rooms): OK → `{"ok":true,"rooms":["announce","general","random"]}`
- `curl localhost:18936` (trash): OK → `{"ok":true,"entries":[]}`
- `systemctl --user is-active facts rooms trash`: all `inactive` — services not under user systemd.
- `ss -ltn | grep 1893`: LISTEN on 127.0.0.1:18931,18932,18933,18934,18935,18936 — running via other supervisor/manual.

## 3. Toolchain presence
- `node -v`: `v24.21.0` (`/Users/test/.local/node/bin/node`, `/opt/homebrew/bin/node`)
- `npm`: present (`/Users/test/.local/node/bin/npm`)
- `git --version`: `git version 2.54.0 (Apple Git-157)` (`/usr/bin/git`)
- `chromium` / `chromium-browser` / `google-chrome`: NOT found in PATH.
- Extras: `python3` (`/usr/bin/python3`), `qemu-img` (`/opt/homebrew/bin/qemu-img`) present.

## 4. Image files in `/tmp/face-img`
- `debian-12-generic-amd64.qcow2` — 428M — QEMU QCOW2 v3, virtual 3 GiB (base cloud image)
- `metaos-face.img` — 428M — QEMU QCOW2 v3, virtual 13 GiB (13958643712 B)
- `work.qcow2` — 4.3G — QEMU QCOW2 v3, virtual 15 GiB (16106127360 B)
- `seed.iso` — 900K — ISO 9660 `CIDATA` (cloud-init seed)
- `seed/` — dir (cloud-init source)
- `face-key` (411B, 0600) + `face-key.pub` (100B) — SSH key for `relay@127.0.0.1:2222`
- Logs: `face-boot1.txt` (70K), `face-boot2.txt` (63K), `face-boot3.txt` (34K), `fresh-boot.txt` (64K)
- `qemu-img info metaos-face.img`: `qcow2, 13G virtual / 428M disk, compat 1.1, zlib, not corrupt`
