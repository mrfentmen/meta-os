# WAVE3_KERNEL_PROOF.md — Section 1, tasks 1-10 (clean clone @ 6524ebaf)

1. Clean clone https://github.com/mrfentmen/meta-os.git to
   /tmp/wave3clean; tip 6524ebaf (Bond wave 1+2 records merge).
   `git status` clean before gate (only the clone).
2. `sh os-build/gate.sh` (NIGHTLY via rustup) → GATE GREEN 7/7.
   Log: /tmp/wave3-gate.log. Boot: /tmp/gate-boot-xrTuyH.
3. VNC boot of the gate image; serial WAVE3clean-serial.txt;
   screendumps WAVE3-w3c-s1/fetch/s2.jpg.
4. Banner `META OS 0.1 (K6)` line 1, `META OS KERNEL - alive
   (K1)` line 2, `panic` count 0.
5. `HELLO FROM USERSPACE` + `user exit code 0` (33-35);
   sleeper before/pid/yielded/after; `crasher: about to read
   zero` then `INT user page-fault ... task killed` (45);
   sleeper continues after.
6. Readkey: `user readkey: entry ...`, `readkey: polling
   syscall 5`; typed x,y,ret via HMP sendkey during the poll ->
   `readkey got 45`, `xreadkey got 173`, `readkey got 28`,
   `readkey: enter seen, done got=3`; clean exit.
7. `fetch` -> ribbon + `Mrfentmen@metaos`,
   `OS: Meta OS 0.1 (K6) x86_64`,
   `Host: bare-metal Rust kernel (no_std)`,
   `Kernel: META OS KERNEL - alive (K1)`, uptime/ticks,
   `Tasks: 8`, `Mem: frames_free 126430 frames_total 126509
   heap_free 255K heap_total 512K`,
   `Programs: hello sleeper crasher (ring 3)`.
   Screendump WAVE3-w3c-fetch.jpg.
8. `status` twice: ticks 2159 -> 4315 (moved), 8 tasks;
   `mem` frames lines; `ps` 8 rows (id 7 Running).
   Screendumps WAVE3-w3c-s1/s2.jpg.
9. `user bad syscall 99 refused` (line 79) + gate asserts
   `loader refused` count 0.
10. No item failed. No kernel/src edits.
