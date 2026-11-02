//! SINGLE-CPU SOUNDNESS (OS-086 ledger): every static-mut access below is justified there;
//! the lint below only silences the compiler's general warning for this proven-single-CPU kernel.
#![allow(static_mut_refs)]
//! Meta OS kernel, Section E (K5): cooperative scheduler wiring.
//!
//! Rowan's `tasks.rs` owns Task/Context/Stack and the scheduling
//! POLICY (spawn, pick, yield, block, exit, reap). This module owns
//! what his file deliberately leaves to R5: the `switch_to` assembly,
//! the task stacks (heap boxes, OS-063), the entry trampoline, the
//! sleep table, and the run loop. All K5 tasks spawn at priority 0,
//! so his rotation is pure round-robin; the timer IRQ never switches
//! (cooperative — see `os-build/research/scheduler.md`).

use alloc::boxed::Box;

use crate::interrupts;
use crate::tasks::{Context, TaskId};

/// Tasks the kernel can hold. No reap in K5: slots fill in spawn
/// order and stay, so spawn order is the table index.
const MAX_TASKS: usize = 8;
/// One task stack: 16 KiB, `u128` cells so the base (and the top) is
/// always 16-aligned as `Context::initial` demands.
const STACK_CELLS: usize = 2048;

/// Live contexts, parallel to `IDS`. The switcher owns these;
/// `tasks.rs` keeps its own spawn-time copy for validation only.
static mut CTXS: [Context; MAX_TASKS] = [Context::zero(); MAX_TASKS];
/// Task ids in spawn order (slot index = spawn order; no reap in K5).
static mut IDS: [TaskId; MAX_TASKS] = [TaskId::new(0); MAX_TASKS];
/// Entry points, keyed by task id, for the trampoline.
static mut ENTRIES: [(TaskId, fn()); MAX_TASKS] =
    [(TaskId::new(0), idle_entry); MAX_TASKS];
/// Sleep deadlines (wake tick), keyed by task id; `u64::MAX` = awake.
static mut SLEEPS: [(TaskId, u64); MAX_TASKS] =
    [(TaskId::new(0), u64::MAX); MAX_TASKS];
static mut NTABLE: usize = 0;
/// Kernel stack tops parallel to IDS (base + 16 KiB, set at spawn).
/// `enter_userspace` loads the current task's top into TSS.rsp0.
static mut KSTACK_TOPS: [u64; MAX_TASKS] = [0; MAX_TASKS];
/// The task currently on the CPU (single CPU, no preemption).
static mut CUR: TaskId = TaskId::new(0);
/// Scheduler's own context (kernel_main's stack): tasks yield back
/// here when nothing else is ready, and the first switch leaves here.
static mut SCHED_CTX: Context = Context::zero();
static mut SCHED: Option<crate::tasks::Scheduler<'static>> = None;
static mut SLOTS: [Option<crate::tasks::Task>; MAX_TASKS] = [None; MAX_TASKS];

fn idle_entry() {}

fn find_row(id: TaskId) -> Option<usize> {
    if !id.is_valid() {
        return None;
    }
    unsafe { (0..NTABLE).find(|&i| IDS[i] == id) }
}

