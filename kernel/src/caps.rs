//! Meta OS kernel, K6.1: in-kernel agent capability policy.
//!
//! This is the first slice of agent policy that actually lives in the
//! kernel. It governs only what the kernel mediates: the syscall a task
//! may call, how many bytes it may write to the console, how long it may
//! sleep, and how many timer ticks it may consume before the kernel kills
//! it. A policy is assigned when the ELF is entered and checked at the
//! syscall boundary; a refusal is logged and returns `DENIED`, and an
//! exhausted wall budget kills the task.
//!
//! This is NOT a sandbox for file, network, or exec. The kernel has no
//! such syscalls (the frozen table is 0-5 plus 6 = cap_query), so those
//! grants remain in the L5 userspace gateway. The honest boundary is in
//! `os-build/KERNEL_SPEC.md` and `docs/AGENT_LAYER_SPEC.md`.
//!
//! The scheduler is cooperative: a task that never makes a syscall is
//! never checked. Policy enforcement is therefore at the syscall
//! boundary, not preemptive. Stated, not implied.
#![allow(static_mut_refs)]

use crate::tasks::TaskId;

pub const SYS_EXIT: u64 = 0;
pub const SYS_WRITE: u64 = 1;
pub const SYS_SLEEP: u64 = 2;
pub const SYS_PID: u64 = 3;
pub const SYS_YIELD: u64 = 4;
pub const SYS_READ_KEY: u64 = 5;
pub const SYS_CAP_QUERY: u64 = 6;

/// A capability refusal is distinct from `u64::MAX`, which remains the
/// normal "no value" (empty key ring) or bad-syscall refusal. Userspace
/// can therefore tell "the kernel denied this" from "there was nothing".
pub const DENIED: u64 = u64::MAX - 1;

/// One task's permit. All limits are absolute; there is no widening.
#[derive(Clone, Copy)]
pub struct Policy {
    pub name: &'static str,
    /// Bit N set means syscall N is allowed.
    pub allowed: u64,
    /// Total console bytes this task may write.
    pub max_write: u64,
    /// Wall-clock budget in timer ticks (~100 Hz) from ELF entry.
    pub max_ticks: u64,
    /// Longest single sleep this task may request, in ticks.
    pub max_sleep: u64,
}

const fn bit(n: u64) -> u64 {
    1u64 << n
}

pub const HELLO: Policy = Policy {
    name: "hello",
    allowed: bit(SYS_EXIT) | bit(SYS_WRITE) | bit(SYS_PID) | bit(SYS_YIELD) | bit(SYS_CAP_QUERY),
    max_write: 256,
    max_ticks: 2_000,
    max_sleep: 0,
};

pub const SLEEPER: Policy = Policy {
    name: "sleeper",
    allowed: bit(SYS_EXIT)
        | bit(SYS_WRITE)
        | bit(SYS_SLEEP)
        | bit(SYS_PID)
        | bit(SYS_YIELD)
        | bit(SYS_CAP_QUERY),
    max_write: 256,
    max_ticks: 2_000,
    max_sleep: 100,
};

pub const CRASHER: Policy = Policy {
    name: "crasher",
    allowed: bit(SYS_EXIT) | bit(SYS_WRITE) | bit(SYS_PID) | bit(SYS_YIELD) | bit(SYS_CAP_QUERY),
    max_write: 256,
    max_ticks: 2_000,
    max_sleep: 0,
};

pub const READKEY: Policy = Policy {
    name: "readkey",
    allowed: bit(SYS_EXIT)
        | bit(SYS_WRITE)
        | bit(SYS_SLEEP)
        | bit(SYS_PID)
        | bit(SYS_YIELD)
        | bit(SYS_READ_KEY)
        | bit(SYS_CAP_QUERY),
    max_write: 1_000_000,
    max_ticks: 100_000,
    max_sleep: 100,
};

/// The policy drill. It is allowed to sleep and write, but not to read
/// the keyboard, and its write/sleep caps are deliberately small enough
/// that its own over-limit calls are refused. The kernel proves the
/// enforcement; the program only reports what the kernel returned.
pub const CAPCHECK: Policy = Policy {
    name: "capcheck",
    allowed: bit(SYS_EXIT)
        | bit(SYS_WRITE)
        | bit(SYS_SLEEP)
        | bit(SYS_PID)
        | bit(SYS_YIELD)
        | bit(SYS_CAP_QUERY),
    max_write: 128,
    max_ticks: 2_000,
    max_sleep: 100,
};

pub fn policy_for(name: &str) -> Option<Policy> {
    Some(match name {
        "hello" => HELLO,
        "sleeper" => SLEEPER,
        "crasher" => CRASHER,
        "readkey" => READKEY,
        "capcheck" => CAPCHECK,
        _ => return None,
    })
}

#[derive(Clone, Copy)]
struct Row {
    id: TaskId,
    policy: Policy,
    written: u64,
    start_tick: u64,
}

const EMPTY: Row = Row {
    id: TaskId::new(0),
    policy: CAPCHECK, // never read for id 0
    written: 0,
    start_tick: 0,
};

