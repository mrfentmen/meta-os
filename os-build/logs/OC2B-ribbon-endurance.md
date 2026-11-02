# OC2B Ribbon endurance (OC2B-119–120) — ABSENT, run skipped honestly

Tree: same proven TEXT tree as the soaks (branch `opencode2/500` tip
`67949822`, kernel == main `2b153988`; gate GREEN). Graphics are UNLANDED.

## Absence verification (single check, 2026-11-02 ~16:10 UTC)

- `grep -rn ribbon kernel/src/`: exactly ONE hit, a doc comment in
  `kernel/src/logo_frames.rs:3` ("its ribbon path (loopPoint),
  surface (buildSurface), lighting" — a Lobster-surface note, not display
  code). No ribbon draw routine exists.
- `grep -n "^mod " kernel/src/main.rs`: gdt interrupts logo_frames mem
  memory sched tasks traps user vga — NO `framebuffer` module wired.
  `kernel/src/framebuffer.rs` header states UNWIRED itself.
- `grep -rn "animate|frame_counter|phaseA|phaseB" kernel/src/*.rs`
  (code lines): ZERO hits. No animation loop, no frame counter exists.
- `kernel/src/vga.rs` header: VGA text at 0xB8000 is the only console;
  `kernel/src/main.rs` header: "No pixel framebuffer exists under
  bootloader 0.9.35".
- Live proof: soak screendumps (OC2B-soakA-*.png, OC2B-soakB-*.png) show
  VGA text only; additionally `os-build/captures/OC2B-ribbon-absent.png`
  (this section) is a screendump of the running soak console showing the
  text shell with no ribbon, no animation phases, no counter.

## OC2B-119 (30-min run with start/end frames): SKIPPED

Condition not met: the ribbon does not animate on this tree (it does not
exist). Running 30 minutes and screenshotting a text console twice would
fake endurance evidence for a feature that has not landed. No
`OC2B-ribbon-start.png` / `OC2B-ribbon-end.png` pair is claimed; the pair
is recorded here as NOT TAKEN, with the reason above. When Rowan lands
the ribbon, this section re-runs for real.

## OC2B-120 (frame-counter samples at 0/10/20/30): NO DATA

There is no frame counter to sample. Four readings cannot be honestly
reported, so none are. Values table: N/A (feature absent).
