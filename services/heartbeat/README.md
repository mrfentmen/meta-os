# heartbeat — a one-beat-per-second daemon

**Not a library.** This is an entry-only Goose program: it defines `main` and imports
`os`, so a test cannot import it without colliding with its own `main`. There is no host
driver for it, and the Round 11 record at `os-build/layer1/r11/heartbeat.md` says so
instead of inventing one.

## What it does

Once per second it appends the bare token `beat` to `heartbeat.log` in the working
directory, then sleeps. It stops after **3,600 beats** (one hour at that interval), or
earlier when a file named `STOP` exists — checked before every beat. On a stop it prints
`daemon stopping cleanly`.

There is no signal API in the Goose stdlib, so the sentinel file is the documented stop
mechanism, not a placeholder for one.

## What it does not do

- It writes **no timestamp** and no newline of its own. The header comment in
  `heartbeat.goose` says "timestamped line"; the code appends the token `beat`, and that
  comment is wrong.
- It is not in the call matrix, deliberately: `callmatrix_audit.py` lists `heartbeat` in
  `NOT_SERVICES` alongside `hello`, `echo` and `mcp-host`. It calls no service and no
  kernel syscall — only `os` file and stdio calls.
- It is not a supervised service today. There is no supervisor entry and no restart drill.

## Running it from this directory

A committed `STOP` file sits beside the source. Running the program from
`services/heartbeat/` therefore exits immediately with `daemon stopping cleanly`. Remove
or rename `STOP` first if you want beats.
