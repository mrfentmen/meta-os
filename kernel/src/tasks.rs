//! Meta OS kernel, milestone K5: tasks and scheduling (UNWIRED).
//!
//! Status: **WRITTEN, NOT WIRED INTO `main.rs`, NOT A KERNEL-CRATE
//! COMPILE, NOT A BOOT VERDICT, NOT A CONTEXT SWITCH THAT HAS EVER
//! RUN.** This file is code, not a running scheduler, and no claim
//! is made that any task has ever executed on it or that any context
//! has ever switched. Per KERNEL_SPEC.md rule 2, it counts only when
//! it builds on the boss's Mac and a QEMU boot shows its behavior.
//! Per ROWAN_LAYER0_TASKS.md RW-L0-03, it is drafted unwired in the
//! R2/R3/K4 pattern, and per RW-L0-01 it is wired into `main.rs`
//! only onto the proven tree, one module per commit, after a K1 boot
//! log exists and `kernel/Cargo.lock` is committed (Q1). Until then
//! it is code, not a running kernel.
//!
//! Authority: boss layer order 2026-11-01 ~08:18, relayed by Pax on
//! room 1 and written into `os-build/LAYERS.md` +
//! `ROWAN_LAYER0_TASKS.md` on main: Rowan owns Layers 1-3 (boot,
//! kernel core, drivers; renumbered to seven layers on the boss's
//! word 2026-11-01 ~09:02, file name and RW-L0-03 ID kept as stable
//! identifiers), and RW-L0-03 assigns Rowan this K5 draft unwired,
//! written against what K4's draft exposes. `kernel/Cargo.lock` is
//! STILL absent on main (checked this run: 404 on the live main tip),
//! so there is still no resolved bootloader version to write
//! against. What this module does about that, honestly, following
//! the R2/R3/K4 precedent:
//!
//! - It does NOT import any bootloader type, any `x86_64` crate
//!   type, or any K4 type, and it does NOT depend on any external
//!   crate. Every structure below is local and uses `core` only, no
//!   `alloc`, so it cannot drag a dependency question into R5.
//! - It does NOT assert any bootloader API name, any interrupt or
//!   timer device name, or any context-switch instruction sequence.
//!   A context switch is not a Rust function call: switching stacks
//!   and restoring callee-saved registers plus `rip` requires an
//!   `asm` trampoline that a Rust `fn` cannot supply (the same
//!   honesty as the R3 IDT contract: no Rust `fn` address is ever
//!   asserted as a switch target). The R5 wiring commit supplies
//!   that trampoline, under the contract below.
//! - It is written against what K4's draft exposes, in the only way
//!   an unwired module honestly can: its stack and entry addresses
//!   are plain `u64` boundary values in K4's units (page-sized,
//!   `PAGE_SIZE = 4096`), and the wiring contract names the exact
//!   K4 items the R5 adapter maps them onto (`VirtAddr` for the
//!   entry and stack addresses, `FrameAllocator` for stack pages).
//!   No K4 name is imported here, so none can be wrong here; the
//!   adapter does the translation, and the adapter is R5's job.
//! - Stack memory is caller-supplied, exactly like K4's heap buffer.
//!   This module never claims stack memory the kernel does not own;
//!   where a stack comes from on the real machine (frames from
//!   K4's `FrameAllocator`, kept out of the heap's buffer) is Q11's
//!   business, and the R5 commit must say which frames it used.
//!
//! Check note (exact words): this module was checked on this VM with
//! standalone `rustc 1.99.1` (`rustc --edition 2021 --crate-type
//! lib`, host target, warnings denied) plus a host test harness in
//! `/tmp` (not shipped) exercising spawn validation, priority pick,
//! round-robin ties, quantum preemption, block/unblock, exit/reap/
//! respawn, and context/stack validation below. That is
//! standalone-clean plus host-exercised logic. It is NOT a kernel
//! crate compile (no `no_std` target, no bootloader crate linked),
//! NOT a context switch that has run, and NOT a boot verdict. The
//! Mac build + QEMU log remain the proof.
//!
//! Wiring contract (for the R5 commit): `main.rs` gains `mod tasks;`
//! and an `asm` trampoline that (a) saves the outgoing task's
//! callee-saved registers (`rbx`, `rbp`, `r12`-`r15`), stack pointer,
//! and flags into its `Context`, (b) restores the incoming task's
//! `Context` the same way, and (c) enters a first-run task through
//! its recorded `rip` with `rsp` at its stack top, built by the
//! initial-frame layout Q11 confirms. The scheduler's decisions
//! (`Scheduler::schedule`, `on_timer_tick`) are pure state changes
//! over the task table; the trampoline is the only part that moves
//! execution, and it does not exist until R5 writes it. This file
//! needs no other crate item.
//!
//! No mocks (KERNEL_SPEC.md rule 6): every function below moves
//! real task-table state or refuses. A spawn that cannot be
//! satisfied returns `None`, never a faked task. A switch decision
//! with no ready task keeps the current task running or reports
//! `None`; it never invents a task. A quantum that cannot be
//! honoured (zero ticks) is refused at spawn, never silently
//! treated as infinite.
//!
//! Safety contract (for the R5 commit and for callers generally):
//! the caller owns the task table and every stack range exclusively
//! while the scheduler lives. Stack ranges must not overlap each
//! other, the kernel image, or K4's heap buffer; this module checks
//! a single stack's own shape (non-empty, page-multiple size,
//! 16-byte-aligned top) but cannot see other owners' ranges, so an
//! overlapping stack is caller error and can corrupt memory. The
//! recorded `Context` values are data, not a guarantee: loading
//! them without the R5 trampoline's exact register discipline
//! (Q11) is undefined behaviour, not a switch.

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// One page: 4096 bytes, the same unit K4's draft uses. Stack sizes
/// in this module must be a multiple of this value.
pub const PAGE_SIZE: usize = 4096;

