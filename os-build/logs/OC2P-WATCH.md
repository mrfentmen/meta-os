# OC2P standing watches (read-only, <2 min, NO VM)

## T1 Rowan — kernel lanes
CMD: `git ls-remote origin 'rowan/kernel-k4*' 'rowan/kernel-kf*'`
LAST-KNOWN (2026-11-03 live):
- rowan/kernel-k4-build `4a37f998`; -design `b7d1b6a4`; -ipc `bd4e003a`
- -ipc2 `f654ed56`; -pair-swap `0a2d5cd5`
- kernel-kf01-spike `8e725f4b`; kernel-kf03 `4d04623e`
TRIGGER: any sha move → support-test within 24h. No kernel edits ever.

## T2 Hana — base bytes on main
CMD: `git ls-tree -r --name-only main | grep -Ei '\.(iso|qcow2)$'` (want 0)
LAST-KNOWN: 0 hits → no re-proof owed.

## T3 isowork — other lane's live tree
CMD: `ls -la /private/tmp/isowork/` (filenames + bytes ONLY, never recompute)
LAST-KNOWN: `metaos-1.0.iso` 4259762176 B 00:29 + `.sha256` + `.sha256-fixed`.
RULE: read-only. Never touch, never boot, never sha for them.

## T4 OC1 evidence — the firing event
WATCH: OC1 STATUS file + serial log + shot dir (paths filled at post time).
LAST-KNOWN: ABSENT — no OC1 STATUS/serials/shots on branch or main.
TRIGGER: the hour OC1 posts → run `OC2P-crosscheck-OC1-boot-TEMPLATE.md`,
file AGREE/DISAGREE.
