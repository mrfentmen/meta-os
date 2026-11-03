# OC2B-158–166,171–175 — baked-image verification (this lane, 2026-11-02)

- Baked file: `/tmp/metaos-2026-11-02-oc2b-baked.qcow2` (snapshot of oc2b-work.qcow2 after shutdown), 1,587,019,776 B, sha256 `849219f3216677ca32b3b3acc982e892b8280ff4dccea79fee9a663d6f570b51` (pre-boot sha; verification boots below dirtied the working copy — sha is of the as-baked state).
- Base: 448,790,736 B → growth +1,138,229,040 B (+253.6%).
- Boot log: `/tmp/oc2b-bake2-boot.txt` (2nd guest session, `-cpu max`, port 2225).
- OC2B-160: `opencode --version` with no manual install step → **1.19.5**. OC2B-172 persistence: same on 2nd boot. YES.
- OC2B-161: checkout present, `git log -1` = b0a66bf02e9e091a72a37e941c80a6d57ef61b66. YES.
- OC2B-162: manual `git pull --ff-only origin main` ran clean (no error); tip stayed b0a66bf — no move in-session (fact, not "up to date" quote — output truncated by head; pull exited 0).
- OC2B-163 desktop screendump: NOT POSSIBLE — server image has no desktop environment (no X/Wayland, no chromium yet). No screendump exists; none claimed. Blocker recorded (not a failure of method).
- OC2B-164 boot/mem vs §6: 2nd guest boot SSH-ready ~75s (vs §6 steady-state 64s — same order); idle mem 213/1965M (vs §6 212/1967M — same).
- OC2B-166 §6 re-run: autologin YES (relay tty1), DHCP 10.0.2.15/24 YES, dashboard HTTP → **000** (no listener on :18900 in baked image; §6 base-image 200 was the lane's server context — difference named, not hidden).
- OC2B-173 in-image model smoke: endpoint `UnknownError` (err_7c808c65, 41.7s) — receipt: none produced client-side (call failed before usage posted). Exact failure recorded.
- OC2B-174 gaps: no desktop/chromium (face-in-browser unverifiable in-image), node absent, model endpoint erroring server-side, dashboard server not running in image.
- OC2B-175 filename: `/tmp/metaos-2026-11-02-oc2b-baked.qcow2` (metaos-YYYY-MM-DD + lane suffix; image itself never in git).
