//! K4 IPC: bounded per-task mailboxes (buildout spec, "Tasks can talk").
//!
//! No channel exists between tasks today (see
//! `os-build/layer1/r12/IPC_GAP.md`): two tasks can both write to the
//! console, which has no destination, no ordering and no backpressure.
//! This module is the kernel side of the fix, in the shape the gap
//! record asks for:
//!
//! * a channel per task id (the mailbox), not console text;
//! * bounded messages: a mailbox holds `MAILBOX_CAP` `u64` values, and
//!   a send to a full box refuses (`IpcError::Full`) rather than
//!   blocking forever;
//! * stated receive semantics: `mailbox_recv` returns `Recv::Msg`,
//!   `Recv::Empty` (nothing yet, caller yields and retries), or
//!   `Recv::Closed` (nothing will ever arrive);
//! * sender identity is the task id itself: a mailbox belongs to one
//!   owner id, and a send names its destination id;
//! * teardown: `mailbox_close` drops the queued mail and marks the
//!   box closed, so a peer sending afterwards gets `Closed` instead
//!   of queueing into a dead task, and a peer receiving after the
//!   drain gets `Closed` instead of spinning. The scheduler calls
//!   `mailbox_close` for the exiting task in `sched::exit_task`.
//!
//! What this module deliberately does NOT do: allocate a syscall
//! number. Numbers 6-15 stay reserved under the F1 ruling; no
//! userspace program can reach these functions until Pax rules a
//! number and a spec update lands in the same commit. The
//! talker/listener pair below runs as kernel tasks (the
//! `start_demo_tasks` shape), so the channel semantics get proven
//! without touching the frozen table or `syscalls.rs` (untouched,
//! as ruled).
//!
//! Single-CPU soundness follows the scheduler's ledger (OS-086):
//! every `static mut` below is touched only by the running task on
//! the one CPU, never from an IRQ handler.

#![allow(static_mut_refs)]

use crate::tasks::TaskId;

/// Messages a mailbox holds before a send refuses with `Full`.
pub const MAILBOX_CAP: usize = 8;

/// Mailboxes: one slot per scheduler slot (`MAX_TASKS` in `sched.rs`).
/// A slot whose box is closed and drained is reclaimable by a later
/// task id (see `mailbox_open`); ids are never reused, so a sender
/// holding a dead task's id gets `NoMailbox` after a reclaim, never
/// mail delivered to the wrong task.
const MAX_MAILBOXES: usize = 8;

/// Why a send refused. `Full` is backpressure, not an error in the
/// caller: the pair yields and retries (see `task_talker`).
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum IpcError {
    /// No open mailbox belongs to the destination id.
    NoMailbox,
    /// The destination box holds `MAILBOX_CAP` messages already.
    Full,
    /// The destination box is closed (owner done or exited).
    Closed,
}

/// What a receive found. `Closed` fires only once the queue is
/// drained, so no message is lost to the close.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Recv {
    /// A message value.
    Msg(u64),
    /// Queue empty, box open: nothing yet.
    Empty,
    /// Queue drained and box closed: nothing will ever arrive.
    Closed,
}

/// One mailbox: a fixed ring, no allocation, no growth.
#[derive(Clone, Copy)]
struct Mailbox {
    /// Owning task id; `TaskId::new(0)` when the slot never opened.
    owner: TaskId,
    /// Ring storage; only the first `len` entries from `head` count.
    buf: [u64; MAILBOX_CAP],
    /// Index of the next message to read.
    head: usize,
    /// Messages queued.
    len: usize,
    /// Set by `mailbox_close`; the queue still drains first.
    closed: bool,
    /// True once claimed; a closed, drained box stays claimable for
    /// reclaim by `mailbox_open` (see the module docs).
    open: bool,
}

impl Mailbox {
    const fn empty() -> Mailbox {
        Mailbox {
            owner: TaskId::new(0),
            buf: [0; MAILBOX_CAP],
            head: 0,
            len: 0,
            closed: false,
            open: false,
        }
    }

    /// Queue `msg`; false when full. The caller checks `closed`
    /// first, so a closed box never accepts mail here.
    fn push(&mut self, msg: u64) -> bool {
        if self.len >= MAILBOX_CAP {
            return false;
        }
        let tail = (self.head + self.len) % MAILBOX_CAP;
        self.buf[tail] = msg;
        self.len += 1;
        true
    }

    /// Take the oldest message, or `None` when empty.
    fn pop(&mut self) -> Option<u64> {
        if self.len == 0 {
            return None;
        }
        let msg = self.buf[self.head];
        self.head = (self.head + 1) % MAILBOX_CAP;
        self.len -= 1;
        Some(msg)
    }

    /// Reset to a fresh, open box for `owner`.
    fn reset(&mut self, owner: TaskId) {
        self.owner = owner;
        self.buf = [0; MAILBOX_CAP];
        self.head = 0;
        self.len = 0;
        self.closed = false;
        self.open = true;
    }
}

static mut BOXES: [Mailbox; MAX_MAILBOXES] = [Mailbox::empty(); MAX_MAILBOXES];