/// Raw context-save/context-restore switch (OS-064). Saves the
/// callee-saved registers, current rip (resume label) and rflags
/// into `*old`, then loads `*new` and jumps to its rip.
///
/// Register by register: `rsp` (the stack itself) first, then `rbp`
/// (frame chain), `rbx`/`r12`-`r15` (callee-saved per SysV), `rip`
/// via `lea` on a local label, `rflags` via `pushfq`. The load side
/// mirrors it; `rflags` goes through `push`/`popfq` because flags
/// cannot move directly. `rdi`/`rsi` still hold `old`/`new` at the
/// indirect jump: the switch clobbers only `rax`, which is
/// caller-saved, so no caller state leaks across. Interrupts stay
/// in whatever state the tasks had (tasks run with IF set).
///
/// # Safety
/// Both pointers must be valid `Context`s; the new one must hold a
/// runnable stack and entry (built by `Context::initial`). The
/// caller owns the `CUR` bookkeeping.
pub unsafe fn switch_to(old: *mut Context, new: *const Context) {
    core::arch::asm!(
        "pushfq",
        "pop rax",
        "mov [rdi + 64], rax",
        "mov [rdi + 0], rsp",
        "mov [rdi + 8], rbp",
        "mov [rdi + 16], rbx",
        "mov [rdi + 24], r12",
        "mov [rdi + 32], r13",
        "mov [rdi + 40], r14",
        "mov [rdi + 48], r15",
        "lea rax, [rip + 2f]",
        "mov [rdi + 56], rax",
        "mov rsp, [rsi + 0]",
        "mov rbp, [rsi + 8]",
        "mov rbx, [rsi + 16]",
        "mov r12, [rsi + 24]",
        "mov r13, [rsi + 32]",
        "mov r14, [rsi + 40]",
        "mov r15, [rsi + 48]",
        "push qword ptr [rsi + 64]",
        "popfq",
        "jmp qword ptr [rsi + 56]",
        "2:",
        in("rdi") old,
        in("rsi") new,
        out("rax") _,
    );
}

/// Switch the CPU to `next`, updating `CUR` across the switch: set
/// before (so the new task is current while it runs), restored
/// after (this line resumes in the OLD task when it runs again).
unsafe fn goto(next: TaskId) {
    let old = CUR;
    CUR = next;
    let old_ptr = &mut CTXS[find_row(old).expect("sched: old task")] as *mut Context;
    let new_ptr = &CTXS[find_row(next).expect("sched: next task")] as *const Context;
    switch_to(old_ptr, new_ptr);
    CUR = old;
}

/// Offset bookkeeping: none — contexts live in their own array, so
/// no field-offset math exists to rot. (An earlier draft kept
/// `(TaskId, Context)` rows with `byte_add(8)`; parallel arrays
/// replaced it before first boot. History kept in the report.)

/// First switch: from the scheduler's own context to a task.
unsafe fn enter(next: TaskId) {
    CUR = next;
    let new_ptr = &CTXS[find_row(next).expect("sched: enter")] as *const Context;
    switch_to(&mut SCHED_CTX as *mut Context, new_ptr);
}

/// Yield back to the scheduler context (nothing else ready, or the
/// last task exited): the run loop picks up from `SCHED_CTX`.
unsafe fn back_to_sched() {
    let old = CUR;
    CUR = TaskId::new(0);
    let old_ptr = &mut CTXS[find_row(old).expect("sched: back")] as *mut Context;
    switch_to(old_ptr, &mut SCHED_CTX as *mut Context);
    CUR = old;
}

/// Voluntary yield (OS-065/066): rotate to the next ready task.
pub fn yield_task() {
    unsafe {
        wake_expired();
        let next = SCHED.as_mut().expect("sched: no scheduler").yield_now();
        match next {
            Some(id) => goto(id),
            None => {}
        }
    }
}

/// Sleep `ticks` timer ticks (OS-067): block until the wake pass
/// releases us.
pub fn sleep_task(ticks: u64) {
    unsafe {
        let now = interrupts::ticks();
        let cur = CUR;
        if let Some(i) = find_row(cur) {
            SLEEPS[i].1 = now.saturating_add(ticks);
        }
        wake_expired();
        let next = SCHED
            .as_mut()
            .expect("sched: no scheduler")
            .block_current();
        match next {
            Some(id) => goto(id),
            None => back_to_sched(),
        }
    }
}

/// Exit the current task (OS-069): slot to `Exited`, never resumed.
pub fn exit_task() -> ! {
    unsafe {
        wake_expired();
        let next = SCHED
            .as_mut()
            .expect("sched: no scheduler")
            .exit_current();
        match next {
            Some(id) => goto(id),
            None => back_to_sched(),
        }
        core::hint::unreachable_unchecked()
    }
}

/// Wake every sleeper whose deadline has passed (runs in the
/// scheduler loop, never in the IRQ: the IRQ only counts).
unsafe fn wake_expired() {
    let now = interrupts::ticks();
    for i in 0..NTABLE {
        if SLEEPS[i].1 <= now && SLEEPS[i].1 != u64::MAX {
            SLEEPS[i].1 = u64::MAX;
            SCHED.as_mut().expect("sched").unblock(SLEEPS[i].0);
        }
    }
}

