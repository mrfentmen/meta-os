//! listener: K4 IPC gate pair, receiver half (design §6).
//! Polls `ipc_recv` until one message arrives, prints its payload,
//! and exits. Peer ids are the gate build's loader-table contract
//! (see `kernel/K4_PAIR_SWAP.md`): this program is spawned sixth,
//! so its own id is 6 and the talker's is 4. The sender id is read
//! from the message's kernel-filled 8-byte header, never trusted
//! from the caller, and checked against the talker's id.
//! Boot NOT CLAIMED: gate-1 (Milo) + Mac/QEMU boot log owed.

#![no_std]
#![no_main]

use user::{sys_exit, sys_getpid, sys_ipc_recv, sys_write, sys_yield};

/// Fixed spawn-order ids for this gate boot (loader-table contract).
const OWN_ID: u64 = 6;
const TALKER_ID: u64 = 4;

#[no_mangle]
pub extern "C" fn _start() -> ! {
    if sys_getpid() != OWN_ID {
        sys_write(b"listener: wrong id\n");
        sys_exit(1);
    }
    let mut buf = [0u8; 72];
    let mut polls = 0u32;
    loop {
        let r = sys_ipc_recv(&mut buf);
        if r != u64::MAX {
            let total = r as usize;
            if total < 9 || total > 72 {
                sys_write(b"listener: bad length\n");
                sys_exit(1);
            }
            let mut sender = 0u64;
            for i in 0..8 {
                sender |= (buf[i] as u64) << (i * 8);
            }
            if sender != TALKER_ID {
                sys_write(b"listener: wrong sender\n");
                sys_exit(1);
            }
            sys_write(b"listener: got ");
            sys_write(&buf[8..total]);
            sys_write(b"\n");
            sys_exit(0);
        }
        // Empty box: yield between polls (design §6 polling pattern).
        // Never spin without yielding — a spinning receiver starves
        // the sender on this cooperative scheduler.
        polls += 1;
        if polls >= 200_000 {
            sys_write(b"listener: timeout\n");
            sys_exit(1);
        }
        sys_yield();
    }
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
