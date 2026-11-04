# BUILD_LOG — Goose toolchain + hello (Lane B B1–B2, R5, 2026-11-04)

## B1. Toolchain discovery (tried in order, first hit wins)

1. `command -v goose` → `/opt/homebrew/bin/goose` — HIT, search stops here.
2. `/opt/homebrew/bin/goose` — same binary as (1), not separately needed.
3. Hard-coded path in `services/run-goose-tests.sh` (old):
   `/Users/test/mcp-servers/toolchains/goose-src/build/goose` — EXISTS
   (`-rwxr-xr-x`, 9319256 bytes, 2026-11-01), same version as (1).
   Replaced by discovery in B3 anyway (one-machine path).
4. Fresh clone of `aardappel/goose` built with cmake — NOT PERFORMED:
   a working toolchain was found at step 1, so there was nothing to build.

Record:

- Path: `/opt/homebrew/bin/goose`
- Version: `goose b781587 (runtime 3901ec457ba9)`
  (`/opt/homebrew/bin/goose --version`)
- Toolchain (`/opt/homebrew/bin/goose toolchain`):
  `C compiler: clang 21.0.0, found on PATH (/usr/bin/cc)`,
  `C++ compiler: /usr/bin/clang++`, `cmake: /opt/homebrew/bin/cmake (4.4.4)`,
  `git: /usr/bin/git (2.54.0)`, `built in: physics, gfx, audio, ui`,
  `GOOSE_HOME: /Users/test/.goose`

## B2. hello compiles and runs (gate)

Command (from `services/`):

```
$ /opt/homebrew/bin/goose run hello/hello.goose
```

Output:

```
HELLO FROM GOOSE
```

Exit: 0. Source: `services/hello/hello.goose` (`fn main() { print("HELLO FROM GOOSE"); }`).
No mocks, no fixtures: the real compiler ran the real file on this host.