/// Stack-top alignment the entry boundary requires (SysV AMD64: the
/// stack pointer is 16-byte aligned when control first reaches a
/// function entry). `Context::initial` refuses a misaligned top
/// rather than recording a switch that would start misaligned.
pub const STACK_ALIGN: u64 = 16;

/// Invalid task id. Ids handed out start at 1; 0 is never a task.
pub const INVALID_ID: u64 = 0;

// ---------------------------------------------------------------------------
// Task identity and state
// ---------------------------------------------------------------------------

/// A task's identity. A plain `u64` wrapper: no scheduling policy is
/// hidden inside it, and id 0 is never handed out.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub struct TaskId(pub u64);

impl TaskId {
    /// Wrap a raw id.
    pub const fn new(id: u64) -> TaskId {
        TaskId(id)
    }

    /// The raw id.
    pub const fn as_u64(self) -> u64 {
        self.0
    }

    /// True only for ids this scheduler can hand out (non-zero).
    pub const fn is_valid(self) -> bool {
        self.0 != INVALID_ID
    }
}

/// Where a task is in its lifecycle. `Blocked` tasks are never
/// picked by the scheduler until `unblock` moves them back to
/// `Ready`; `Exited` tasks hold their slot until `reap` frees it.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum TaskState {
    /// Eligible to run; waiting for the scheduler to pick it.
    Ready,
    /// Currently the scheduler's running task.
    Running,
    /// Waiting on something outside the scheduler; not eligible.
    Blocked,
    /// Finished; slot held until reaped.
    Exited,
}

// ---------------------------------------------------------------------------
// Saved context
// ---------------------------------------------------------------------------

/// The register state a context switch must carry. These are the
/// callee-saved registers plus the stack pointer, the instruction
/// pointer, and the flags word: exactly the state the R5 `asm`
/// trampoline saves and restores, and nothing else. No value here
/// is ever executed by this module; it is data the trampoline
/// reads, and loading it any other way is not a switch.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Context {
    /// Saved stack pointer.
    pub rsp: u64,
    /// Saved base pointer (callee-saved).
    pub rbp: u64,
    /// Saved `rbx` (callee-saved).
    pub rbx: u64,
    /// Saved `r12` (callee-saved).
    pub r12: u64,
    /// Saved `r13` (callee-saved).
    pub r13: u64,
    /// Saved `r14` (callee-saved).
    pub r14: u64,
    /// Saved `r15` (callee-saved).
    pub r15: u64,
    /// Instruction pointer to resume at.
    pub rip: u64,
    /// Saved flags word.
    pub rflags: u64,
}

impl Context {
    /// All-zero context. Not a valid resume state on its own
    /// (`rip` 0, `rsp` 0); use `initial` for a first-run task.
    pub const fn zero() -> Context {
        Context {
            rsp: 0,
            rbp: 0,
            rbx: 0,
            r12: 0,
            r13: 0,
            r14: 0,
            r15: 0,
            rip: 0,
            rflags: 0,
        }
    }

