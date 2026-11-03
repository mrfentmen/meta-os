# Spinning ASCII Meta loop — live wallpaper
`meta-loop.mp4`: 12 kernel attract frames (kernel/src/logo_frames.rs),
rendered Menlo 44pt two-tone Meta blue on #070B16, 1920x1080 @ 8fps,
1.5 s seamless loop (wrap step measures same as mid-cycle steps).
462 KB. Regenerate: metaos-theme/wallpapers/gen-ascii-loop.py
Play it: open meta-loop.mp4 (QuickTime/VLC).
On MetaOS: v1 = Xfce backdrop slideshow through per-frame PNGs
(see set-slideshow.sh — zero extra packages, native xfconf);
v2 = mpv loop behind the desktop (needs mpv + xwinwrap, planned).

## Live renderer supersedes the MP4 (2026-11-02)
`meta-live.py` cycles these exact frames in a GTK desktop-layer window —
the real art, live, no video file. The MP4 remains as a portable preview.
Autostart: `metaos-livebg.desktop` (TryExec-guarded).
Headless proof: 12 frames load, ticker wraps 0..11 cleanly, dense/ink
colors exact. GTK rendering itself is proven at first live boot.
