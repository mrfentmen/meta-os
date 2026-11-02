# Attract screen — spinning Meta loop (boss order 2026-11-01 ~21:40)

The boss asked for the ASCII spinning Meta logo as the
computer's screen. The name for it: an **attract screen** — the
idle display the machine shows when nobody is typing (the OS
cousin of a screensaver).

## Asset (done, on main)

`kernel/src/logo_frames.rs`: 12 frames, 46x17 characters, a
lemniscate band spun about the vertical axis with a fixed
tilt, depth-shaded with the classic `.,-~:;=!*#$@` ramp.
Generated offline by Pax; data only, no code. Frame 0 is the
loop full-face; the set cycles as one spin.

## Integration (Rowan, kernel lane — task R-9)

- Declare `mod logo_frames;` in `kernel/src/main.rs`.
- In the console task (`sched.rs`), add an attract state:
  - Enter when the console has had no keypress for ~2 seconds
    after boot, and again after ~30 seconds idle at the shell.
  - While active: clear the screen, draw the current frame
    centred, advance one frame every ~6 ticks, print
    `META OS 0.1` under the loop.
  - Any keypress exits attract, redraws the shell as it was,
    and the key is processed normally (not swallowed).
- Draw from the console task's existing loop between key
  polls. No new task, no blocking, no scheduler changes.
- Not in scope: colours beyond the current VGA writer default,
  a second animation, any change to the shell commands.

## Proof

A boot log cannot show it, so the proof is a screen capture:
QEMU screenshot while attract is active (the pipeline screen
capture path exists) plus a drive.py session showing a
keypress returning to a working shell (`status` answers).
Milo gate-1 on the code, OpenCode captures it with the demo
beats (Round 6, R6-2).