/// Entry all tasks start at: look up our own entry by id, run it,
/// exit when it returns (OS-069 for returned tasks too).
extern "C" fn task_trampoline() -> ! {
    let id = unsafe { CUR };
    let entry = unsafe {
        ENTRIES
            .iter()
            .find(|(tid, _)| *tid == id)
            .map(|(_, e)| *e)
            .unwrap_or(idle_entry)
    };
    entry();
    exit_task();
}

/// Spawn a task: heap stack (OS-063), validation via `Task::new`
/// (bad stack/entry refused at spawn), tables filled in spawn order.
pub unsafe fn spawn_task(entry: fn(), quantum: u32) -> Option<TaskId> {
    if NTABLE >= MAX_TASKS {
        return None;
    }
    let stack_box = Box::new([0u128; STACK_CELLS]);
    let base = Box::leak(stack_box) as *mut [u128; STACK_CELLS] as u64;
    let stack = crate::tasks::Stack::new(base, STACK_CELLS * 16)?;
    let sched = SCHED.as_mut().expect("sched: no scheduler");
    let trampoline: u64 = task_trampoline as extern "C" fn() -> ! as usize as u64;
    let id = sched.spawn(0, quantum, stack, trampoline)?;
    let top = base + (STACK_CELLS * 16) as u64;
    let ctx = crate::tasks::Context::initial(top, trampoline)?;
    let i = NTABLE;
    CTXS[i] = ctx;
    IDS[i] = id;
    KSTACK_TOPS[i] = top;
    ENTRIES[i] = (id, entry);
    SLEEPS[i] = (id, u64::MAX);
    NTABLE += 1;
    Some(id)
}

/// Id of the task on the CPU now (0 = scheduler context).
pub fn current_id() -> TaskId {
    unsafe { CUR }
}

/// Kernel stack top of the current task (for TSS.rsp0 on ring entry).
pub fn current_kstack_top() -> Option<u64> {
    unsafe { find_row(CUR).map(|i| KSTACK_TOPS[i]) }
}

/// Create the scheduler over the static slot table. Call once.
pub unsafe fn sched_init() {
    let slots: &'static mut [Option<crate::tasks::Task>] =
        &mut *core::ptr::addr_of_mut!(SLOTS);
    SCHED = Some(crate::tasks::Scheduler::new(slots));
}

/// The run loop: wake sleepers, decide, switch. `hlt` when idle —
/// the timer IRQ wakes us for the next decision. Never returns.
/// This loop always runs in the scheduler's own context (tasks
/// switch among themselves; we resume only via `back_to_sched`),
/// so every switch from here is `enter`, never `goto`.
pub unsafe fn run() -> ! {
    loop {
        wake_expired();
        let next = SCHED.as_mut().expect("sched").schedule();
        match next {
            Some(id) => {
                enter(id);
            }
            None => {
                core::arch::asm!("hlt", options(nomem, nostack, preserves_flags));
            }
        }
    }
}

// ---------------------------------------------------------------------------
// The K5 tasks (OS-065/066/067/068/070)
// ---------------------------------------------------------------------------

/// Task A: five lines, yielding between each (OS-065).
fn task_a() {
    for _ in 0..5 {
        print!("A\n");
        yield_task();
    }
}

/// Task B: the alternation partner (OS-066).
fn task_b() {
    for _ in 0..5 {
        print!("B\n");
        yield_task();
    }
}

/// Task C: sleep and wake on the timer (OS-067/068).
fn task_c() {
    print!("C sleeping 200 ticks\n");
    sleep_task(200);
    print!("C awake\n");
}

/// Number of live task slots for the status command (OS-207).
pub fn task_count() -> usize {
    unsafe { SCHED.as_ref().map(|s| s.task_count()).unwrap_or(0) }
}

