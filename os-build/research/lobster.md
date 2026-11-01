# Lobster research (OS-167)

Sources: lobster-mcp 1.1.0 (upstream @ 6c1389c6e2: 187 doc
sections across 14 documents, 879 builtins, 45 keywords, 18
samples) + the live interpreter build below.

## What it is

A language by Wouter van Oortmerssen (strlen.com/lobster):
statically typed with inference (`var a = 1`), multiple return
values, strict nil handling, vectors akin to resizable lists.
Runs through its own interpreter/VM (`bin/lobster`); game and
engine samples dominate, but the language is general-purpose.

## How a script runs

`lobster script.lobster` through the interpreter built from
https://github.com/aardappel/lobster (`cd dev && cmake
-DCMAKE_BUILD_TYPE=Release && make -j8`, binary at
`bin/lobster`). Cheat sheet (`get_cheatsheet`) covers C-style
carryover; samples cover subprocess/threads/binary/textinput.

## What the agent layer needs from it (to verify against the
interpreter, OS-169..176)

File read/write (memory), timers or sleep (scheduling), process
or socket IPC (bus), stdout + exit codes (shim proofs). Gaps vs
workarounds go in the Section L report block — stated, not
assumed. Interpreter build state: cloned shallow 2026-11-01,
built on this Mac (versions in the report).