const MAX_ROWS: usize = 8;

static mut ROWS: [Row; MAX_ROWS] = [EMPTY; MAX_ROWS];

fn table() -> *mut Row {
    core::ptr::addr_of_mut!(ROWS) as *mut Row
}

fn index_of(id: TaskId) -> Option<usize> {
    if !id.is_valid() {
        return None;
    }
    unsafe {
        for i in 0..MAX_ROWS {
            if (*table().add(i)).id == id {
                return Some(i);
            }
        }
    }
    None
}

fn row(i: usize) -> &'static mut Row {
    unsafe { &mut *table().add(i) }
}

fn announce(policy: Policy) {
    println!(
        "cap grant {} write={} ticks={} sleep={}",
        policy.name, policy.max_write, policy.max_ticks, policy.max_sleep
    );
}

/// Assign a policy to the task calling this. Called from `run_elf` at
/// ELF entry, so the policy is in force before the first ring-3
/// instruction. Re-assignment resets usage and the wall clock.
pub fn assign_current(policy: Policy) {
    let id = crate::sched::current_id();
    if !id.is_valid() {
        return;
    }
    let start_tick = crate::interrupts::ticks();
    unsafe {
        let mut free = None;
        for i in 0..MAX_ROWS {
            let slot = &mut *table().add(i);
            if slot.id == id {
                *slot = Row {
                    id,
                    policy,
                    written: 0,
                    start_tick,
                };
                announce(policy);
                return;
            }
            if !slot.id.is_valid() && free.is_none() {
                free = Some(i);
            }
        }
        if let Some(i) = free {
            *row(i) = Row {
                id,
                policy,
                written: 0,
                start_tick,
            };
            announce(policy);
        } else {
            println!("cap table full; {} runs unpoliced", policy.name);
        }
    }
}

/// What the syscall entry must do next.
pub enum Gate {
    Allow,
    Refuse,
    Kill,
}

/// Check the calling task's permit for syscall `num`. Also enforces the
/// wall budget: an expired task is killed, not merely refused.
pub fn gate(num: u64) -> Gate {
    let i = match index_of(crate::sched::current_id()) {
        Some(i) => i,
        None => return Gate::Allow,
    };
    let row = row(i);
    let now = crate::interrupts::ticks();
    if now.saturating_sub(row.start_tick) >= row.policy.max_ticks {
        println!(
            "cap kill {} budget {} ticks",
            row.policy.name, row.policy.max_ticks
        );
        return Gate::Kill;
    }
    if num < 64 && (row.policy.allowed & bit(num)) != 0 {
        Gate::Allow
    } else {
        println!("cap deny {} syscall {}", row.policy.name, num);
        Gate::Refuse
    }
}

/// May this task write `len` more console bytes? Checked before the
/// buffer is dereferenced or printed.
pub fn allow_write(len: u64) -> bool {
    let i = match index_of(crate::sched::current_id()) {
        Some(i) => i,
        None => return true,
    };
    let row = row(i);
    let remaining = row.policy.max_write.saturating_sub(row.written);
    if len > remaining {
        println!(
            "cap deny {} write {} over {}",
            row.policy.name, len, remaining
        );
        false
    } else {
        true
    }
}

/// Charge a write only after the kernel actually printed it.
pub fn charge_write(len: u64) {
    if let Some(i) = index_of(crate::sched::current_id()) {
        let row = row(i);
        row.written = row.written.saturating_add(len);
    }
}

/// May this task sleep `ticks` timer ticks? A request longer than its
/// per-sleep cap, or one that would run past its wall budget, is refused
/// before the task is blocked.
pub fn allow_sleep(ticks: u64) -> bool {
    let i = match index_of(crate::sched::current_id()) {
        Some(i) => i,
        None => return true,
    };
    let row = row(i);
    if ticks > row.policy.max_sleep {
        println!(
            "cap deny {} sleep {} over {}",
            row.policy.name, ticks, row.policy.max_sleep
        );
        return false;
    }
    let now = crate::interrupts::ticks();
    let remaining = row
        .policy
        .max_ticks
        .saturating_sub(now.saturating_sub(row.start_tick));
    if ticks > remaining {
        println!(
            "cap deny {} sleep {} past budget {}",
            row.policy.name, ticks, remaining
        );
        return false;
    }
    true
}

/// Remaining budget, packed as `(ticks << 32) | write_bytes`. Returns
/// `u64::MAX` for a task with no policy.
pub fn query() -> u64 {
    let i = match index_of(crate::sched::current_id()) {
        Some(i) => i,
        None => return u64::MAX,
    };
    let row = row(i);
    let now = crate::interrupts::ticks();
    let remaining_ticks = row
        .policy
        .max_ticks
        .saturating_sub(now.saturating_sub(row.start_tick));
    let remaining_write = row.policy.max_write.saturating_sub(row.written);
    (remaining_ticks.min(u32::MAX as u64) << 32) | remaining_write.min(u32::MAX as u64)
}