    /// The context a task starts with: stack pointer at the stack
    /// top, instruction pointer at the entry address, callee-saved
    /// registers zero, flags with the interrupt-enable bit set
    /// (`0x202`: bit 1 always 1 on x86_64, bit 9 IF). Refused
    /// (`None`) when the entry is 0, the stack top is 0, or the
    /// stack top is not 16-byte aligned: a first switch built on
    /// any of those would start broken, so the refusal happens
    /// here, at spawn, not at switch time.
    pub const fn initial(stack_top: u64, entry: u64) -> Option<Context> {
        if entry == 0 || stack_top == 0 || stack_top % STACK_ALIGN != 0 {
            return None;
        }
        Some(Context {
            rsp: stack_top,
            rbp: 0,
            rbx: 0,
            r12: 0,
            r13: 0,
            r14: 0,
            r15: 0,
            rip: entry,
            rflags: 0x202,
        })
    }
}

// ---------------------------------------------------------------------------
// Stack
// ---------------------------------------------------------------------------

/// A task's stack range. The stack grows down: `bottom` is the
/// lowest address, `top` is one past the highest byte, and the
/// first-run stack pointer is `top`. The range is caller-owned
/// memory; this module never allocates it and never touches a byte
/// inside it.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Stack {
    /// Lowest address in the range.
    pub bottom: u64,
    /// One past the highest address in the range; the initial `rsp`.
    pub top: u64,
}

impl Stack {
    /// Build a stack range from a bottom address and a byte size.
    /// Refused (`None`) when the size is 0, not a multiple of
    /// `PAGE_SIZE`, the top overflows, or the top is not
    /// 16-byte aligned (it cannot be, given a page-multiple size
    /// and an aligned bottom, but the check stays explicit so a
    /// misaligned bottom is refused rather than silently kept).
    pub const fn new(bottom: u64, size_bytes: usize) -> Option<Stack> {
        if size_bytes == 0 || size_bytes % PAGE_SIZE != 0 {
            return None;
        }
        let size = size_bytes as u64;
        let top = match bottom.checked_add(size) {
            Some(top) => top,
            None => return None,
        };
        if top % STACK_ALIGN != 0 {
            return None;
        }
        Some(Stack { bottom, top })
    }

    /// Size of the range in bytes.
    pub const fn size(self) -> u64 {
        self.top - self.bottom
    }

    /// True when the range is non-empty and its top is aligned.
    /// (`new` already guarantees this; the check exists for stacks
    /// built literally, so a hand-built range is validated too.)
    pub const fn is_valid(self) -> bool {
        self.top > self.bottom
            && (self.top - self.bottom) % (PAGE_SIZE as u64) == 0
            && self.top % STACK_ALIGN == 0
    }

    /// True when `sp` lies inside the range (bottom inclusive, top
    /// exclusive of the one-past end only in the sense that `top`
    /// itself is the valid initial pointer; a running `rsp` must be
    /// strictly inside).
    pub const fn contains_sp(self, sp: u64) -> bool {
        sp >= self.bottom && sp <= self.top
    }
}

// ---------------------------------------------------------------------------
// Task
// ---------------------------------------------------------------------------

/// One task: identity, lifecycle state, scheduling parameters, the
/// context the trampoline will restore, and the stack it runs on.
/// Priority is a plain `u8`: higher wins, ties break round-robin.
/// `quantum_ticks` is the timer-tick budget a task runs before the
/// scheduler preempts it; zero is refused at construction, never
/// treated as "run forever".
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Task {
    /// Identity handed out by the scheduler.
    pub id: TaskId,
    /// Lifecycle state.
    pub state: TaskState,
    /// Scheduling priority; higher wins.
    pub priority: u8,
    /// Timer ticks this task may run before preemption.
    pub quantum_ticks: u32,
    /// Timer ticks this task has used in its current run.
    pub ticks_used: u32,
    /// Saved register state for the trampoline.
    pub context: Context,
    /// Caller-owned stack range.
    pub stack: Stack,
}

