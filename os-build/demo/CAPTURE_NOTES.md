# CAPTURE_NOTES.md — kernel-only 3:00 demo cut (OC1B §11, 2026-11-02)

Film: os-build/demo/demo-3min.mp4
(180.000000s measured by ffprobe, 10fps, 1280x720, h264, no audio,
sha256 a29bc47dd56e9f583d8af231d8d3908f3a4c4d6218fb1b3492ce5381b3ae13f0).
Cut list: os-build/demo/oc1b-cut.txt. Cards: os-build/demo/oc1b-frames/
(s01-s05, s11 are copies of os-build/captures/oc1b-beat*.png).

## What is real

Beats 1-5 are verbatim serial lines from two fresh QEMU boots (K1, K2) of
the image built on this tree (94010c76, image sha 58ed24c1...): banner,
alive, memory map, three loader addresses, HELLO, sleeper cycle, crasher
fault + sleeper continuation, bad-syscall refusal, readkey got=5 from keys
typed live over HMP sendkey, two STATUS answers with ticks 2073 -> 3719,
mem, eight ps rows, fetch ribbon + facts. Full serials committed as
os-build/demo/oc1b-beat1-serial.txt and
os-build/logs/OC1B-demo-beat5-serial.txt (panic count 0 in both).
Beat 7 is a live NYC DOT still (3 Ave @ 60 St, Brooklyn, fetched 11:14 EST
with on-image 11:14:38 caption) read live by Muse Spark ("normal
activity"), plus a real all-flags crew chain over that frame that ended
baseline (no flag, no dispatch). Frame, reading, chain committed as
os-build/demo/oc1b-beat6-frame.jpg / oc1b-beat6-reading.json and
os-build/logs/oc1b-chain/live-baseline-chain.json.

## What is scripted

Card layout, hold durations, and narration order follow
os-build/DEMO_KERNEL_ONLY_PLAN.md. Long serial lines are wrapped for
display on the cards; the serials themselves are unaltered. No serial line
was re-typed or edited. The typed shell words (status, mem, ps, fetch) and
keys (a, b, ret) are the only live inputs, and the serials show their
effects verbatim — including the shell's "unknown command" for the
fanned-out key copies.

## What is simulated

One thing, labelled on screen for the whole of beat 7: dispatch. The live
reading flagged nothing, so nothing was sent — the film says so and shows
no receipt. The endpoint that WOULD receive a flagged dispatch is the
loopback simulated endpoint only (http://127.0.0.1:8935/dispatch-simulated,
simulated=true), named on the no-dispatch card. The retired staged receipt
(sim-6623d237a90b3d9d) is not shown and not presented as this run's.

## Self-check

Twelve segment midpoints extracted and matched to their source cards;
t=10 (boot), t=90 (fault+readkey), t=160 (no-dispatch) verified against
the logs they claim. Zero frames show a face, a web page, or a browser.
Known anomaly, disclosed: on this tree the VGA text path garbles the fetch
ribbon while the serial is correct (exhibit
os-build/captures/oc1b-vga-fetch.png) — so the film shows serial cards,
never VGA. Supersedes: the wave-2 CAPTURE_NOTES (R6-2 screendumps +
staged beat-6 receipt card) described the old film; this file describes
the new one.