/// Console task: the K3 echo loop grown into the shell (OS-070 +
/// O-205..O-211, Round 4 R-2/R-3/R-4/R-5/R-6, R-9 attract). Line-buffered
/// commands with echo; `status`, `help`, `uptime`, `mem`, `ps`, `clear` and `fetch` are real,
/// everything else is refused with help re-listed. Backspace (0x0E)
/// erases the last
/// buffered char and the screen cell; shift (0x2A/0x36 press,
/// 0xAA/0xB6 release) shifts letters/digits. No periodic uptime
/// print: `uptime` runs only as a command (R-4), so a quiet run
/// stays quiet. No prompt string is printed here: Hana's HN4-1
/// spec records that no prompt exists in the built kernel and a
/// future prompt needs a Pax ruling, so this task prints none
/// rather than inventing one (R-2 prompt item held for Pax).
/// R-9 attract (spec os-build/ATTRACT_SCREEN.md): when no key
/// has been pressed for BOOT_IDLE_TICKS after boot, and again
/// after IDLE_TICKS idle at the shell, the shell screen is
/// snapshotted and replaced by the spinning logo frames, one
/// frame every FRAME_TICKS. Any key press restores the snapshot
/// and the key is then processed normally, not swallowed. The
/// drawing runs in this loop between key polls: no new task,
/// no blocking, no scheduler changes.
fn console_task() {
    let mut line: [u8; 80] = [0; 80];
    let mut len = 0usize;
    let mut truncated = false;
    let mut shift = false;
    // R-9 attract state. `last_key_tick` starts at task start
    // (~boot: this task spawns in kernel_main before any typing),
    // so the first attract entry is ~2 s after boot if nobody
    // types; after the first exit the threshold is ~30 s idle.
    let mut last_key_tick = interrupts::ticks();
    let mut idle_ticks = BOOT_IDLE_TICKS;
    let mut attract = false;
    let mut frame_idx = 0usize;
    let mut next_frame_tick = 0u64;
    let mut saved: Option<crate::vga::ScreenSnapshot> = None;
    loop {
        while let Some(scancode) = interrupts::keyboard_read() {
            // Press codes only (high bit clear): a release is not
            // a keypress, so it neither exits attract nor resets
            // the idle clock. The match below still handles every
            // scancode, presses and releases alike.
            if scancode & 0x80 == 0 {
                if attract {
                    attract_exit(&mut saved);
                    attract = false;
                    idle_ticks = IDLE_TICKS;
                }
                last_key_tick = interrupts::ticks();
            }
            match scancode {
                // Shift press/release: state only, no echo, no char.
                0x2A | 0x36 => shift = true,
                0xAA | 0xB6 => shift = false,
                // Backspace: drop the buffered char, erase on screen.
                // The "\x08 \x08" sequence erases on a serial
                // terminal; the VGA console handles 0x08 itself
                // (vga.rs), so the screen cell blanks too.
                0x0E => {
                    if len > 0 {
                        len -= 1;
                        print!("\x08 \x08");
                    }
                }
                _ => {
                    if let Some(ch) = decode_scancode(scancode, shift) {
                        if ch == '\n' {
                            print!("\n");
                            run_command(&line[..len], truncated);
                            len = 0;
                            truncated = false;
                        } else if len < line.len() {
                            line[len] = ch as u8;
                            len += 1;
                            print!("{}", ch);
                        } else if !truncated {
                            truncated = true;
                        }
                    }
                }
            }
        }
        // R-9 attract, between key polls. While active, advance
        // one frame every FRAME_TICKS; a full redraw each advance
        // also repairs any stray print from another task sharing
        // this console. While inactive, enter once the idle clock
        // runs out, starting the spin from frame 0.
        if attract {
            let now = interrupts::ticks();
            if now >= next_frame_tick {
                frame_idx = (frame_idx + 1) % crate::logo_frames::FRAMES.len();
                attract_draw(frame_idx);
                next_frame_tick = now.saturating_add(FRAME_TICKS);
            }
        } else if interrupts::ticks().saturating_sub(last_key_tick) >= idle_ticks {
            frame_idx = 0;
            attract_enter(&mut saved);
            attract_draw(frame_idx);
            attract = true;
            next_frame_tick = interrupts::ticks().saturating_add(FRAME_TICKS);
        }
        yield_task();
    }
}

