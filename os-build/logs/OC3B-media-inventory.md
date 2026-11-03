# OC3B-101/106/111/114/120 — media inventory (static sources only)

Present by committed entry: image viewer Ristretto (OC2 drop-in),
Media Player + Volume Control + Screenshot (this lane, oc3b-desktop/).
Present by Xubuntu-base convention, TryExec-guarded, boot to confirm:
parole/pavucontrol/xfce4-screenshooter binaries themselves, webcam
stack (no cheese/guvcview named in ANY package list or payload tree —
recorded honestly absent as an app; the kernel UVC driver question is
OC1 hardware territory, not a launcher claim).

Audio plumbing: pavucontrol implies a PulseAudio/PipeWire sink to
control; neither daemon is named in the sliced package lists on main.
Recorded as UNCONFIRMED plumbing (not absent, not present) — OC1
`pactl info` at boot decides. No lane invents a sound server here.

102/103/104/105/112/113/119/121 film, loop, screenshot-file,
save-path, mute-test: all need the booted player. BLOCKED-with-owner
(OC1), listed once here instead of five empty files — the per-task
proof files below point back at this verdict rather than duplicating
it. (Where a task mandates a specific proof path, a pointer file
exists saying exactly that.)
