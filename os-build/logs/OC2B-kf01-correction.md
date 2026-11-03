# KF-01 correction acknowledgment (this lane, 2026-11-02, main 1c3104d2)

Pax's `os-build/KF01_CORRECTION_AND_RK008_MAP.md` (main 4b8d0105): the recorded
0.11.17 spike pinned the HOST crate (`bootloader`, image builder) instead of the
KERNEL interface (`bootloader_api`). Attempt 1 as recorded was malformed; 0.11 is
not a dead end. Budget amended: malformed attempt consumes nothing; 2 fresh attempts stand:
(1) corrected 0.11.17 = `bootloader_api` pin + RK-008 source rewrite + host-side image
build, verbatim logs or it does not count; (2) Rowan's pick if (1) fails with logs.

Effect on this lane's Sec 2 (OC2B-026–032, committed 14faa6e5): the MATCH reproductions
stand AS REPRODUCTIONS of the recorded evidence (the errors match the round7 log), but the
route conclusion ("0.11.x is a dead end") is WITHDRAWN — superseded by the correction.
No boot was ever claimed from those attempts, so nothing else changes.

Owed by this lane (Mac lane per the correction doc): when Rowan lands the corrected pin +
RK-008 rewrite on `rowan/bootloader-spike` (currently @1f006090, still the RK-006 wrong
pin `bootloader = "0.11"` — verified this lane, no newer commit), build + boot +
screendump set + verbatim logs committed on opencode2/500. Until then KF-01 stays BLOCKED —
on a corrected, buildable attempt instead of a malformed one.

Fences respected in this check: read-only (`git show`, `git ls-remote`); kernel/ untouched.
