# R6-2 DEMO CAPTURE — beat file index (OPENCODE_NEXT_TASKS #1)

Script: `os-build/DEMO_SCRIPT.md` (H-FP1). Session tool:
`os-build/demo-capture.sh` on merge 28e99285 (GATE GREEN 7/7).
Captures are stills + one serial log, not clips — durations do
not apply; the serial log carries the timeline. Receipt id
`sim-6623d237a90b3d9d` re-verified in beat6-receipt.txt.

| Beat | File | Shows |
|---|---|---|
| 1 boot | beat1-boot.ppm | K4/mem + loader/hello window (banner in serial lines 1-2) |
| 2 ring 3 | beat2-ring3.ppm | loader lines 0x600000000000/0x610000000000/0x620000000110 + HELLO |
| 3 programs | beat3-programs.ppm | sleeper/crasher lines, pid 5, about-to-read-zero |
| 4 fault | beat4-fault.ppm + beat4b-after-fault.ppm | pre/post shell lines; fault line itself serial-only (line 44) |
| 5 shell | beat5-status/mems/ps.ppm | typed status/mem/ps + answers (ticks 12574, frames 127147/127196, 7 rows id-7 Running) |
| 5/6 serial | serial-all.txt (67 lines) | every beat's lines incl. `task killed`, STATUS, `user bad syscall 99 refused` |
| 6 receipt | beat6-drill.log/receipt.txt/package-sent.json/incident.json | R5-imperium record copies; SIMULATED throughout |
