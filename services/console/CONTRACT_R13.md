# Contract note — R13-007, console restart idempotence

Status: **AUDITED — 1 gap filed**.
Facet: whether running the console entry twice, or restarting it in place, returns it to a known
state.

## Evidence

Command:

```sh
grep -nE 'fn .*(init|reset)|history_init|var line|var cursor|var esc_state|var history' services/console/*.goose
```

Output includes:

```text
console.goose:38:var line: u8[..256] = [0; 256];
console.goose:39:var line_len: i64 = 0;
console.goose:40:var cursor: i64 = 0;
console.goose:46:var history: MsgRing = msg_init(256, 8);
console.goose:55:var esc_state: i64 = 0;
entry.goose:... history_init();
```

## Corrected contract

A fresh process starts with zeroed static line/cursor/escape state; that part is clean by process
initialisation. `entry.goose` calls `history_init()` for the history ring. There is no single
`console_reset()` and no contract for re-entering `service_main` in the same process: a second
in-process start would reinitialise history but inherit `line`, `line_len`, `cursor` and
`esc_state`. Restart idempotence is therefore only true across process replacement, not across a
service restart in place.

## Mismatches

- **R13-007-G1** — no idempotent in-process restart contract; partial reset only. See
  `GAPS_R13.md`.
