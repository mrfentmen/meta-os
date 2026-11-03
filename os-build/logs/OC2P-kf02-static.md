# OC2P KF-02 static prep (NO VM — maps runbook to PROVEN S1 serials)

Runbook: `os-build/logs/OC2P-kf02-runbook.md` (target 717e7ffb).
PROVEN S1 serials (single-boot):

- `os-build/logs/OC2P-kf01-corrected/serial.log` (+ `serial2.log`)
- `os-build/logs/OC2P-kf01-corrected/OC2P-kf01-boot.txt`
- `os-build/logs/OC2P-kf01-corrected/VERDICT.md` (BOOT verdict)

10/10 runbook Step-6 assertions ALREADY EVIDENCED in S1: alive 1, K4-up 1,
HELLO 1, exit-0 x3, task-killed 1, readkey-entry 1, bad-call-refused 1,
bad-syscall-99-refused 1, STATUS tasks=8 ticks=5507, drive-session commands.
Zero panics, zero triples, loader-refused 0.

NEEDS OC1 FURNACE (not claimed here): triple repetition N=1,2,3 on the 0.11
stack + per-boot screendumps + kill/closeout + verdict file. Runbook stays
PARKED per OC123 iron rule 1. No new boot claims in this file.
