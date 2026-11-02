# Config surface of `crates/os-boot` (B008)

Everything the crate reads: environment variables, CLI flags, and files. Defaults and refusal
behaviour are taken from the code, not from the Python source.

## Environment variables

| Variable | Read at | Default | Used for | Refusal when wrong |
|---|---|---|---|---|
| `CARGO_MANIFEST_DIR` | `carried.rs:91-101` (compile-time `env!`) | set by Cargo | base for `source_path` / `asset_path` | no refusal: a wrong base yields a bad path; the caller sees a missing file when it opens it. The byte-identity test panics naming the entry (`carried.rs:112-128`) |
| `HOME` | `cli.rs:238` | none | expands a leading `~/` in `@file` values | if unset, the path is used literally; the read then fails with `cannot read <path>: <os error>` (`cli.rs:245-253`) |
| `MOS_NICK` | `cli.rs:559` | empty string | nick printed by `register` | no refusal: an empty nick is accepted and prints `REGISTERED : …` |
| `PATH` | `git.rs:22-29` | system | locating the `git` binary | missing git → `GitError("git not found on PATH")` |
| `GIT_*` | inherited by `git.rs:22-29` | git's own | git's normal environment (identity, config) | a git failure surfaces as `git <args> failed: <stderr tail>` (`git.rs:31-39`) |

## CLI flags

Parsed by `run_cli` (`cli.rs:538-695`). All are long-form only; `--flag=value` and
`--flag value` are both accepted (`cli.rs:490-505`). Repeated flags: the **first** value is used
(`cli.rs:562`, `:590`).

| Flag | Command | Default | Meaning | Refusal when wrong |
|---|---|---|---|---|
| `--caps` | register, worker | none / `""` | comma-separated capabilities | `register` without it → usage, exit 2 (`cli.rs:547-549`) |
| `--dm` | register, worker | `""` | DM dead-drop secret | never refused; parsed and (for `worker`) discarded |
| `--roles` | register, worker | `""` | roles string | never refused |
| `--max-jobs` | register | `1` | integer | non-integer → usage, exit 2 (`cli.rs:552-556`) |
| `--title` | dispatch | none | job title | missing → usage, exit 2 (`cli.rs:576-579`) |
| `--spec` | dispatch | none | text or `@file` | missing → usage exit 2; unreadable `@file` → `ERROR: cannot read …`, exit 1 (`cli.rs:318-325`) |
| `--accept` | dispatch | `""` | text or `@file` | unreadable `@file` → exit 1, same path |
| `--req` | dispatch | `""` | required caps | never refused |
| `--room` | dispatch | `""` | room name | never refused |
| `--lease` | dispatch | `1800` | integer seconds | non-integer → usage, exit 2 (`cli.rs:592-596`) |
| `--branch` | dispatch, review, merge | `""` / required | branch name | review/merge missing → usage, exit 2 (`cli.rs:666-668`, `:680-682`) |
| `--base` | dispatch, review, merge | `""` / `"main"` | base branch | never refused (an unknown base reaches the git guard) |
| `--repo` | tick, verify, review, merge | none | repo path | review/merge missing → usage exit 2; tick/verify optional |
| `--workdir-base` | tick, verify | none | workdir root | never refused |
| `--workdir` | worker | `"."` in Python; **discarded** in Rust | worker workdir | parsed, then ignored (`cli.rs:638-641`) |
| `--once` | worker | false | single cycle | absent → loop mode, stderr + exit 2 (`cli.rs:650-654`) |

Not accepted at all: `-h`, `--help`, short flags, and argparse-style abbreviations. Any of them
is an unknown positional/flag → usage, exit 2.

## Files read

| File | Read at | When | Refusal |
|---|---|---|---|
| `@<path>` spec/accept, `~/` expanded | `cli.rs:235-254` | `dispatch` | `ERROR: cannot read <path>: <err>`, exit 1 |
| `<repo>/os/<entry>` for all 47 manifest entries | `carried.rs:91-95` | tests only | test panic naming the entry |
| `<crate>/assets/<entry>` for all 47 entries | `carried.rs:97-101` | tests only | test panic naming the entry |
| The git repository named by `--repo` | `git.rs:20-126` | `review`, `merge` | `not a git repo` (review), or a `git status` failure (merge) |

## Config the crate does not have

No config file, no dotfile, no port, no socket, no timeout setting. The only tunable behaviour
is the git binary on `PATH`; there is no way to point the crate at another git executable.
