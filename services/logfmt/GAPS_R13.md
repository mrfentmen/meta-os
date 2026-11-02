# Gap records — R13-020 logfmt

## R13-020-G1 — no environment variables, so no configuration contract

- **Claim:** `logfmt` reads environment variables that an operator can set.
- **Reality:** no `getenv`, `environ`, `sys_env`, `config` or `cfg_` identifier exists in
  `services/logfmt/*.goose`. Widths and levels are `let` constants (lines 48-52, 85-87).
- **Evidence:** the env grep in `CONTRACT_R13.md` returns no matches.
- **Impact:** changing the tag width or message cap requires a source edit and a rebuild. A
  malformed-value refusal path cannot be tested because there is no value to supply.
  This is a documented absence, not a hidden default.
- **Owner:** logfmt configuration; Layer 4 config policy (B-L1-13).
