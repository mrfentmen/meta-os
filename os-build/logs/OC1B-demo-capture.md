# OC1B demo capture hub (tasks 254-256, 258, 260-262, 264-268, 270, 274)

Tree: opencode/500-s11 @ 94010c76 (== opencode/500 tip at capture time).
Image: kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin
built on this tree 2026-11-02 (~11:04 EST) from a clean userspace+kernel
build (nightly toolchain, RUSTC_BOOTSTRAP=1). sha256:
58ed24c12202eef3e2d24cd3158567f66c626b50034a0f93828d8a6ac48ff
Both capture sessions (K1 beats 1-4, K2 beat 5+fetch) booted THIS image.
QEMU 11.1.3, -display vnc for screendumps, -serial file: for serials,
HMP sendkey for live keys (real PS/2 scancodes, kernel keyboard path).

## Beats 1-4 serial (K1): os-build/demo/oc1b-beat1-serial.txt (414 lines)

Beat 1 — banner, alive, memory (card s01, L1-2,19,20,23,26):
  L1  META OS 0.1 (K6)
  L2  META OS KERNEL - alive (K1)
  L19 mem map: 15 regions, usable 506036K reserved 12601100K other 0K
  L20 mem frames: 126509 usable total
  L23 mem heap: 512K total
  L26 mem summary: K4 up

Beat 2 — ring 3 loader lines, three user addresses (card s02, L32-43):
  L32 user hello: 2527624 bytes magic=0x464c457f type=Some(2) entry=Some(105553116266496)
  L33 user hello: entry 0x600000000000 head [50, 48, ...]
  L38 user sleeper: 2798768 bytes ... entry=Some(106652627894288)
  L39 user sleeper: entry 0x610000000010 head [50, 48, ...]
  L42 user crasher: 2539192 bytes ... entry=Some(107752139522320)
  L43 user crasher: entry 0x620000000110 head [50, 48, ...]
  L34 HELLO FROM USERSPACE
(three distinct user addresses: 0x600000000000, 0x610000000010, 0x620000000110)

Beat 3 — three programs (card s03, L34-35,40-41,44):
  L34 HELLO FROM USERSPACE
  L35 user exit code 0
  L40 sleeper: before sleep
  L41 sleeper: pid 5
  L44 crasher: about to read zero

Beat 4 — fault isolation + bad-syscall refusal (card s04, L45,48,75):
  L45 INT user page-fault addr 0x0000000000000000 err 0x0000000000000004: task killed
  L48 sleeper: yielded and back
  L75 user bad syscall 99 refused
