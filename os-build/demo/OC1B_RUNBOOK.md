# OC1B RUNBOOK — replay the film and every live proof behind it (Nov 4)

Tree: opencode/500-s11 @ 94010c76 (merge target: opencode/500 via Pax).
Image: kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin,
sha256 58ed24c12202eef3e2d24cd3158567f66c626b50034a0f93828d8a6ac48ff.

## 0. Watch the film (2 min)

  ffplay os-build/demo/demo-3min.mp4
(or any player). 180.000000s. Closing line: "That is what runs today."

## 1. Verify the film's numbers (3 min)

  ffprobe -v error -show_entries format=duration,size \
    -of default=noprint_wrappers=1 os-build/demo/demo-3min.mp4
  sha256sum os-build/demo/demo-3min.mp4   # expect a29bc47d...3ae13f0
  # frame checks vs logs:
  ffmpeg -ss 10  -i os-build/demo/demo-3min.mp4 -frames:v 1 /tmp/r10.png
  ffmpeg -ss 90  -i os-build/demo/demo-3min.mp4 -frames:v 1 /tmp/r90.png
  ffmpeg -ss 160 -i os-build/demo/demo-3min.mp4 -frames:v 1 /tmp/r160.png
Compare with os-build/demo/oc1b-check/t{10,90,160}.png and the line
numbers in os-build/logs/OC1B-demo-capture.md.

## 2. Re-run the kernel proofs (15-25 min, needs nightly + QEMU)

  NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"
  export PATH="$NIGHTLY:$PATH" RUSTC_BOOTSTRAP=1
  # userspace (4 bases) then kernel:
  cd os-build/userspace/user
  for pair in "hello:0x600000000000" "sleeper:0x610000000000" \
      "crasher:0x620000000000" "readkey:0x630000000000"; do
    b=${pair%%:*}; base=${pair##*:}
    sed "s/0x620000000000/$base/" link.ld > "/tmp/link-$b.ld"
    RUSTFLAGS="-C relocation-model=static -C code-model=large \
      -C link-arg=-no-pie -C link-arg=-T/tmp/link-$b.ld" \
      cargo build --target x86_64-unknown-none --bin "$b"
  done; cd ../../../; (cd kernel && cargo bootimage)
  # boot, type a/b/ret early for readkey, then status/mem/ps/fetch late:
  IMG=kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin
  qemu-system-x86_64 -drive format=raw,file="$IMG" -display vnc=:21 \
    -no-reboot -m 512M -serial file:/tmp/rb.txt \
    -monitor "unix:/tmp/rb-mon,server,nowait" &
  # t+10s: sendkey a; sendkey b; sendkey ret  |  t+60s: status x2, mem, ps, fetch
  grep -E "alive|HELLO|task killed|bad syscall 99 refused|got=|STATUS" /tmp/rb.txt
  # expect: alive, HELLO, task killed, refusal, readkey got lines, STATUS x2

## 3. Re-run the live beat-7 proof (5 min, needs SPARK_API_KEY + egress)

  export SPARK_API_KEY="$(head -n 1 "$HOME/Desktop/hackathon key.txt")"
  python3 server/queue/livecams.py --assess-one --area Brooklyn \
      --division vigiles --out /tmp/rb-live
  # expect: one live frame + live-reading.json, category on screen.
  # If egress fails: fallback is the committed frame+reading
  # (os-build/demo/oc1b-beat6-frame.jpg + oc1b-beat6-reading.json) —
  # show those, say so, move on. No re-typed claims, no staged fill-in.

## 4. Re-run the chain proof (5 min, needs SPARK_API_KEY)

  export TRIO_SAM_SEGMENT=1 TRIO_REVIEW_WONDER=1 TRIO_JUDGE_MODEL=1
  python3 /tmp/oc1b-chain.py   # (script kept outside repo; see capture log)
  # expect: outcome baseline on a normal-activity frame; a flagged frame
  # would proceed to review/judge and dispatch ONLY to the loopback
  # simulated endpoint. Never invent a flag.

## 5. Fallback order (if anything live fails on the day)

Cut to the committed log line named in os-build/logs/OC1B-demo-capture.md
(fallback table), read it aloud, move on. The film itself is the primary
record; live steps are bonuses, never load-bearing.