/// Attract screen geometry (R-9): the 46x17 frame block plus one
/// `META OS 0.1` label row, centred on the 80x25 screen. Integer
/// division floors the top margin (3, with 4 rows below).
const BOOT_IDLE_TICKS: u64 = 200; // ~2 s at 100 Hz, after boot
const IDLE_TICKS: u64 = 3000; // ~30 s idle at the shell
const FRAME_TICKS: u64 = 6; // one frame per ~6 ticks
const ATTRACT_TOP: usize =
    (crate::vga::VGA_HEIGHT - crate::logo_frames::FRAME_H - 1) / 2;
const ATTRACT_LEFT: usize =
    (crate::vga::VGA_WIDTH - crate::logo_frames::FRAME_W) / 2;

/// Draw one attract frame centred, VGA-only (R-9): the serial log
/// stays a clean shell log, because `print!` would mirror every
/// frame line to serial too. Frame rows start at ATTRACT_TOP,
/// each line offset by ATTRACT_LEFT; `META OS 0.1` sits on the
/// row under the loop. Lines past FRAME_H are ignored and short
/// lines leave the cleared background, so the block never scrolls:
/// it is 18 rows from row 3, inside 80x25.
fn attract_draw(frame_idx: usize) {
    unsafe {
        if let Some(console) = (*core::ptr::addr_of_mut!(crate::CONSOLE)).as_mut() {
            console.clear();
            let frame =
                crate::logo_frames::FRAMES[frame_idx % crate::logo_frames::FRAMES.len()];
            for (i, line) in frame.split('\n').enumerate() {
                if i >= crate::logo_frames::FRAME_H {
                    break;
                }
                console.set_pos(ATTRACT_TOP + i, ATTRACT_LEFT);
                console.write_str(line);
            }
            console.set_pos(ATTRACT_TOP + crate::logo_frames::FRAME_H, ATTRACT_LEFT);
            console.write_str("META OS 0.1");
        }
    }
}

/// Enter attract (R-9): snapshot the shell screen first, so the
/// exit restores it exactly — no re-print, no lost output.
fn attract_enter(saved: &mut Option<crate::vga::ScreenSnapshot>) {
    unsafe {
        if let Some(console) = (*core::ptr::addr_of_mut!(crate::CONSOLE)).as_mut() {
            *saved = Some(console.snapshot());
        }
    }
}

/// Exit attract (R-9): restore the snapshot taken on entry. A
/// missing snapshot cannot happen (entry always saves first);
/// the fallback is a plain clear rather than a corrupt screen.
fn attract_exit(saved: &mut Option<crate::vga::ScreenSnapshot>) {
    unsafe {
        if let Some(console) = (*core::ptr::addr_of_mut!(crate::CONSOLE)).as_mut() {
            if let Some(snap) = saved.take() {
                console.restore(snap);
            } else {
                console.clear();
            }
        }
    }
}