impl Task {
    /// Build a task in `Ready` state. Refused (`None`) when the id
    /// is invalid, the quantum is 0, the stack is invalid, or the
    /// initial context cannot be built (zero entry, misaligned
    /// stack top). The refusal is the spawn contract: no task is
    /// ever created in a state the trampoline cannot start.
    pub const fn new(
        id: TaskId,
        priority: u8,
        quantum_ticks: u32,
        stack: Stack,
        entry: u64,
    ) -> Option<Task> {
        if !id.is_valid() || quantum_ticks == 0 || !stack.is_valid() {
            return None;
        }
        let context = match Context::initial(stack.top, entry) {
            Some(context) => context,
            None => return None,
        };
        Some(Task {
            id,
            state: TaskState::Ready,
            priority,
            quantum_ticks,
            ticks_used: 0,
            context,
            stack,
        })
    }

    /// True when this task is eligible for the scheduler to pick.
    pub const fn is_ready(self) -> bool {
        matches!(self.state, TaskState::Ready)
    }
}

// ---------------------------------------------------------------------------
// Scheduler
// ---------------------------------------------------------------------------

/// The scheduler: a fixed caller-supplied table of task slots plus
/// the running-task pointer, the next id counter, and the tick
/// count. The table size is the task limit: no allocation, no
/// growth, and a spawn with no free slot returns `None` rather
/// than overwriting a live task.
///
/// Policy, stated exactly so a host test can pin it: among `Ready`
/// tasks the highest priority wins; among equal priorities the
/// scan starts just after the current task and wraps, so equal
/// tasks rotate (round-robin) instead of starving the later ones.
/// A decision point is one of three things, and they differ on
/// purpose: `schedule` is a priority decision — the running task
/// keeps running unless a `Ready` task has strictly higher
/// priority, so a spurious decision never demotes the best task;
/// `yield_now` and quantum expiry are rotation decisions within a
/// priority level — the running task's turn is over, so it goes
/// back to `Ready` and the best `Ready` task runs, with ties
/// rotating from just after the yielding task. Priority still
/// dominates across levels: a yield or a spent quantum never
/// promotes a lower-priority task over a ready higher-priority
/// one, so a lone highest-priority task resumes at once and a
/// lower-priority task waits — starvation under a busy higher
/// task is the documented property of fixed priority, not a
/// scheduler error, and no aging is implemented here. A task that
/// exhausts its quantum is preempted to `Ready` on the next timer
/// tick and its `ticks_used` resets. Nothing here moves
/// execution: `schedule`, `yield_now`, and `on_timer_tick` only
/// change table state and report which task the trampoline should
/// run next.
pub struct Scheduler<'a> {
    /// Caller-owned task table; `None` is a free slot.
    slots: &'a mut [Option<Task>],
    /// Index of the `Running` task, if any.
    current: Option<usize>,
    /// Next id to hand out (starts at 1, never 0).
    next_id: u64,
    /// Timer ticks seen since the scheduler was created.
    ticks: u64,
}

