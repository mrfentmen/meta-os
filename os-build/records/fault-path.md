# Record — the fault path, from the code

Scope: what happens when the CPU faults, in the kernel that exists on `main` today. Every
claim cites the file and line range it came from. Code wins over older documents; where they
disagree, the disagreement is listed at the end.

## Kernel-mode fault

1. The CPU pushes its frame and the vector's trampoline in `kernel/src/traps.rs` saves the
   scratch registers, passing `(vector, &frame, error_code)` to `dispatch_trampoline`.
2. `interrupts::dispatch` (`kernel/src/interrupts.rs`, dispatch table around line 300) looks up
   the registered handler for that vector. If none, it prints
   `INT unhandled vector 0x<v> ip 0x<ip>` and **returns**, which means `iretq` resumes the
   faulting instruction. For a genuinely unexpected vector that is a re-fault loop, not a
   recovery. (Stated because it is a real property, not a hypothetical: the double-fault
   handler had exactly this shape and produced a 3.3 MB log until 2026-11-02.)
3. Registered exception handlers (`kernel/src/interrupts.rs`, `print_exception` and the
   per-vector functions) print name, vector, `ip`, and the error code when the CPU pushes one
   (`has_error_code` covers 8, 10-14, 17, 21, 29, 30).
4. **Double fault** (`kernel/src/interrupts.rs`, `double_fault_handler`): prints once, then
   `INT double-fault: halting` and a `hlt` loop. There is no return path, deliberately — a
   double fault has no recovery, and returning re-faults forever. Verified 2026-11-02:
   `os-build/logs/K16-doublefault-fixed.txt` is 1,134 bytes with one double-fault line; the
   previous handler's log was 3.3 MB of the same line (`K3-doublefault.txt`).

## Ring-3 fault

`page_fault_handler` (`kernel/src/interrupts.rs`, lines 467-500) reads **CR2** for the faulting
address, then branches on `frame.code_segment & 3 == 3`:

- **Ring 3:** prints `INT user page-fault addr 0x... err 0x...: task killed` and calls
  `sched::exit_task()`. The task never resumes; the kernel and every other task continue.
  Evidence: `K1-boot.txt` / `K6-boot.txt`, `crasher: about to read zero` followed by the kill
  line and task A/B continuing.
- **Ring 0:** prints the exception detail and returns. That return resumes the faulting
  instruction, so a kernel page fault repeats. This is the same shape as finding 1: the kernel
  has no "panic on kernel fault" policy yet, and a real one should halt rather than loop.

## What `exit_task` does

`kernel/src/sched.rs`, lines 174-190: wakes expired sleepers, asks the scheduler to exit the
current task, switches to the next ready task if there is one, otherwise switches back to the
scheduler context. The exited slot is marked `Exited` and never resumed. `ps` in the shell
reports those states (`K7-boot.txt` shows six `Exited` rows and one `Running`).

## The timer is not part of this path

Sleep deadlines are checked in `wake_expired` (`kernel/src/sched.rs`, lines 191-200) from the
scheduler loop, not from the timer IRQ: the IRQ only increments `TICKS`. A fault therefore
cannot race a wake-up inside interrupt context, because no wake-up happens there.

## Disagreements found

1. `kernel/src/interrupts.rs`'s module header still says the module is **UNWIRED** and
   **UNCOMPILED**. It is wired in `main.rs` and proven by boot logs. The header is stale and
   is Rowan's file to correct (kernel/src is his lane).
2. The header also says "UNVERIFIED ... no boot log exists", which contradicts
   `os-build/logs/` from 2026-11-02.
3. Kernel-mode page faults have no halt policy (see above); the older failure documents assume
   a kernel fault is fatal, which today it is only in the sense that it loops.