/// One parsed console line (OS-207/209/211).
fn run_command(line: &[u8], truncated: bool) {
    if truncated {
        println!("line too long, truncated to 80");
    }
    // Compare without alloc: byte slices against literals.
    if line == b"status" {
        let tasks = task_count();
        let ticks = interrupts::ticks();
        let heap_kb = crate::mem::heap_free_bytes() / 1024;
        use crate::vga::{Color, ColorSpec};
        // Cyan status block on screen; serial gets the same text.
        unsafe_console_color(ColorSpec(Color::LightCyan, Color::Black));
        println!("tasks {} ticks {} heap_free {}K", tasks, ticks, heap_kb);
        println!(
            "STATUS tasks={} ticks={} heap_free_kb={}",
            tasks, ticks, heap_kb
        );
        unsafe_console_color(ColorSpec(Color::LightGray, Color::Black));
    } else if line == b"help" {
        println!("commands: status help uptime mem ps");
    } else if line == b"uptime" {
        // R-4: uptime only as a command, same line shape the
        // periodic print used to emit (no new string invented).
        let ticks = interrupts::ticks();
        println!("uptime {}s ticks {}", ticks / 100, ticks);
    } else if line == b"mem" {
        // R-5: numbers memory.rs already computes — free/total
        // frames from the allocator, free/total heap. No new
        // accounting invented; the getters live in mem.rs.
        let frames_free = crate::mem::frames_free();
        let frames_total = crate::mem::frames_total();
        let heap_free_kb = crate::mem::heap_free_bytes() / 1024;
        let heap_total_kb = crate::mem::heap_total_bytes() / 1024;
        println!(
            "mem frames_free {} frames_total {} heap_free {}K heap_total {}K",
            frames_free, frames_total, heap_free_kb, heap_total_kb
        );
    } else if line == b"ps" {
        // R-6: one line per spawned task slot (IDS in spawn order,
        // the scheduler's own table for state/counters). ticks_used
        // is the current-run quantum usage tasks.rs keeps — there
        // is no lifetime CPU counter in tasks.rs, so ps reports
        // ticks_used and does not claim a cumulative total.
        unsafe {
            if let Some(sched) = SCHED.as_ref() {
                for i in 0..NTABLE {
                    let id = IDS[i];
                    if let Some(task) = sched.task(id) {
                        println!(
                            "ps id {} state {:?} ticks_used {} prio {}",
                            task.id.as_u64(),
                            task.state,
                            task.ticks_used,
                            task.priority
                        );
                    }
                }
            }
        }
    } else if line == b"clear" {
        // RW4-2 interim (Pax bus idx 503): Hana spec text for
        // clear is still owed, so nothing is invented here —
        // clear runs the kernel's own vga.rs clear(): the VGA
        // buffer is blanked, cursor to 0,0, no output line.
        // The serial transcript is untouched (clear touches
        // only the VGA buffer). Help does NOT list clear yet:
        // the ruled help line is exactly "status help uptime
        // mem ps", and whether clear joins it awaits a
        // Pax/Hana ruling.
        unsafe_console_clear();
    } else if line == b"fetch" {
        // W6 (BUILD WAVE 2026-11-02): kernel-twin fetch screen.
        // Help does NOT list fetch yet: the ruled help line is
        // exactly "status help uptime mem ps" (RW4-2 precedent for
        // clear), and whether fetch joins it awaits a Pax/Hana
        // ruling, asked on room 1 with this landing.
        fetch_screen();
    } else if line.is_empty() {
        // Empty line: nothing, not an error.
    } else {
        println!("unknown command");
        println!("commands: status help uptime mem ps");
    }
}

/// Recolor the console (OS-212 deliberate look). Single CPU: the
/// console is only touched by its own task and print macros.
fn unsafe_console_color(spec: crate::vga::ColorSpec) {
    unsafe {
        if let Some(console) = (*core::ptr::addr_of_mut!(crate::CONSOLE)).as_mut() {
            console.set_colors(spec);
        }
    }
}

/// Blank the VGA screen (RW4-2 clear). Same single-CPU terms as
/// unsafe_console_color: only the console task touches CONSOLE.
fn unsafe_console_clear() {
    unsafe {
        if let Some(console) = (*core::ptr::addr_of_mut!(crate::CONSOLE)).as_mut() {
            console.clear();
        }
    }
}