impl<'a> Scheduler<'a> {
    /// Create a scheduler over a caller-owned slot table. All slots
    /// should start `None`; any pre-filled slot keeps its task and
    /// counts against the table, which is caller error if the ids
    /// collide with `next_id` — the honest rule is that the caller
    /// passes an empty table, and `spawn` is the only writer.
    pub fn new(slots: &'a mut [Option<Task>]) -> Scheduler<'a> {
        Scheduler {
            slots,
            current: None,
            next_id: 1,
            ticks: 0,
        }
    }

    /// Number of slots in the table (the task limit).
    pub fn capacity(&self) -> usize {
        self.slots.len()
    }

    /// Number of live tasks (any state except a free slot).
    pub fn task_count(&self) -> usize {
        self.slots.iter().filter(|slot| slot.is_some()).count()
    }

    /// Timer ticks seen.
    pub fn ticks(&self) -> u64 {
        self.ticks
    }

    /// Id of the running task, if any.
    pub fn current_id(&self) -> Option<TaskId> {
        self.current
            .and_then(|index| self.slots[index].as_ref().map(|task| task.id))
    }

    /// Find a task by id, whatever its state.
    pub fn task(&self, id: TaskId) -> Option<&Task> {
        self.slots.iter().flatten().find(|task| task.id == id)
    }

    /// Create a task in the first free slot. Returns the new id, or
    /// `None` when the arguments are invalid (see `Task::new`) or
    /// no slot is free. Never overwrites a live task.
    pub fn spawn(
        &mut self,
        priority: u8,
        quantum_ticks: u32,
        stack: Stack,
        entry: u64,
    ) -> Option<TaskId> {
        let free = self.slots.iter().position(|slot| slot.is_none())?;
        let id = TaskId::new(self.next_id);
        let task = Task::new(id, priority, quantum_ticks, stack, entry)?;
        self.slots[free] = Some(task);
        self.next_id = self.next_id.checked_add(1).unwrap_or(1);
        if self.next_id == INVALID_ID {
            // Id counter wrapped past u64::MAX; 0 is never handed
            // out, so skip it rather than issuing an invalid id.
            self.next_id = 1;
        }
        Some(id)
    }

    /// Pick the next task to run without changing any state: the
    /// highest-priority `Ready` task, ties broken round-robin from
    /// just after the current task. `None` when no task is ready.
    pub fn pick_next(&self) -> Option<TaskId> {
        let start = self.current.map(|index| index + 1).unwrap_or(0);
        self.pick_next_from(start)
    }

    /// Same pick, but scanning from an explicit slot (used by
    /// `yield_now`, where the yielding task's slot is the
    /// round-robin origin even though `current` is already
    /// cleared). `start` may exceed the table length; it wraps.
    fn pick_next_from(&self, start: usize) -> Option<TaskId> {
        let len = self.slots.len();
        if len == 0 {
            return None;
        }
        let mut best: Option<(usize, u8)> = None;
        for step in 0..len {
            let index = (start + step) % len;
            if let Some(task) = self.slots[index].as_ref() {
                if task.is_ready() {
                    let better = match best {
                        // Strictly higher priority replaces the
                        // best; an equal priority keeps the
                        // earlier scan position, which is the
                        // round-robin order from `start`.
                        Some((_, best_priority)) => task.priority > best_priority,
                        None => true,
                    };
                    if better {
                        best = Some((index, task.priority));
                    }
                }
            }
        }
        best.map(|(index, _)| self.slots[index].as_ref().unwrap().id)
    }

    /// Run the picked task: the task with `id` becomes `Running`
    /// with a fresh tick counter, and `current` points at it. The
    /// caller must have decided `id` is the right task; this
    /// helper only performs the transition.
    fn run_task(&mut self, id: TaskId) -> Option<TaskId> {
        let index = self
            .slots
            .iter()
            .position(|slot| slot.as_ref().map(|task| task.id) == Some(id))?;
        if let Some(task) = self.slots[index].as_mut() {
            task.state = TaskState::Running;
            task.ticks_used = 0;
        }
        self.current = Some(index);
        Some(id)
    }

    /// Demote the running task to `Ready` (its `ticks_used`
    /// resets) and clear `current`. Returns `true` only when a
    /// task was actually demoted.
    fn demote_current(&mut self) -> bool {
        if let Some(index) = self.current {
            if let Some(task) = self.slots[index].as_mut() {
                if task.state == TaskState::Running {
                    task.state = TaskState::Ready;
                    task.ticks_used = 0;
                    self.current = None;
                    return true;
                }
            }
        }
        false
    }

    /// Perform one priority decision: the running task keeps
    /// running unless a `Ready` task has strictly higher priority,
    /// in which case that task preempts it. When no task runs, the
    /// best `Ready` task starts. When nothing can run, the return
    /// is `None` and `current` clears. This is a state change
    /// only: no register is touched here.
    pub fn schedule(&mut self) -> Option<TaskId> {
        let next = self.pick_next();
        match (self.current, next) {
            (Some(index), Some(id))
                if self.slots[index]
                    .as_ref()
                    .map(|task| task.state == TaskState::Running)
                    .unwrap_or(false) =>
            {
                let current_priority = self.slots[index].as_ref().unwrap().priority;
                let next_priority = self.task(id).unwrap().priority;
                if next_priority > current_priority {
                    self.demote_current();
                    self.run_task(id)
                } else {
                    // No strictly better task: the runner stays.
                    self.slots[index].as_ref().map(|task| task.id)
                }
            }
            (_, Some(id)) => {
                // Nothing running (or a stale pointer): start the
                // best ready task.
                self.current = None;
                self.run_task(id)
            }
            (Some(index), None)
                if self.slots[index]
                    .as_ref()
                    .map(|task| task.state == TaskState::Running)
                    .unwrap_or(false) =>
            {
                self.slots[index].as_ref().map(|task| task.id)
            }
            _ => {
                self.current = None;
                None
            }
        }
    }

    /// Voluntary yield: the running task's turn is over, so it
    /// goes back to `Ready` and the best `Ready` task runs.
    /// Equal-priority tasks rotate: the scan starts just after
    /// the yielding task, so a lone equal-priority competitor
    /// runs next instead of the yielder resuming at once. A
    /// lower-priority task never jumps a ready higher-priority
    /// one, so when the yielding task is itself the highest
    /// priority it resumes at once. Returns the task the
    /// trampoline should run next, or `None` when nothing is
    /// ready.
    pub fn yield_now(&mut self) -> Option<TaskId> {
        let yielded = self.current;
        self.demote_current();
        let start = yielded.map(|index| index + 1).unwrap_or(0);
        match self.pick_next_from(start) {
            Some(id) => self.run_task(id),
            None => {
                self.current = None;
                None
            }
        }
    }

    /// Block the running task: it leaves `Running` for `Blocked`
    /// and the scheduler picks the next task. Returns the next
    /// task's id, or `None` when nothing is ready. `false` work is
    /// avoided: when no task is running, nothing is blocked and
    /// the return is the current decision unchanged.
    pub fn block_current(&mut self) -> Option<TaskId> {
        let index = self.current?;
        if let Some(task) = self.slots[index].as_mut() {
            if task.state != TaskState::Running {
                return self.current_id();
            }
            task.state = TaskState::Blocked;
            task.ticks_used = 0;
        }
        self.current = None;
        self.schedule()
    }

    /// Wake a `Blocked` task back to `Ready`. Returns `true` only
    /// when the task exists and was `Blocked`; anything else is
    /// refused, never silently promoted.
    pub fn unblock(&mut self, id: TaskId) -> bool {
        for slot in self.slots.iter_mut() {
            if let Some(task) = slot.as_mut() {
                if task.id == id && task.state == TaskState::Blocked {
                    task.state = TaskState::Ready;
                    return true;
                }
            }
        }
        false
    }

    /// End the running task: it goes to `Exited` and the scheduler
    /// picks the next task. Returns the next task's id, or `None`
    /// when nothing is ready. The exited task keeps its slot until
    /// `reap` frees it.
    pub fn exit_current(&mut self) -> Option<TaskId> {
        let index = self.current?;
        if let Some(task) = self.slots[index].as_mut() {
            if task.state != TaskState::Running {
                return self.current_id();
            }
            task.state = TaskState::Exited;
            task.ticks_used = 0;
        }
        self.current = None;
        self.schedule()
    }

    /// Free the slot of an `Exited` task so `spawn` can reuse it.
    /// Returns `true` only when the task exists and was `Exited`;
    /// a live task's slot is never freed.
    pub fn reap(&mut self, id: TaskId) -> bool {
        for slot in self.slots.iter_mut() {
            if let Some(task) = slot.as_ref() {
                if task.id == id && task.state == TaskState::Exited {
                    *slot = None;
                    return true;
                }
            }
        }
        false
    }

    /// One timer tick: the tick count advances; a `Running` task's
    /// `ticks_used` advances with it, and when it reaches its
    /// quantum the task is preempted to `Ready` and a new decision
    /// is taken. When the running task is inside its quantum, the
    /// return is its id, unchanged. When no task runs, a decision
    /// is taken if any task is ready. The timer device itself is
    /// not touched here: K3's PIT programming is the R5 commit's
    /// wiring, and this function is what that wiring calls.
    pub fn on_timer_tick(&mut self) -> Option<TaskId> {
        self.ticks = self.ticks.checked_add(1).unwrap_or(self.ticks);
        let index = match self.current {
            Some(index) => index,
            None => return self.schedule(),
        };
        let preempt = match self.slots[index].as_mut() {
            Some(task) if task.state == TaskState::Running => {
                task.ticks_used = task.ticks_used.saturating_add(1);
                task.ticks_used >= task.quantum_ticks
            }
            _ => false,
        };
        if preempt {
            // Quantum spent is a rotation decision within the
            // task's priority level, not a priority decision, so
            // this is `yield_now`, not `schedule`: equal-priority
            // tasks rotate, and a lone highest-priority task
            // resumes at once rather than promoting a lower one.
            self.yield_now()
        } else {
            self.slots[index].as_ref().map(|task| task.id)
        }
    }
}
