//! talker: K4 IPC gate pair, sender half (design §6).
//! Sends one message to the listener's fixed spawn-order id and
//! exits. Peer ids are the gate build's loader-table contract
//! (see `kernel/K4_PAIR_SWAP.md`): this program is spawned fourth,
//! so its own id is 4 and the listener's is 6. `getpid` (syscall 3)
//! returns only the caller's own id, so the own-id check below is
//! the only identity this program can verify itself; the peer id
//! is a named constant, never probed.
//! Boot NOT CLAIMED: gate-1 (Milo) + Mac/QEMU boot log owed.

#![no_std]
#![no_main]

use user::{sys_exit, sys_getpid, sys_ipc_send, sys_write, sys_yield};

/// Fixed spawn-order ids for this gate boot (loader-table contract).
const OWN_ID: u64 = 4;
const LISTENER_ID: u64 = 6;
const MSG: &[u8] = b"IPC-OK";

#[no_mangle]
pub extern "C" fn _start() -> ! {
    if sys_getpid() != OWN_ID {
        sys_write(b"talker: wrong id\n");
        sys_exit(1);
    }
    let mut tries = 0u32;
    loop {
        let r = sys_ipc_send(LISTENER_ID, MSG);
        if r == 0 {
            sys_write(b"talker: sent\n");
            sys_exit(0);
        }
        // Full box or other refusal: yield and retry, bounded, so a
        // stuck listener fails loudly instead of spinning forever.
        tries += 1;
        if tries >= 1000 {
            sys_write(b"talker: refused\n");
            sys_exit(1);
        }
        sys_yield();
    }
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}
