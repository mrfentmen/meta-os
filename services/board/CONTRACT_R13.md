# Contract note — R13-003, board config defaults

Status: **AUDITED — 1 gap filed**.
Facet: which defaults the board uses when no configuration is supplied.

## Evidence

Command:

```sh
grep -nE 'cfg|config|default|BD_MAX|fn bd_init' services/board/*.goose
```

Output:

```text
board.goose:36:let BD_MAX_ROOMS: i64 = 4;
board.goose:37:let BD_MAX_POSTS: i64 = 24;
board.goose:38:let BD_ROOM_NAME_MAX: i64 = 16;
board.goose:39:let BD_POST_MAX: i64 = 96;
board.goose:56:fn bd_init() {
```

No `cfg`, `config`, or `default` symbol or branch exists.

## Corrected contract

The board has no runtime configuration surface. Its capacities are compile-time constants
(4 rooms, 24 posts, 16-byte names, 96-byte posts) and `bd_init()` only clears the tables. There is
no config file, environment variable, or caller-supplied default. A caller that needs different
capacities must change the constants and rebuild.

## Mismatches

- **R13-003-G1** — the task asks for config defaults; no config-default contract exists. The only
  defaults are the fixed capacities above. See `GAPS_R13.md`.
