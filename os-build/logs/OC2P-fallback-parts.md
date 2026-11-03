# OC2P fallback demo — PROVEN parts only (`OC123_DEMO_4H.md` fallback)

| Part | Path | Label |
|---|---|---|
| (1) kernel serial | `os-build/logs/OC2P-kf01-corrected/serial.log`, `serial2.log`, `OC2P-kf01-boot.txt`, `VERDICT.md` | VERIFIED (boot; STATUS tasks=8 ticks=5507, 0 panics) |
| (2) appliance demo | `os-build/logs/OC2-appliance-proof-journal.txt`, `OC2-appliance-crew-status.json` (20/20, $0.43), `OC2-appliance-events.jsonl` | VERIFIED (fresh boot, autostart, patrol) |
| (2b) image bytes | `/Users/test/metaos-images/metaos-agent-2026-11-02.qcow2` (2.5 GB, outside git; sha + recipe in STATUS) | VERIFIED (bytes exist off-tree) |
| (3) theme stills | `iso/theme/wallpaper/meta-wallpaper.png`, `greeter-wallpaper.png`, `iso/boot/grub/themes/metaos/meta-grub.png` | CODE-INSPECTED (`make_wallpaper.py --check` current; visual quality unjudged) |

Rule: label every part VERIFIED vs CODE-INSPECTED. A labelled parts demo
beats a faked whole. Decided at T+3 by OC1 if the ISO does not boot.
