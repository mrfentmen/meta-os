// OS-061: one page on why the first scheduler is cooperative round-robin.
//
// A preemptive scheduler switches tasks inside the timer interrupt,
// which means the switch can land mid-`Heap::alloc`, mid-serial-write,
// or mid-VGA-write with no locking anywhere. This kernel has no locks
// yet (no spinlock, no critical sections), so preemption today would
// corrupt the heap or interleave console bytes. Cooperative tasks
// switch only at `yield` points the code chose, so every switch
// happens between critical sections, never inside one. Priorities
// exist in `tasks.rs` but all K5 tasks spawn at 0: pure round-robin.
// Preemption (quantum expiry in the timer IRQ) waits for locks.

## OS-073: what this scheduler cannot do (honest list)

- No preemption: the timer IRQ only counts; a task that never
  yields keeps the CPU forever. Found live during testing: with the
  wake pass only in the run loop, a lone running task starved the
  sleeper — fixed by waking on every scheduling decision, but a
  never-yielding task still rules. Locks + quantum expiry come later.
- No priorities in effect: all tasks spawn at 0 (pure round-robin);
  `quantum_ticks` is set to `u32::MAX` and never expires.
- No reaping: exited tasks keep slot + leaked stack until a K6
  reaper frees them. Four demo tasks fit; a task farm would not.
- No blocking on anything but sleep: no IPC waits, no I/O waits.
