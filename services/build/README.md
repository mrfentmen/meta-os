# `build` — generated output, not a service

This directory holds build artifacts: the `.c`, `.o` and `.elf` files produced when a service is
compiled. It is **not** a Layer 4 service, it has no `*.goose` source, no entry point, no matrix
id and no test. Everything here is ignored by `.gitignore` (`*`, with `!.gitignore` and
`!README.md`); generated C is a build output, and committing it would make the repository's diff
lie about what changed.

The recipe that writes here — `goose -o`, then `clang -ffreestanding`, then `ld -T` — is in
[`../BUILD.md`](../BUILD.md). The corpus runner that produces most of these files is
`os-build/layer1/run_native.sh`, which builds into `os-build/layer1/host/build`, not here.

If you are looking for a build *service* (a service that performs builds on behalf of the OS),
there is not one: no `services/build/*.goose` exists and no `SVC_BUILD` id is defined. Round 11's
items R11-025..030 assume one, which is why `os-build/layer1/r11/build.md` records the mismatch
instead of a limits test.
