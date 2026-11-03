# OC3B-245/246 — removable-media autorun policy

Xfce/Thunar never auto-executes media contents: the volume manager
opens the folder window or does nothing, per upstream defaults, and
no lane ships an autorun handler, desktop file, or udev rule that
would change that. So "never executes silently" holds by absence of
mechanism, not by a tested prompt. OC1 confirms on boot with a USB
stick: insert, observe folder-or-nothing, eject. That observation is
the proof; this file is the policy record it checks against.
