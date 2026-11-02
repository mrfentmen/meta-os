# The user's first minute (OS-213): power to prompt, scripted

0:00 Power / QEMU launch. SeaBIOS, bootloader stages (dots).
0:20 `META OS - milestone K6` + `META OS KERNEL - alive (K1)` on
screen and serial. K1-K3 survived every later section.
0:25 `mem map:` — 16 regions scroll by, then allocator, probe ok,
heap, Box+Vec, stress, `mem summary: K4 up`.
0:30 `ABABABABAB` — tasks A and B alternate and exit.
0:31 `C sleeping 200 ticks` — task C sleeps.
0:32 `HELLO FROM USERSPACE` + `user exit code 0` — first program.
0:33 `sleeper: before sleep` / `pid 5` / `yielded and back`.
0:34 `crasher: about to read zero` → `user page-fault ... task
killed` — the kernel does not flinch; sleeper continues.
0:36 `C awake` (sleep done) → `sleeper: after sleep` →
`bad syscall 99 refused` → `sleeper: bad call refused` →
`user exit code 0`.
0:40 `uptime Ns` every second, forever. Type `status`: tasks,
ticks, heap. Type `help`. Type nonsense: refused with help.
Everything marked NOT BUILT below is absent from this
walkthrough on purpose.
