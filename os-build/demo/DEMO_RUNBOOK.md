# DEMO RUNBOOK — Nov 4 replay (Wave 3 task 36; rehearsed task 37)

All paths relative to the repo root on Del's Mac. Times are
measured durations from the rehearsal run below.

## 0. Preconditions (2 min)

- NIGHTLY pinned: `NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"; export PATH="$NIGHTLY:$PATH"`
- QEMU present: `qemu-system-x86_64 --version` (11.1.3)
- Branch: `opencode/wave3` at the rehearsed tip (record tip: ________)

## 1. Film (1 min: ffprobe + 2 frame spots)

- `ffprobe -v error -show_entries format=duration -of csv=p=0 os-build/demo/demo-3min.mp4` → expect `180.000000`
- `ffmpeg -y -v error -ss 10 -i os-build/demo/demo-3min.mp4 -frames:v 1 /tmp/rb-b1.jpg` → boot text frame
- `ffmpeg -y -v error -ss 160 -i os-build/demo/demo-3min.mp4 -frames:v 1 /tmp/rb-b6.jpg` → judge receipt card
- Play: `ffplay -autoexit os-build/demo/demo-3min.mp4` (3:00)

## 2. Kernel proof (8 min: build + boot + type)

- `sh os-build/gate.sh` → GATE GREEN (builds userspace + kernel, boots headless, types help/status, asserts 7/7)
- Interactive: boot the gate image with `-vnc :NN -serial file:rb-boot.txt -monitor unix:...`, type `status` (ticks move), `fetch` (Mrfentmen@metaos + real status), `mem`, `ps`; `screendump` each to rb shots
- Readkey typed bytes: during `readkey: polling`, HMP `sendkey` a b ret → expect `readkey got` + `done got=N`

## 3. Model proofs (12 min + live spend ~$0.02)

- `python3 -m unittest discover -s tests/queue-python` → 141 OK (pre-live gate)
- `SPARK_API_KEY="$(head -1 ~/Desktop/hackathon\ key.txt)"` (never print it)
- chat_text wonder + segment frame + generate image + spark reading (Section 3 proof file has exact calls)
- Judge incident with TRIO_JUDGE_MODEL=1; file the receipt + timeline excerpt

## Rehearsal log (task 37/38)

## Rehearsal log (task 37/38) — rehearsed 2026-11-02 on opencode/wave3
- Film checks: ffprobe 180.000000, t=10 boot frame OK, t=160 judge receipt card OK.
- Branch gate: GREEN (log /tmp/reh2-gate.log, boot b85Q5D).
- Model commands dry-checked (imports only, no spend).
- GAPS FOUND (fixed or recorded):
  1. Pack-drill + soak shared one image file -> qemu write-lock failures, all drill runs empty. Fixed: separate image copies per run (soak-w3b, pack-w3).
  2. Broad pkill patterns (`bootimage-metaos`) killed soak QEMUs twice. Fixed: kill by exact PID file only.
  3. Fresh-chromium first paint needs ~25s before screenshots; early shots come back black. Noted in runbook timing.
  4. t=160 card initially cited the R5-4 receipt; rebuilt to cite the filed wave-3 judge run. CAPTURE_NOTES updated to match.
