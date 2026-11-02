# WAVE2 PROOF INDEX (task 20) — every claim → its log

Kernel (Section 2):
- Readkey gate 419c209: opencode/round6 os-build/logs/readkey-gate-419c209-boot.txt (entry 0x630000000010, 8 tasks, 0 panic) + readkey-tworeader-419c209.txt (got=7) + transcript.
- Two-reader R-FP3: same tworeader log.
- W6 gate-2 boot 9de854d: W6-gate-9de854d-boot.txt + run transcript + W6-fetch-screen.jpg + W6-fetch-serial.txt (this branch).
- Clean-clone gate f027175: PROOF-f027175.md + PROOF-f027175-boot.txt (this branch).
- Current-tip screendump 2904e743: WAVE2-boot-tip.jpg + serial (this branch, from wave2 gate image).
- Bootloader spike: opencode/round7 os-build/logs/SPIKE_BOOTLOADER_RESULT.md (0.11.17 std-fail, 0.10.9 API-fail).
- Userspace packs: MORE_TASKS-findings-01.md on opencode/round6 (quitter unwired finding; hog/talker/listener absent).
- ABI checker: check_all PASS table (/tmp/wave2-checkall.log): abi_check, boot_manifest, failure_table, claim, facts, link, root_manifest all PASS.
- Soak: running, log /tmp/soak-serial.txt (verdict lands separately).

Demo film (Section 1):
- os-build/demo/demo-3min.mp4 (180.000s) + frames/ + cut.txt + CAPTURE_NOTES.md + CAPTURE.md + serial-all.txt.

Face (Section 3): os-build/face/ + guest-*.jpg + STATUS.md (all 74 tasks).
Image (Section 4): os-build/face/image/ (5 parts + manifest + JOIN note, sha f7d8581e) + fresh-boot.txt + guest-toolchain-listing.txt.