/// Open `owner`'s mailbox. Idempotent and non-destructive:
/// opening an already-open box leaves its queue and its closed
/// flag untouched — this matters because the listener opens its
/// box when it first runs, which may be after the talker has
/// already queued mail and closed the channel; a reset here
/// would drop that mail and resurrect the channel. A genuinely
/// fresh box comes from a never-opened or reclaimed slot.
/// Returns false only when every slot is live (open, unclosed)
/// — with `MAX_TASKS` live tasks that cannot happen for a task
/// the scheduler is running.
pub fn mailbox_open(owner: TaskId) -> bool {
    if !owner.is_valid() {
        return false;
    }
    unsafe {
        // Existing box for this owner: keep it exactly as it is.
        if BOXES.iter().any(|slot| slot.open && slot.owner == owner) {
            return true;
        }
        // Never-opened slot first, then a closed, drained slot.
        if let Some(slot) = BOXES.iter_mut().find(|slot| !slot.open) {
            slot.reset(owner);
            return true;
        }
        if let Some(slot) = BOXES
            .iter_mut()
            .find(|slot| slot.open && slot.closed && slot.len == 0)
        {
            slot.reset(owner);
            return true;
        }
    }
    false
}

/// Close `owner`'s mailbox: queued mail is dropped, later sends get
/// `Closed`, and a receiver draining the box is not affected (the
/// queue is already empty by definition here — a close after sends
/// must go through `mailbox_close_to`, which keeps the queue).
/// The scheduler calls this for the exiting task, so no sender
/// queues into a dead task afterwards.
pub fn mailbox_close(owner: TaskId) {
    if !owner.is_valid() {
        return;
    }
    unsafe {
        if let Some(slot) = BOXES.iter_mut().find(|slot| slot.open && slot.owner == owner) {
            slot.closed = true;
            slot.len = 0;
            slot.head = 0;
        }
    }
}

/// Close the channel TO `owner` without dropping queued mail: the
/// receiver still drains what is queued, then sees `Closed`. This
/// is the talker's done signal (see `task_talker`).
pub fn mailbox_close_to(owner: TaskId) {
    if !owner.is_valid() {
        return;
    }
    unsafe {
        if let Some(slot) = BOXES.iter_mut().find(|slot| slot.open && slot.owner == owner) {
            slot.closed = true;
        }
    }
}

/// Send `msg` to `owner`'s mailbox. Never blocks: a full box
/// refuses with `Full` and the caller decides (yield and retry, or
/// give up) — the refusal is the backpressure the gap record asks
/// for, not a scheduler block.
pub fn mailbox_send(owner: TaskId, msg: u64) -> Result<(), IpcError> {
    if !owner.is_valid() {
        return Err(IpcError::NoMailbox);
    }
    unsafe {
        match BOXES.iter_mut().find(|slot| slot.open && slot.owner == owner) {
            None => Err(IpcError::NoMailbox),
            Some(slot) if slot.closed => Err(IpcError::Closed),
            Some(slot) => {
                if slot.push(msg) {
                    Ok(())
                } else {
                    Err(IpcError::Full)
                }
            }
        }
    }
}

/// Receive from `owner`'s mailbox: the oldest message, `Empty`
/// while the box is open and dry, or `Closed` once the queue is
/// drained and the box is closed — including when the box was
/// never opened, since no message can ever arrive there.
pub fn mailbox_recv(owner: TaskId) -> Recv {
    if !owner.is_valid() {
        return Recv::Closed;
    }
    unsafe {
        match BOXES.iter_mut().find(|slot| slot.open && slot.owner == owner) {
            None => Recv::Closed,
            Some(slot) => match slot.pop() {
                Some(msg) => Recv::Msg(msg),
                None => {
                    if slot.closed {
                        Recv::Closed
                    } else {
                        Recv::Empty
                    }
                }
            },
        }
    }
}

// ---------------------------------------------------------------------------
// The acceptance pair (kernel tasks, IPC_GAP.md transcript)
// ---------------------------------------------------------------------------

/// Listener id for `task_talker`, set by the spawner after spawning
/// the listener and before spawning the talker. Zero means unset:
/// the talker refuses to run rather than sending into the void.
static mut LISTENER_ID: TaskId = TaskId::new(0);

/// Record the listener's id for the talker. Called by the spawner
/// only; the talker reads it once at start.
pub fn ipc_set_listener(id: TaskId) {
    unsafe {
        LISTENER_ID = id;
    }
}

/// Talker: sends 1, then 2, to the listener, then closes the
/// channel and ends. Prints the acceptance lines as it goes:
/// `talker: sent 1`, `talker: sent 2`, `talker: done`. A full box
/// yields and retries (backpressure handled by the sender, not
/// hidden in the kernel); any other refusal ends the task with a
/// refusal line rather than a silent hang.
pub fn task_talker() {
    let listener = unsafe { LISTENER_ID };
    if !listener.is_valid() {
        print!("talker: no listener\n");
        return;
    }
    mailbox_open(listener);
    for msg in [1u64, 2] {
        loop {
            match mailbox_send(listener, msg) {
                Ok(()) => break,
                Err(IpcError::Full) => crate::sched::yield_task(),
                Err(_) => {
                    print!("talker: refused\n");
                    return;
                }
            }
        }
        print!("talker: sent {}\n", msg);
    }
    mailbox_close_to(listener);
    print!("talker: done\n");
}

/// Listener: drains its own mailbox until the close arrives, then
/// ends. Prints `listener: got <n>` per message and
/// `listener: closed` at the end — the transcript the gap record
/// defines, with the talker's lines interleaved by the scheduler.
pub fn task_listener() {
    let me = crate::sched::current_id();
    mailbox_open(me);
    loop {
        match mailbox_recv(me) {
            Recv::Msg(msg) => print!("listener: got {}\n", msg),
            Recv::Empty => crate::sched::yield_task(),
            Recv::Closed => {
                print!("listener: closed\n");
                return;
            }
        }
    }
}
