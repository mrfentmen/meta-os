# OC2B-151/152/153 — OpenCode bake-in install record (this lane, 2026-11-02)

Guest: Debian 12 (lane base image), QEMU `-cpu max` (REQUIRED — see below).
- Install commands (exact): `curl -fsSL https://opencode.ai/install | bash` (curl present at /usr/bin/curl; git/node absent pristine).
- First `opencode --version` on default QEMU cpu: `Illegal instruction` (exit 471) — binary needs CPU flags qemu64 lacks. Rebooted guest with `-cpu max` → `opencode --version` = **1.19.5**. No manual install step involved beyond the official script.
- Smoke (OC2B-153): `echo "say OK" | timeout 150 opencode run -m opencode/space-bunny-free "say OK" < /dev/null` → wall 41.7s → `UnknownError: Unexpected server error ... ref err_7c808c65`. No reply text (endpoint-side failure, one attempt, no retry).
- OC2B-168: install itself succeeded; no license/size/install blocker. Model-endpoint failures are recorded, not install failures.
