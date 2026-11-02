# OC2B-156/157/167 — baked checkout + updater + toolchain (this lane, 2026-11-02)

- Checkout path: `/home/relay/bake/meta-os`, `git clone --depth 1 https://github.com/mrfentmen/meta-os.git` (28.9s, 246M). Tip at bake: `b0a66bf02e9e091a72a37e941c80a6d57ef61b66` (Merge Buffy Round 12). Full 805M history NOT cloned (shallow by design — recorded).
- `git` installed in guest for the bake: `sudo apt-get install -y git` → git 2.39.5.
- Updater: `/etc/systemd/system/oc2b-bake-pull.service` (oneshot, User=relay, `git pull --ff-only origin main`) + `.timer` (OnBootSec=5min, daily), daemon-reload, timer ENABLED (symlink verified). Redacted content: no secrets involved (public repo, no creds).
- Toolchain now in image: opencode 1.19.5, git 2.39.5, curl (present), python3 (present). node/chromium NOT installed (out of bake scope — recorded gap).
