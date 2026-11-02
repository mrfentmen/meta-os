# WAVE3_KERNEL_PROOF.md — Section 1, tasks 1-10 (tip c7aeb162)

1. Clean worktree /tmp/wave3 at origin/main c7aeb162 (not a clone;
   `git status` clean at start; same tree a fresh clone would fetch).
2. `sh os-build/gate.sh` (NIGHTLY pinned) → GATE GREEN 7/7.
   Log: WAVE3-combined-gate.log. Boot image from this tree.
3. Interactive QEMU+VNC boot, serial WAVE3-combined-serial.txt,
   screendumps WAVE3-w3_s1/fetch/s2.jpg.
4. Banner `META OS 0.1 (K6)` line 1, `META OS KERNEL - alive (K1)`
   line 2, `panic` count 0 (grep -ci).
5. Userspace: `HELLO FROM USERSPACE` + `user exit code 0`;
   `sleeper: before sleep` / pid 5 / `yielded and back` /
   `after sleep`; `crasher: about to read zero` then
   `INT user page-fault ... task killed`, sleeper continues.
6. Readkey ON THE COMBINED TREE: `user readkey: entry
   0x630000000010`; `readkey: polling syscall 5`; typed a,b,ret
   via HMP sendkey during the poll window ->
   `readkey got 30`, `readkey got 158`, `readkey got 28`,
   `readkey: enter seen, done got=3`; clean exit
   (`user exit code 0` follows).
7. Fetch ON THE COMBINED TREE: typed `fetch` -> ribbon +
   `Mrfentmen@metaos`, `OS: Meta OS 0.1 (K6) x86_64`,
   `Host: bare-metal Rust kernel (no_std)`,
   `Kernel: META OS KERNEL - alive (K1)`,
   `Uptime: 28s ticks 2875`, `Tasks: 8`,
   `Mem: frames_free 126430 frames_total 126509
   heap_free 255K heap_total 512K`,
   `Programs: hello sleeper crasher (ring 3)`.
   Screendump WAVE3-w3_fetch.jpg.
8. Shell: `status` -> `tasks 8 ticks 2177`,
   then `tasks 8 ticks 4258` (ticks moved);
   `mem` -> frames lines; `ps` -> 8 rows
   (id 1-6,8 Exited, id 7 Running).
   Screendumps WAVE3-w3_s1.jpg / WAVE3-w3_s2.jpg.
9. `user bad syscall 99 refused` (serial line 103, sleeper's
   bad call; gate asserts `loader refused` count 0 separately).
10. No item failed. No kernel/src edits (Rowan's lane untouched).
