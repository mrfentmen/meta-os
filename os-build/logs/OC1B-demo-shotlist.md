# OC1B demo shotlist (tasks 251-252) — kernel-only film, current tree

Source beats: DEMO_KERNEL_ONLY_PLAN (8 beats, 180s) + DEMO_SCRIPT fallbacks.
Backing rule: every shot names its committed log or live run; unbacked shots cut here.

| # | Shot | Backing |
|---|---|---|
| b1 | boot banner/alive/mem lines | WAVE3-combined-serial.txt lines 1-3 (re-capture live on this tree: cap-b1) |
| b2 | loader lines, 3 user addresses, HELLO | live serial (re-capture: cap-b2) |
| b3 | hello exit 0, sleeper cycle, crasher line | live serial (re-capture: cap-b3) |
| b4 | fault line + sleeper continues + readkey got=3 (typed live) | live serial (re-capture: cap-b4 + key sends) |
| b5 | status x2 (ticks move), mem, ps rows | live typed session (re-capture: cap-b5) |
| b5c | bad syscall refused close | serial refusal line (re-capture inline) |
| b6 | livecam assessment live run | NEW live run this session (cap-b6-live.txt) |
| b6b | patrol→review→judge→response timeline | timeline file from live run |
| b6c | dispatch receipt close-up, simulated=true legible | receipt render card |
| cut | 180.000s assembly | ffmpeg concat (previous build script reused) |
| check | t=10/t=90/t=160 frame checks | extracted PNGs vs logs |

Dropped at list time: none — all shots have either committed backing (R5-soak, WAVE3 serials) or a live-run slot this session.
