# OC2B-046/047 — §2 screendump index (2026-11-02, tree 67949822)
No screendumps were taken in §2: every bootable-artifact step (027/029/031/
035 and all KF-03..KF-05/KF-08 graphics steps) had no image to boot — builds
stop at compile time (KF-01) or the code is unlanded (KF-02+). Per task rules
(capture ONLY if an image exists; never fake a capture), the index is
honestly empty. Each absent capture below carries its verified reason.

| capture (planned) | task | tree sha | status |
|---|---|---|---|
| OC2B-kf01-a1.png | 027 | 67949822 | absent-verified — 0.11.17 build fails, no image (see OC2B-kf01-attempt1.txt) |
| OC2B-kf01-a2.png | 029 | 67949822 | absent-verified — 0.10.9 build fails, no image (see OC2B-kf01-attempt2.txt) |
| OC2B-kf01-candidate.png | 031 | 67949822 | absent-verified — candidate build fails, no image (see OC2B-kf01-candidate.txt) |
| OC2B-kf02-shell.png | 035 | — | absent-verified — no upgraded stack exists (see OC2B-kf02.txt) |
| OC2B-kf03-first/red/blue, kf04-text(_late), kf05-bootlines | 039–045 | — | absent-verified — framebuffer/pixel code unlanded (see OC2B-kf03.txt) |

OC2B-047 verification: zero captures claim a tree sha, so zero mismatches.
First capture taken in a later section starts the non-empty index there.

## §3 rows (OC2B-071, 2026-11-02, tree 67949822)
No screendumps taken in §3: KF-06 ribbon, KF-07 phases/keypress, KF-08 fallback,
and all graphics-support captures (060–070) have no graphics tree to boot.
| capture (planned) | task | tree sha | status |
|---|---|---|---|
| OC2B-kf06-ribbon.png / ribbon2.png / kf06-fresh.png | 051/052/070 | — | absent-verified — no ribbon code (see OC2B-kf04-08.txt) |
| OC2B-kf07-phaseA/B.png, kf07-keypress.png | 053/055 | — | absent-verified — nothing animates |
| OC2B-kf08-fallback.png | 056 | — | absent-verified — no graphics tree/fallback flag |
| OC2B-kf-mode.png, kf-transition.png, kf-fetch.png | 062/066/069 | — | absent-verified — single text mode only; not-capturable noted |
| OC2B-soakA/B + ribbon-start/end (§5 lane) | — | — | not this lane; no rows claimed |

## §4 rows (OC2B-095, 2026-11-02, tree 67949822)
No screendumps taken in §4: KF-09 windows, KF-10 window shell, topbar/dock unlanded.
| capture (planned) | task | tree sha | status |
|---|---|---|---|
| OC2B-kf09-window.png / kf09-two.png | 076/077 | — | absent-verified — no windowing code (see OC2B-kf09-11.txt) |
| OC2B-kf10-status/mem/ps/badcmd/badsyscall/longline/help/clearA/clearB.png | 078–082/088/091/092 | — | absent-verified — no window shell |
| OC2B-kf-topbar.png / kf-dock.png | 086/087 | — | absent-verified — no bar/dock drawn |
| OC2B-oc-desktop.png (§7 lane) | — | — | not this lane; no rows claimed |

OC2B-047 re-verification (§2–§4): zero captures taken, zero sha claims, zero mismatches.