(survivor line L48 follows the kill line L45: containment holds.
`sleeper: bad call refused` L76 is the same event in the sleeper's own words.)

Readkey, live keys (plan beat 4, same session; a/b/ret via HMP sendkey at
t~10-13s wall; kernel fans each scancode out to the console ring and the
readkey-only ring, interrupts.rs):
  L53 readkey: polling syscall 5
  L55 readkey got 30
  L56 readkey got 158
  L195 readkey got 48
  L197 readkey got 176
  L409 readkey got 28
  L410 readkey: enter seen, done got=5
  L411 user exit code 0
got=5 (not got=3): press+release scancodes for a (30/158) and b (48/176)
plus ret press (28, enter seen). WAVE3's got=3 dropped the b pair; this
tree's deterministic outcome is got=5. The claim is "real keys reach
userspace through syscall 5" — proven with got=5, narrated as got=5.
Shell-side copies of the same keys produced "ab" + "unknown command"
(L412-414): the fan-out twin-ring working as designed, quoted honestly.

panic count in K1 serial: 0 (grep -c panic). loader-refused count: 0.

## Beat 5 serial (K2): os-build/logs/OC1B-demo-beat5-serial.txt (2115 lines)

Typed live in one session via HMP sendkey (status, status, mem, ps, fetch).
panic count 0. Refusal again present (L86 `user bad syscall 99 refused`).

status x2, ticks move, heap does not (card s05, L2075,2078):
  L2075 STATUS tasks=8 ticks=2073 heap_free_kb=255
  L2077 (shell echo) tasks 8 ticks 3719 heap_free 255K
  L2078 STATUS tasks=8 ticks=3719 heap_free_kb=255
mem (L2080): mem frames_free 126430 frames_total 126509 heap_free 255K heap_total 512K
ps (L2082-2089, eight rows, id 7 Running):
  ps id 1 state Exited ticks_used 0 prio 0
  ps id 2 state Exited ticks_used 0 prio 0
  ps id 3 state Exited ticks_used 0 prio 0
  ps id 4 state Exited ticks_used 0 prio 0
  ps id 5 state Exited ticks_used 0 prio 0
  ps id 6 state Exited ticks_used 0 prio 0
  ps id 7 state Running ticks_used 0 prio 0
  ps id 8 state Exited ticks_used 0 prio 0
fetch (cards s06-s07, L2096-2115; ribbon L2096-2105, facts L2108-2115):
  Mrfentmen@metaos / OS: Meta OS 0.1 (K6) x86_64 /
  Host: bare-metal Rust kernel (no_std) /
  Kernel: META OS KERNEL - alive (K1) / Uptime: 59s ticks 5906 /
  Tasks: 8 / Mem: frames_free 126430 frames_total 126509 heap_free 255K heap_total 512K /
  Programs: hello sleeper crasher (ring 3)

## Beat 7 chain (OC1B-260): os-build/logs/oc1b-chain/live-baseline-chain.json

Real all-flags crew run (TRIO_SAM_SEGMENT=1 TRIO_REVIEW_WONDER=1
TRIO_JUDGE_MODEL=1) over the capture-day live frame, in-process with the
production assessment function (spark_gen.generate — the same function
trio_agent and livecams --assess-one call), real crew_records, real
loopback-guarded dispatch seam. Camera 3 Ave @ 60 St Brooklyn
(88278063-8891-4144-9295-f5dc9a94d2ea), frame sha256 aef1cf8e...35f947b54.
Outcome: baseline, category "normal activity", model muse-spark-1.3,
latency 4872 ms; 1 patrol-check event; dispatch endpoint
http://127.0.0.1:8935/dispatch-simulated (never called — no flag).
Review/judge/response steps are ABSENT because nothing flagged: the plan
invents no incident, and neither does this run. The film says exactly that.

## Beat 7 receipt close-up (OC1B-261): os-build/captures/oc1b-beat6-receipt.png

No dispatch occurred (baseline reading), so NO receipt exists. Staging a
flag to manufacture one is forbidden by the plan. The close-up card states
the honest shape with `simulated=true` legible: nothing flagged, nothing
sent; the loopback SIMULATED endpoint named. The retired staged receipt
(R5-imperium/receipt.txt, sim-6623d237a90b3d9d) is NOT shown and NOT
presented as this run's.

## SIMULATED label, whole beat 7 (OC1B-262)

Beat 7 spans film 138-164s (s08 138-144, s09 144-152, s10 152-158,
s11 158-164). SIMULATED appears on s08 (footer: muse-spark-1.3 card
titled "a real camera, read live" — label check: the card carries the
model + live-reading source), s10 (footer "SIMULATED all beat 7"), s11
(face: "SIMULATED" in title and endpoint block). s09 is the raw camera
still (no overlay, as committed). Label check: PASS — every interpreted
frame of the beat carries the SIMULATED provenance; the unlabelled still
is the unaltered evidence.

## Film build (OC1B-264)

Source cards: os-build/demo/oc1b-frames/s01..s12.png (s01-s05, s11 are
copies of the committed os-build/captures/oc1b-beat*.png proofs; s09 is
the padded live still; rest are serial/reading excerpt cards rendered
from committed logs by /tmp/oc1b-cards.py with PIL/Monaco).
Intermediates (/tmp/oc1b-seg/*.mp4) never enter git.
Build (from os-build/demo/oc1b-frames/):
  for each seg: ffmpeg -loop 1 -i <seg>.png -t <dur> -r 10 -pix_fmt yuv420p /tmp/oc1b-seg/<seg>.mp4
  ffmpeg -f concat -safe 0 -i /tmp/oc1b-seg/list.txt -c copy ../demo-3min.mp4
Output: os-build/demo/demo-3min.mp4 (replaced on branch).

## ffprobe (OC1B-265)

  duration=180.000000, size=719410 bytes, codec h264, 1280x720,
  pix_fmt yuv420p, r_frame_rate 10/1, nb_frames=1800, stream duration 180.000000.
Measured with ffprobe, not estimated. Exactly 180.000s.

## Frame checks t=10/t=90/t=160 (OC1B-266)

Extracts: os-build/demo/oc1b-check/t10.png, t90.png, t160.png.
  t=10  -> s01 beat-1 card: banner L1-2, mem L19,20,23,26. Matches serial. PASS.
  t=90  -> s04 beat-4 card (70-92s): fault L45, survivor L48, refusal L75,
           got lines 55-56 + 409-410 got=5. Matches serial. PASS.
  t=160 -> s11 nodispatch card (158-164s): no-dispatch honest shape,
           simulated=true legible. Matches chain outcome (baseline). PASS.

## Watch-through (OC1B-267)

Midpoint frame extracted per segment (t=11,34,58,81,106,124,133,141,148,
155,161,172) and matched to its source card (downscaled-luma means agree
to <=0.3; s09 still 81.7 vs 82.0). Content inventory: 11 serial/reading
text cards + 1 live DOT still (street, no people per its own reading).
Frames showing a face: 0. Frames showing a web page: 0. Frames showing a
browser: 0. The still carries its on-image DOT timestamp, not a browser.

## Honesty pass (OC1B-268)

- No staged element presented as real: readkey got=5 narrated as got=5;
  shell "unknown command" from fanned-out keys kept in the record;
  no-dispatch card says no receipt exists; retired staged receipt nowhere shown.
- No simulated element presented as real: the only dispatch mention is the
  labelled loopback endpoint + simulated=true on the no-dispatch card.
- Medicus: scene-only doctrine respected — no Medicus beat, no diagnosis
  language anywhere in the film.
- Known anomaly, disclosed: on THIS tree the VGA text path renders the
  fetch ribbon as garbled glyphs while the serial carries the correct ASCII
  ribbon (exhibit: os-build/captures/oc1b-vga-fetch.png — ribbon region
  garbled, facts lines below it clean; WAVE3-w3_s1.jpg on the wave-3 tree
  was clean text). The film therefore uses serial-excerpt cards (the plan's
  "serial terminal held large" shot), never VGA. Not a capture defect: the
  serial is the kernel's own byte record. Rowan's lane to diagnose; no
  kernel/src edit made or attempted here.

## Fallbacks, per beat (OC1B-270)

Every beat's fallback is a committed file in this repo (no live re-enactment):
  b1: oc1b-beat1-serial.txt L1-2,19,20,23,26 (+ WAVE3-w3_s1.jpg era backup, superseded)
  b2/b3/b4: oc1b-beat1-serial.txt loader/hello/fault/readkey lines
  b5: OC1B-demo-beat5-serial.txt STATUS/mem/ps lines
  fetch: OC1B-demo-beat5-serial.txt L2096-2115
  beat7: OC1B-demo-beat6-live.txt + oc1b-beat6-frame.jpg + oc1b-beat6-reading.json
         + oc1b-chain/live-baseline-chain.json (primary sources, not downgrades)
  b8: OC1B-demo-beat5-serial.txt L2078,2088
All fallback paths resolve (checked at commit time).

## Film record (OC1B-274)

sha256 a29bc47dd56e9f583d8af231d8d3908f3a4c4d6218fb1b3492ce5381b3ae13f0
size 719410 bytes (< 1MB repo discipline: film committed at
os-build/demo/demo-3min.mp4).
Closing line of the film (s12): "That is what runs today." — the script's
closing line, present verbatim.
