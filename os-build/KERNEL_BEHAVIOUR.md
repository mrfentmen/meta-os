# Kernel behaviour, read from the code (Bond lane 3, 2026-11-02)

Every claim names a file and line range on `main` at the time of
writing. This is a record of what the code does, not a claim that it
has run; boot evidence lives in `os-build/logs/` and is indexed in
`os-build/BOOT_LOG_INDEX.md`. Where an older document disagrees with
the code, the disagreement is under **Findings**; kernel files are
Rowan's write lane and nothing here edits them.

## 1. Boot order

`kernel/src/main.rs:128-190` is the whole sequence:

| Step | Line | What happens |
|---|---|---|
| serial + VGA console | `main.rs:129-140` | UART and 80x25 text console come up |
| banner | `main.rs:142-143` | `META OS 0.1 (K6)` then `META OS KERNEL - alive (K1)` |
| GDT + TSS | `main.rs:147` | `gdt::init()` |
| handlers + gates | `main.rs:149-151` | `register_builtins()`, `traps::install()`, layout assert |
| PIC + PIT + IDT | `main.rs:152-158` | `cli`, remap to 32/40, 100 Hz, `lidt`, `sti` |
| timer proof | `main.rs:159` | `prove_timer()` waits for 10 real ticks |
| memory | `main.rs:163-165` | `mem::mem_init(boot_info)` |
| scheduler | `main.rs:181-184` | `sched_init()`, `start_demo_tasks()` — never returns |

The banner is printed before the GDT and IDT exist, which is why the
first lines of every boot log appear even when a later stage fails.
`prove_timer` is a measurement, not a canned print: it reads the
handler's `TICKS` counter and is bounded (`main.rs:193-218`).

## 2. Allocator