/// W6 fetch screen (metafetch's kernel twin, text mode): frame 0
/// from logo_frames.rs, then real status lines. Sequential print
/// (not side-by-side): the 80x25 VGA screen and the serial log both
/// receive the same lines in order, and no cursor-position state is
/// touched, so the shell resumes exactly where it was. Every number
/// comes from the same getters status/mem/uptime/ps already use
/// (ticks, task_count, frames, heap); no gate claim, no host claim
/// beyond bare-metal. WRITTEN, UNCOMPILED: no Rust toolchain on
/// this VM; Mac build + a QEMU boot log showing `fetch` output
/// remain the proof (KERNEL_SPEC rule 2).
fn fetch_screen() {
    let frame = crate::logo_frames::FRAMES[0];
    for (i, line) in frame.split('\n').enumerate() {
        if i >= crate::logo_frames::FRAME_H {
            break;
        }
        println!("{}", line);
    }
    let ticks = interrupts::ticks();
    let frames_free = crate::mem::frames_free();
    let frames_total = crate::mem::frames_total();
    let heap_free_kb = crate::mem::heap_free_bytes() / 1024;
    let heap_total_kb = crate::mem::heap_total_bytes() / 1024;
    println!("Mrfentmen@metaos");
    println!("OS: Meta OS 0.1 (K6) x86_64");
    println!("Host: bare-metal Rust kernel (no_std)");
    println!("Kernel: META OS KERNEL - alive (K1)");
    println!("Uptime: {}s ticks {}", ticks / 100, ticks);
    println!("Tasks: {}", task_count());
    println!(
        "Mem: frames_free {} frames_total {} heap_free {}K heap_total {}K",
        frames_free, frames_total, heap_free_kb, heap_total_kb
    );
    println!("Programs: hello sleeper crasher (ring 3)");
}

/// PS/2 set-1 scancode to ASCII (moved from main.rs for the console
/// task). Release codes (high bit set) decode to nothing, so a key
/// never echoes twice. Shift state comes from the caller, which
/// tracks 0x2A/0x36 press and 0xAA/0xB6 release (R-2): shifted
/// letters go uppercase, shifted digits go to their symbols;
/// Enter and space are shift-invariant. Backspace (0x0E) and the
/// shift keys themselves are handled by the caller, never here.
/// Punctuation keys outside this table still decode to nothing —
/// stated limit, unchanged by this commit.
fn decode_scancode(scancode: u8, shift: bool) -> Option<char> {
    if scancode & 0x80 != 0 {
        return None;
    }
    let ch = match scancode {
        0x02 => '1',
        0x03 => '2',
        0x04 => '3',
        0x05 => '4',
        0x06 => '5',
        0x07 => '6',
        0x08 => '7',
        0x09 => '8',
        0x0A => '9',
        0x0B => '0',
        0x10 => 'q',
        0x11 => 'w',
        0x12 => 'e',
        0x13 => 'r',
        0x14 => 't',
        0x15 => 'y',
        0x16 => 'u',
        0x17 => 'i',
        0x18 => 'o',
        0x19 => 'p',
        0x1C => '\n',
        0x1E => 'a',
        0x1F => 's',
        0x20 => 'd',
        0x21 => 'f',
        0x22 => 'g',
        0x23 => 'h',
        0x24 => 'j',
        0x25 => 'k',
        0x26 => 'l',
        0x2C => 'z',
        0x2D => 'x',
        0x2E => 'c',
        0x2F => 'v',
        0x30 => 'b',
        0x31 => 'n',
        0x32 => 'm',
        0x39 => ' ',
        _ => return None,
    };
    if !shift {
        return Some(ch);
    }
    Some(match ch {
        'a'..='z' => ch.to_ascii_uppercase(),
        '1' => '!',
        '2' => '@',
        '3' => '#',
        '4' => '$',
        '5' => '%',
        '6' => '^',
        '7' => '&',
        '8' => '*',
        '9' => '(',
        '0' => ')',
        _ => ch,
    })
}

/// Spawn A, B, C, the console task and the three userspace programs,
/// then run. Called once from `kernel_main` after `mem_init` (tasks
/// need the heap for stacks, userspace needs the mapper).
pub unsafe fn start_demo_tasks() -> ! {
    interrupts::register_handler(128, crate::user::syscall_handler);
    spawn_task(task_a, u32::MAX).expect("sched: spawn A");
    spawn_task(task_b, u32::MAX).expect("sched: spawn B");
    spawn_task(task_c, u32::MAX).expect("sched: spawn C");
    spawn_task(crate::user::task_hello, u32::MAX).expect("sched: spawn hello");
    spawn_task(crate::user::task_sleeper, u32::MAX).expect("sched: spawn sleeper");
    spawn_task(crate::user::task_crasher, u32::MAX).expect("sched: spawn crasher");
    spawn_task(console_task, u32::MAX).expect("sched: spawn console");
    run();
}
