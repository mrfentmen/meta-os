# OC3B-151/152/153/168 — demo content inventory + verification + size

All byte counts are exact `git cat-file -s` on main @c38c6187.
No file opened-to-watch here; structural proof via ffprobe on bytes
extracted to /tmp (read-only), playback confirmation is OC1's.

| Item | Path on main | Bytes | Verified as |
|---|---|---|---|
| 3-min film | os-build/demo/demo-3min.mp4 | 719410 | h264 1280x720 10fps, duration exactly 180.000s, no audio track. Matches cut plan beat sum 22+25+23+22+28+18+26+16. OC3B-152/171 structural pass. |
| ASCII loop | metaos-theme/wallpapers/live/meta-loop.mp4 (+ payload-theme twin) | 461855 | h264 1920x1080, duration 1.5s loop segment. OC3B-153 structural pass; stutter-free looping is OC1 playback. |
| Wallpaper 1366 | iso/theme/wallpaper/meta-wallpaper-1366x768.png | 82037 | 1366x768, renders fullscreen pixel-native. OC3B-154 pass. |
| Wallpaper 1920 | iso/theme/wallpaper/meta-wallpaper.png | 143696 | 1920x1080, renders fullscreen pixel-native. OC3B-154 pass. |
| ASCII art stills | metaos-theme/wallpapers/meta-ascii.png etc. | sized | 1920x1080 verified on meta-ascii. |
| Studio loop frames | metaos-theme/wallpapers/studio-loop/loop-*.jpg | — | source frames for the loop MP4. |
| Footage pool | oc-proofs/footage/nb-*.mp4 + nc-*.mp4 + EDL_3MIN.md + FOOTAGE_INDEX.md | see index | staged clips (10-30s each), indexed, not yet assembled into a cut. |
| Demo audio | os/demo-assets/audio/ (stingers + narration + TIMING.md) | see dir | original synthesized works, LICENSES.md on file. Film itself ships silent by cut design. |

OC3B-155 placed-paths: target ~/Videos (film+loop+footage) and
~/Pictures (wallpapers+stills); owned by the image/ISO lane at
install — recorded here as the contract, confirmed on OC1 boot.
OC3B-168 total: film+loop+the two wallpapers = 1,406,998 bytes
(~1.4 MB). OC3B-169/170: no ISO budget figure is published anywhere
to check against, so no pass/fail is claimed; the 1.4 MB number plus
the footage-pool figure go to Pax with the question, not a verdict.
