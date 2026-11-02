# Gap records — R13-003 board

## R13-003-G1 — no config-default contract

- **Claim:** the board has defaults for configuration when none is supplied.
- **Reality:** there is no config parser, no environment read, and no caller-supplied defaults.
  `BD_MAX_ROOMS`, `BD_MAX_POSTS`, `BD_ROOM_NAME_MAX` and `BD_POST_MAX` are compile-time constants;
  `bd_init()` only clears the tables.
- **Evidence:** the grep in `CONTRACT_R13.md`; `services/board/board.goose:36-39,56`.
- **Impact:** configuration changes require editing source and rebuilding. Any deployment expecting
  a runtime board config would silently use these fixed values.
- **Owner:** board config surface (B-L1-13 if it is ever wired).
