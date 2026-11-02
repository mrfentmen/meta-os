# build — Round 11 record

Source: **none** — `services/build/` contains only `.gitignore` (`*` then `!.gitignore`) ·
Test: **none, and none is possible** · Status: NOT A SERVICE

## 1. Limits — NOT APPLICABLE

There is no code in this directory. R11-025..030 ("deepen services/build") assume a service that
does not exist. `services/BUILD.md` is the build *recipe* document, and `services/build/` is the
generated-output directory that recipe writes into: `goose -o build/<svc>.c`, then `.o`, then
`.elf`. Generated C is not source and is deliberately not committed.

**FINDING:** the Round 11 list treats `services/build` as a service. It is a build artifact
directory. Either the list is wrong or a build service is planned and unstarted; either way a
limits test here would test nothing.

## 2. Refusals — NOT APPLICABLE

No callable surface. The only refusal this directory has is `.gitignore`'s: everything except
itself is untracked.

## 3. Restart — NOT APPLICABLE

Nothing runs, so nothing restarts. A build is a one-shot command from `services/BUILD.md`; it has
no supervisor entry and no state.

## 4. Contract — NAMED GAP

| direction | other | call | in the matrix? |
|---|---|---|---|
| out | the Goose toolchain | `goose -o`, `clang`, `ld` | n/a — host tools, not services |
| out | none | — | no `SVC_BUILD` id exists |

No service id, no matrix row, no entry point. Recorded rather than invented so the next reader
does not go looking for a module.

## 5. Load — NOT APPLICABLE

No driver to load. `os-build/layer1/run_native.sh` builds and runs the tests, and its output
directory is this one — the load it carries is the corpus's, not a service's.

## 6. README truth pass — PROVEN

There was no README, which is exactly how a build directory gets mistaken for a service. Added
`services/build/README.md` stating what the directory is, what writes it, and that it is not part
of the service corpus; `services/build/.gitignore` now keeps that README (`!README.md`) while
still ignoring every generated artifact. `services/BUILD.md` remains the authority on the recipe.
