# Root manifest — what is the OS, what is a program

Written 2026-11-02 because the root README and several status files still mix the two, and
the boss's rule is blunt: the OS is the kernel and its layers; everything else is a program
that runs on it, and nothing may be described as the OS that is not.

Rule of thumb used here: **if the kernel would have to load it to boot, it is the OS.** If it
is an application a user or agent opens after boot, it is a program. A program that has not
been ported to run on our kernel is a program on the host until that port exists, whatever the
README says.

## The OS (layers 1-6)

| Path | Layer | What it is | Evidence |
|---|---|---|---|
| `kernel/` | 1-3 | Boot entry, memory, paging, heap, scheduler, traps, syscalls, VGA console, keyboard, timer. `kernel/src` is Rust, `no_std`. | Builds and boots: `kernel/BUILD_LOG.md`, logs in `os-build/logs/` |
| `services/` | 4 | 25 Goose services and 18 shared libraries — supervisor, logd, fs, storage, time, net, shell, agenthost, callmatrix | Runs as host processes: `os-build/layer1/SERVICE_RUNS.md` (33 programs, 0 fails). **Not booted on the kernel.** |
| `services/common/` | 4 | Shared Goose libraries (args, cfg, fmt, json, sys, syscall surface) | Same host runs |
| `services/tests/` | 4 | 33 Goose test programs (t76-t93 and the limit suites) | `os-build/layer1/check_services.sh` |
| `lobster/` | 5-6 | Agent-layer programs and the Lobster shim/budget/agent-call surfaces | Host-side only; see `os-build/LAYERS.md` |
| `agents/` | 5 | The Node agent runtime, watchman, baton, registry, room-1 bus | `node --test tests/agents-*.test.mjs` |
| `mcp-gateway/`, `relay/` | 4-5 | MCP backend registry and Meta Nuntius, the product's own messaging relay | Host processes; not kernel-managed |
| `aegis/` | 7-adjacent | Security tooling (sweep, surface checks, manifests) shipped with the OS image | `node --test tests/aegis-*.test.mjs` |
| `crates/os-*` | 4-5 | Rust service crates: supervisor, identity, jobs, memory, budget, workspace, worker, misc, boot assets | `cargo test --workspace` |
| `os-build/` | — | Build system, specs, gates, logs, evidence. Not shipped as a runtime component | This directory |
| `os/` | 4 | The earlier OS tree the Rust/Goose work replaces; still referenced by some harnesses | Mixed; do not cite as the kernel |

## The programs (layer 7)

These are applications. They are real and they are tested, and none of them boots on our
kernel yet.

| Path | Program | Today |
|---|---|---|
| `js/`, `index.html`, `styles.css` | Imperium console (camera, sampler, assess client) | Working on the host |
| `server/` | Imperium server, assess endpoint, queue | Working on the host |
| `eval/`, `test-footage/` | Evaluation sets and frame packs | Test data, never shipped |
| `site/` | The public site | Static |
| `native/` | macOS app shell hosting the console | Host app |
| `board/` | The board surface (agent messaging face) | Host surface |
| `design/`, `docs/` | Design assets and documents | Not runtime |
| `intel/`, `nervus/` | OSINT/intel tooling and the model-surgery bench | Host tooling |
| `labs/`, `hortus-rung3/`, `handsfree/`, `vendor/`, `tools/` | Labs and support code | Host tooling |

## What this manifest corrects

1. **The root README's "OS image" row** claimed a bootable disk image with zero failed units.
   That image was a stock Debian carrier, which `KERNEL_SPEC.md` rule 1 forbids as product.
   The OS is `kernel/` plus the layers above; the Debian image is a development carrier only.
2. **The Goose services are not "the OS" and are not booted.** They are the systems layer,
   written and run as host processes with five syscalls deliberately refused
   (`os-build/layer1/host/host_shim.c`). Calling that "the OS" is the exact confusion this
   file exists to stop.
3. **`os/` is not the kernel.** It is the earlier tree; `kernel/` is the kernel.
4. **No program is ported to the kernel yet.** Every row in the programs table runs on the
   host. That is not a defect to hide; it is the next port.
