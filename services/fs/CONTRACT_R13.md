# Contract note — R13-016, fs heartbeat line

Status: **AUDITED — 2 gaps filed**.
Facet: the heartbeat line `fs` emits, its interval, and what a supervisor can use to tell a live
filesystem from a mounted-but-stuck one.

## Evidence

Commands:

```sh
grep -nEi 'heartbeat|health|alive|status|stats|fs_stat|uptime' services/fs/*.goose
nl -ba services/fs/fs.goose | sed -n '429,443p'
```

Relevant output:

```text
services/fs/fs.goose:440:fn fs_stats() -> i64, i64, i64 {
services/fs/fs.goose:441:    if !fs_mounted { return 0, 0, E_STATE; }
services/fs/fs.goose:442:    return fs_free_blocks, fs_writes, CODE_OK;
services/fs/fs.goose:443:}
```

There is no `heartbeat`, `health`, `alive`, `uptime` or timer reference anywhere in `fs.goose`,
`paths.goose` or `fsck.goose`.

## Corrected contract

`fs` emits no heartbeat line and owns no timer. Its only status surface is
`fs_stats() -> (free_blocks, writes, code)`: `(0, 0, E_STATE)` when unmounted, otherwise the
current free-block count, a monotonic count of blocks written, and `CODE_OK`. Nothing carries a
timestamp, an interval or a “last progressed” mark.

The filesystem is synchronous: `fs_sync` writes the superblock and returns; there is no
background loop that could emit a beat.

## Mismatches

- **R13-016-G1** — no heartbeat line exists, so a supervisor cannot distinguish an idle mounted
  filesystem from a wedged one by output.
- **R13-016-G2** — the unmounted result `(0, 0, E_STATE)` is shaped like a healthy zero-usage
  reading; only the third field separates them. See `services/fs/GAPS_R13.md`.
