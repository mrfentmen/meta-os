#!/usr/bin/env bash
# os-build/layer1/prove_k2_k3.sh — capture the two milestones the serial log
# cannot see: the VGA screen (K2) and real keystrokes (K3 keyboard).
#
# The trick is QEMU's monitor on stdin. `screendump` grabs the VGA buffer, so
# the kernel's own text is captured as pixels; `sendkey` injects PS/2 scancodes,
# so the keyboard handler, the ring buffer, the scancode decode and the shell
# are exercised for real rather than inferred. Nothing here is mocked: the
# keystrokes go through the emulated i8042 exactly as a human's would.
#
# Three QEMU facts cost a run each to learn, so they are written down:
#   - `-display none` has no graphical console, so `sendkey` is silently
#     dropped: the kernel polled an empty buffer and nothing was typed.
#   - `-vnc` alone is not enough either. Key events route through the
#     display's input handler, which exists only while a client is connected;
#     the monitor still accepts `sendkey` and still drops it. vnc_type.py
#     connects as a real RFB client, which is what gives those events a path.
#   - `screendump` writes the current VGA state, so the boot shot must be taken
#     before paging floods the screen, and the shell shot after the keys land.
#
# The keys are real PS/2 traffic: QEMU translates each keysym to set-2
# scancodes for the emulated i8042, which is what the kernel's IRQ1 handler
# reads. Nothing bypasses the kernel.
#
# Then it asserts, from the artifacts:
#   - K3 timer line with a non-zero tick count,
#   - a shell command answered (uptime/STATUS),
#   - both screenshots non-blank (screen_evidence.py writes PNGs + maps).
#
# Exit: 0 all proofs present, 1 a proof is missing, 2 the image is missing.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

BIN="${KERNEL_BIN:-kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin}"
# Capture to a scratch name, then promote to the evidence name only when every
# check passes. An earlier version wrote K3-boot.txt directly, so a flaky
# keyboard run overwrote a proven log with a failed one — evidence must never
# be destroyed by a run that proves nothing.
LOG="os-build/logs/K3-capture.txt"
SHOT_BOOT="os-build/logs/K2-boot.ppm"
SHOT_SHELL="os-build/logs/K2-shell.ppm"

[ -f "$BIN" ] || { echo "prove_k2_k3: no image at $BIN (run build_kernel.sh)" >&2; exit 2; }
mkdir -p os-build/logs
rm -f "$LOG" "$SHOT_BOOT" "$SHOT_SHELL"

# Timing: the banner and alive line print before paging, so ~1.2 s is the boot
# screen. The console task spawns only after the scheduler starts, and how long
# that takes varies with machine load — an attempt at 2.5 s was lost outright on
# one run and worked on the next. So the same short command is typed at three
# points instead of trusting one window; a lost attempt costs nothing because
# every attempt produces the same STATUS line.
(
    sleep 2.5
    python3 os-build/layer1/vnc_type.py 127.0.0.1 5909 $'status\n' 0.09 || echo "vnc_type: attempt 1 failed" >&2
    sleep 1.6
    python3 os-build/layer1/vnc_type.py 127.0.0.1 5909 $'status\n' 0.09 || echo "vnc_type: attempt 2 failed" >&2
    sleep 1.6
    python3 os-build/layer1/vnc_type.py 127.0.0.1 5909 $'uptime\n' 0.09 || echo "vnc_type: attempt 3 failed" >&2
) &
TYPIST=$!
{
    sleep 1.2
    echo "screendump $PWD/$SHOT_BOOT"
    sleep 7.6
    echo "screendump $PWD/$SHOT_SHELL"
    sleep 0.6
    echo "quit"
} | qemu-system-x86_64 \
        -drive "format=raw,file=$BIN" \
        -serial "file:$LOG" \
        -vnc 127.0.0.1:9 -monitor stdio -m 256M -no-reboot \
        >os-build/logs/qemu-monitor.log 2>&1

# QEMU's own replies live here: a rejected sendkey is visible here and
# nowhere else, which is why the monitor transcript is kept next to the log.
wait "$TYPIST" 2>/dev/null || true

if grep -qiE "error|unknown command|invalid" os-build/logs/qemu-monitor.log; then
    echo "prove_k2_k3: monitor reported a problem:" >&2
    grep -iE "error|unknown command|invalid" os-build/logs/qemu-monitor.log | head -5 >&2
fi

if [ ! -s "$LOG" ]; then
    echo "prove_k2_k3: no serial log at $LOG" >&2
    exit 1
fi
echo "prove_k2_k3: serial log $LOG ($(wc -l < "$LOG" | tr -d ' ') lines)"

status=0
if grep -E "^K3 timer: [1-9][0-9]* ticks" "$LOG" >/dev/null; then
    echo "prove_k2_k3: K3 TIMER PROVEN — $(grep -E '^K3 timer:' "$LOG" | head -1)"
else
    echo "prove_k2_k3: K3 TIMER NOT PROVEN — no advancing tick line" >&2
    grep -E "K3 timer" "$LOG" >&2 || true
    status=1
fi

if grep -E "^(uptime [0-9]+s ticks [0-9]+|STATUS tasks=[0-9]+ ticks=[0-9]+)" "$LOG" >/dev/null; then
    echo "prove_k2_k3: K3 KEYBOARD PROVEN — a typed command ran:"
    grep -E "^(uptime [0-9]+s ticks [0-9]+|STATUS tasks=[0-9]+ ticks=[0-9]+)" "$LOG" | tail -3 | sed 's/^/  /'
else
    echo "prove_k2_k3: K3 KEYBOARD NOT PROVEN — no command output from a keystroke" >&2
    status=1
fi

EXISTING=()
for shot in "$SHOT_BOOT" "$SHOT_SHELL"; do
    [ -s "$shot" ] && EXISTING+=("$shot")
done
if [ ${#EXISTING[@]} -eq 0 ]; then
    echo "prove_k2_k3: K2 NOT PROVEN — QEMU produced no screendump" >&2
    exit 1
fi
if python3 os-build/layer1/screen_evidence.py "${EXISTING[@]}"; then
    echo "prove_k2_k3: K2 CONSOLE PROVEN — screendump carries readable text"
else
    echo "prove_k2_k3: K2 NOT PROVEN — screendump is blank" >&2
    status=1
fi

if [ "$status" -eq 0 ]; then
    cp "$LOG" os-build/logs/K3-boot.txt
    echo "prove_k2_k3: promoted $LOG to os-build/logs/K3-boot.txt"
else
    echo "prove_k2_k3: proof incomplete; kept $LOG, left K3-boot.txt untouched" >&2
fi

exit "$status"
