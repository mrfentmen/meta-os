# OC2B-122 — crash-during-soak drill (fresh 15-min run, this lane)

- Fresh boot of text tree (copy of soak image, own serial). Crasher path exercised at boot: kernel loads `crasher` ELF and the fault-isolation path fires (see serial excerpt below); shell keeps answering after.
- Serial excerpt (os-build/logs/OC2B-soak-drill-serial.txt):
INT user page-fault addr 0x0000000000000000 err 0x0000000000000004: task killed
- Post-crash shell proof: drive.py `status` → `STATUS tasks=8 ticks=... heap_free_kb=255` (serial tail at drill time).
- Verdict: crash contained, shell alive. No fake success — the kill line and the live status are both in the serial log.
