# Gap records — R13-007 console

## R13-007-G1 — no idempotent restart

- **Claim:** the console can be restarted into a known state.
- **Reality:** `entry.goose` calls `history_init()`, but `line`, `line_len`, `cursor` and
  `esc_state` are process-static and have no reset function. A fresh process is clean; a second
  in-process `service_main` is not.
- **Evidence:** the state declarations in `services/console/console.goose:38-55`; `entry.goose`.
- **Impact:** a supervisor restart must replace the process. An in-place restart can inherit a
  half-edited line and escape state.
- **Owner:** console entry/init (Q-B-L1-4).