Two allocators share one memory map: frames (page granularity) and a
linked-list heap (`alloc`'s `GlobalAlloc`).

### 2.1 Frames

- Frame count comes from the bootloader map, converted to
  `MemoryRegion`s: `kernel/src/mem.rs:127-190`. Region types are
  mapped `Usable` / `Reserved` / `Other` (`mem.rs:106-116`).
- Bitmap storage: 2048 `u64` words = 131,072 frames = 512 MiB of
  addressable RAM (`mem.rs:27-29`). A frame beyond that is not
  covered; `covered_frames()` reports the difference
  (`kernel/src/memory.rs:386-394`).
- Allocation is first-fit over the bitmap, deallocation clears the
  bit and refuses a frame that is not currently allocated:
  `memory.rs:353-480` (`allocate` at `:409-431`, `deallocate` at
  `:432-480`).
- The mapper owns the allocator (`memory.rs:561-600`), so a page table
  and a user page come from the same free pool. `mem_init` proves one
  fresh mapping with a write/read-back before trusting it
  (`mem.rs:205-230`).
- `mem`/`status` read the same counters, not copies:
  `frames_total()` (`mem.rs:290-300`), `frames_free()` (`:302-306`).

### 2.2 Heap

- Backing store is a static 512 KiB buffer inside the kernel image
  (`mem.rs:22-26`), deliberately marked `Kernel` in the map so the
  frame allocator cannot hand it out.
- Initialised as the global allocator at `mem.rs:219-221`; `Box` and
  `Vec` are proven immediately after (`mem.rs:222-230`), then a
  10,000-allocation stress (`mem.rs:232-241`).
- Allocation is a first-fit linked list with block splitting; free
  coalesces adjacent blocks (`memory.rs:783-950`, `alloc` at
  `:852-928`, `dealloc` at `:929-...`).
- Exhaustion is not a panic: `alloc` returns a null pointer
  (`mem.rs:60-66`), which `Box`/`Vec` turn into the standard
  allocation failure. The global allocator is a `static mut` behind
  a `Sync` shell justified by single-CPU + no allocation in IRQs
  (`mem.rs:44-51`).
- The heap is why `MAX_TASKS` is 8: each task stack is a 16 KiB
  `Box` (`kernel/src/sched.rs:21-25`, `:218-232`), so roughly 128 KiB
  of the 512 KiB is stacks before any other allocation.

### 2.3 Why 512 KiB and not 256 KiB

The source records the measurement: 256 KiB ran dry at the 8th task
(`mem.rs:20-24`). That is a real observed limit, not a guess.

## 3. Task lifecycle

Two files split the work: `tasks.rs` owns identity, state and policy;
`sched.rs` owns the stacks, the context switch and the run loop.

### 3.1 States

`TaskState` is `Ready`, `Running`, `Blocked`, `Exited`
(`kernel/src/tasks.rs:142-160`). Rules the code enforces:

- `Ready` is the only state the picker considers
  (  `tasks.rs:466-490`, `Task::is_ready` at `:350-352`).
- `Blocked` is never picked; only `unblock` moves it back to `Ready`,
  and only for a task that is currently `Blocked` (`tasks.rs:626-640`).
- `Exited` keeps its slot until `reap` frees it; `reap` refuses a
  live task (`tasks.rs:642-676`).
- `INVALID_ID = 0` is never handed out; ids start at 1 and the counter
  skips 0 on wrap (`tasks.rs:110-111`, `:443-465`).

### 3.2 Spawn

- `Task::new` refuses: invalid id, zero quantum, invalid stack, zero
  entry, misaligned stack top (`tasks.rs:301-368`).
- `Stack::new` refuses: zero size, non-page-multiple size, overflow,
  misaligned top (`tasks.rs:238-290`).
- `sched::spawn_task` refuses at 8 live rows
  (`sched.rs:218-220`), allocates a 16 KiB stack from the heap
  (`:221-224`), and records context, id, entry, sleep slot and kernel
  stack top in parallel arrays (`:225-238`).
- `start_demo_tasks` spawns seven tasks: A, B, C, hello, sleeper,
  crasher, console (`sched.rs:650-662`). That is exactly the
  `STATUS tasks=7` seen in the logs, with one table slot spare.

### 3.3 Switch and scheduling

- The switch is raw assembly that saves/restores callee-saved
  registers, `rsp`, `rip` and `rflags`
  (`sched.rs:75-107`). It changes execution; the policy functions
  below only change table state.
- Policy (`tasks.rs:388-720`): highest priority wins; equal priorities
  rotate from just after the current task (`pick_next` at `:466-490`,
  `yield_now` at `:592-608`). `schedule` only preempts for a strictly
  higher priority (`:542-590`). `block_current`, `exit_current` and
  `reap` are the lifecycle transitions (`:610-676`).
- Every demo task is spawned at priority 0 with `quantum = u32::MAX`
  (`sched.rs:652-661`), so the running policy is pure round-robin.
- **No preemption runs today.** `timer_handler` only increments
  `TICKS` and sends EOI (`kernel/src/interrupts.rs:502-512`); it never
  calls `on_timer_tick`. `tasks.rs:678-710` implements quantum
  preemption, but nothing in `sched.rs` invokes it and the quantum is
  `u32::MAX` anyway. The scheduler is cooperative: switches happen
  at `yield`, `sleep`, `exit`, and the run loop
  (`sched.rs:141-190`, `:262-281`).
- Sleep is wall-clock by tick, not a timer queue: a deadline is stored
  per task (`sched.rs:154-163`) and `wake_expired` scans the table on
  every scheduler pass (`:191-201`). A sleeping task therefore wakes
  on the next scheduler decision after its deadline, not in the IRQ.
- The run loop `hlt`s only when nothing is ready (`sched.rs:262-281`).

### 3.4 Refusals in the lifecycle

| Request | Refusal | Where |
|---|---|---|
| spawn past 8 rows | `None` | `sched.rs:218-220` |
| spawn with bad stack/quantum/entry | `None` | `tasks.rs:301-368` |
| unblock a task that is not `Blocked` | `false` | `tasks.rs:626-640` |
| reap a task that is not `Exited` | `false` | `tasks.rs:642-656` |
| schedule with nothing ready | `None`, `current` cleared | `tasks.rs:578-590` |

No path invents a task or a fake id.

## 4. Fault path

### 4.1 Ring-0 faults

- Wired vectors: 0, 1, 3, 6, 8, 10-14, 32, 33
  (`kernel/src/traps.rs:19`). The error-code set is asserted against
  `interrupts::has_error_code` at `traps.rs:195-201`.
- Each handler prints a real line with vector, `rip`, and (when the
  CPU pushed one) the error code: `interrupts.rs:415-427`, handlers at
  `:429-465`.
- Double fault prints once and halts forever
  (`interrupts.rs:445-461`). Returning was the old behaviour and
  produced a 3.3 MB repeating log (comment at `:449-460`).

### 4.2 Ring-3 faults

- `page_fault_handler` reads CR2 for the fault address (the CPU does
  not push it): `interrupts.rs:467-480`.
- If the fault came from ring 3 (`frame.code_segment & 3 == 3`), it
  prints
  `INT user page-fault addr 0x... err 0x...: task killed`
  and calls `sched::exit_task()` — it never `iretq`s back into the
  faulting context (`interrupts.rs:481-492`).
- The scheduler then runs the next ready task; the console task keeps
  answering. The observed line is in
  `os-build/logs/MERGED-boot-2.txt:45`.
- A ring-0 page fault falls through to the ordinary exception print
  (`interrupts.rs:493-500`); there is no recovery path.

### 4.3 Syscall faults

The syscall handler validates the write buffer before touching it:
`crate::mem::is_mapped_range` walks every covering page
(`kernel/src/mem.rs:308-330`) and the handler refuses with
`u64::MAX` instead of faulting the kernel (`kernel/src/user.rs:140-143`).
The full call table is in `os-build/USERSPACE_ABI.md`.

## 5. Findings — older docs that disagree with the code

Reported for their owners; nothing below was edited.

1. **`tasks.rs`'s header is stale about wiring.** It says
   "WRITTEN, NOT WIRED INTO `main.rs` ... NOT A CONTEXT SWITCH THAT
   HAS EVER RUN" (`kernel/src/tasks.rs:1-18`). The code now wires it:
   `sched.rs` owns a `tasks::Scheduler` in a static
   (`sched.rs:45-47`), calls `spawn`, `yield_now`, `block_current`,
   `exit_current` (`sched.rs:141-190`, `:218-239`), and `main.rs`
   calls `sched_init` + `start_demo_tasks` (`main.rs:181-184`). The
   header's status words describe an earlier commit and should be
   brought current by Rowan.
2. **The same header says `kernel/Cargo.lock` is absent.** It is
  committed in the tree (`kernel/Cargo.lock` exists on `main`). The
  header's "404 on the live main tip" note (`tasks.rs:21-27`) is
  stale.
3. **`gates.md` says "K7: NO LOG"** (`os-build/gates.md:20`), but
   `os-build/logs/K7-boot.txt` exists (74 lines) and is quoted as the
   shell-alignment target by `os-build/layer1/K7_ALIGN.md:1-13` and
   `SCOREBOARD.md:18`. What does *not* exist is a K7 milestone banner:
   the file's first lines are `META OS 0.1 (K6)` /
   `META OS KERNEL - alive (K1)` (`K7-boot.txt:1-2`). The gate line
   should say "no K7 *banner*", not "no log".
4. **`boot-test.sh` greps the wrong banner string.** Its "K2 banner"
   check is `checkline "K2 banner" "META OS - milestone K3"`
   (`os-build/boot-test.sh:52`), while `main.rs:142` prints
   `META OS 0.1 (K6)`. `FREEZE_CERT.md:41-42` already flags this;
   the code still disagrees, so the check cannot pass on a current
   build.
5. **`os-build/logs/MERGED-boot.txt` is empty.** Zero bytes; it proves
   nothing and should be either filled or deleted by its owner.
6. **`K3-doublefault.txt` is 34,270 lines** while the current handler
   halts after one line (`interrupts.rs:445-461`). The long log
   predates that fix; `K16-doublefault-fixed.txt` (29 lines) is the
   post-fix shape. Do not cite the 34k file as current behaviour.
7. **`readkey` imports a wrapper that does not exist.** See
   `os-build/USERSPACE_ABI.md` findings 1-2: `sys_read_key` is called
   but never defined, and `readkey` is not in `build.rs`'s bin list.
   Syscall 5 is live in the kernel, but no shipped userspace program
   exercises it.

## 6. What this record does not claim

- No compile and no boot is claimed here. Those come only from a
  named log or a gate run.
- The framebuffer (`kernel/src/framebuffer.rs`) is not described
  because it is not wired into `main.rs`; `os-build/face/KERNEL_FACE.md`
  owns that status.
- `kernel/src/syscalls.rs` is not described as behaviour: it is
  frozen and unwired (`os-build/PAX_12H.md` F1).
