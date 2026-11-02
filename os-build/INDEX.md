# os-build index — where the truth lives

One line per artifact, grouped by what question it answers. If a document is not here and it
makes an OS claim, it is either historical or wrong; `OS_STATUS.md` is the page to trust first.

## Start here

| File | Answers |
|---|---|
| `OS_STATUS.md` | one page: what the OS is, what is proven, what is missing |
| `KERNEL_STATUS.md` | the milestone matrix with the artifact behind each mark |
| `SCOREBOARD.md` | layer-by-layer status against artifacts |
| `ROOT_MANIFEST.md` | what is the OS and what is a program, path by path |

## Kernel

| File | Answers |
|---|---|
| `../kernel/BUILD_LOG.md` | toolchain, bootloader, image hash, QEMU command, capture traps |
| `../kernel/README.md` | how to build and boot, and what that does not prove |
| `../kernel/MAC_QUESTIONS.md` | what the Mac build answered, and what only hardware can |
| `QEMU_LIMITS.md` | what a QEMU boot cannot prove |
| `logs/` | the serial logs and VGA captures named by every claim |
| `logs/BOOT_DIFF.md` | K1 vs K7, structurally: zero regressions |

## Boot and services

| File | Answers |
|---|---|
| `layer1/BOOT_ORDER.md` | the 22-service sequence and its dependencies |
| `BOOT_MANIFEST.md` | what each loss costs; effective fatality through the cascade |
| `boot-manifest.json` | the same as data, for the image lane |
| `SERVICE_FAILURE_TABLE.md` | per service, what its contract says about its absence |
| `../services/MANIFEST.md` | the services, libraries and their status words |

## Userspace

| File | Answers |
|---|---|
| `USERSPACE_ABI.md` | the six calls, arguments, returns, refusals, findings |
| `USERSPACE_PROGRAMS.md` | each program, its expected log lines, its status |
| `proposals/` | changes that belong to another lane, with owners |
| `ROWAN_PROPOSALS.md` | kernel-lane proposals and the disclosure of what already landed |

## Records (code read, line by line)

| File | Answers |
|---|---|
| `records/fault-path.md` | what a fault does, ring 0 vs ring 3, double fault |
| `records/memory-allocator.md` | the bitmap allocator's guarantees and gaps |
| `records/task-lifecycle.md` | states, ids, stacks, spawn/exit/reap |
| `records/syscall-path.md` | trap to dispatch to return, register by register |
| `records/boot-sequence.md` | kernel init order, and why it is that order |
| `records/console-shell.md` | the shell task, its commands and refusal behaviour |

## Verification

| File | Answers |
|---|---|
| `layer1/README.md` | what each check proves, and what it does not |
| `layer1/check_all.sh` | the one command and its exit code |
| `CLEAN_CLONE.md` | does `main` build from nothing but itself |
| `layer1/test_checkers.sh` | proof that the checkers fail when they should |

## Specs and plans

| File | Answers |
|---|---|
| `../KERNEL_SPEC.md` | the kernel's authority, milestones and syscall table |
| `KERNEL_BUILDOUT_SPEC.md` | what the kernel still needs, in order |
| `LAYERS.md` | the seven layers |
| `../OPENCODE_OS_BUILD.md` | the 240-task build list for the Mac lane |
