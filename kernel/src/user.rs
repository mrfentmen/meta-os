//! SINGLE-CPU SOUNDNESS (OS-086 ledger): every static-mut access below is justified there;
//! the lint below only silences the compiler's general warning for this proven-single-CPU kernel.
#![allow(static_mut_refs)]
//! Meta OS kernel, Section F (K6): first userspace (OS-076..OS-088).
//!
//! Four static ELFs (built by `kernel/build.rs` into OUT_DIR) are
//! parsed and mapped at their linked addresses, then entered with
//! `iretq` at ring 3. Syscalls arrive on `int 0x80` (vector 128);
//! the handler reads the saved registers, serves write/exit/sleep/
//! getpid/yield/read_key, and refuses anything else. A userspace page fault
//! kills only that task (see the `page_fault_handler` note in
//! `interrupts.rs`). `core` only.

use crate::gdt::{set_rsp0, USER_CODE_SELECTOR, USER_DATA_SELECTOR};
use crate::interrupts::InterruptFrame;
use crate::memory::{
    MapError, Mapper, VirtAddr, ENTRY_NO_EXECUTE, ENTRY_WRITABLE,
};

pub static HELLO_ELF: &[u8] =
    include_bytes!(concat!(env!("OUT_DIR"), "/hello.elf"));
pub static SLEEPER_ELF: &[u8] =
    include_bytes!(concat!(env!("OUT_DIR"), "/sleeper.elf"));
pub static CRASHER_ELF: &[u8] =
    include_bytes!(concat!(env!("OUT_DIR"), "/crasher.elf"));
pub static READKEY_ELF: &[u8] =
    include_bytes!(concat!(env!("OUT_DIR"), "/readkey.elf"));

/// One user stack per userspace task (K6 scope: four programs).
/// Stacks are FRESH USER pages, not kernel .bss: the bootloader's
/// kernel mappings are supervisor-only, and ring 3 faults on them
/// (found live: first `push` faulted err=0x7 on the .bss stack).
/// 8 KiB each at 64 KiB spacing from USTACK_BASE.
const USTACK_BASE: u64 = 0x0000_5000_0000_0000;
const USTACK_SIZE: u64 = 8192;
static mut NEXT_USTACK: u64 = 0;

/// Map one user stack and return its top. Must run before `iretq`.
fn map_ustack(slot: u64) -> Option<u64> {
    let base = USTACK_BASE + slot.checked_mul(0x10000)?;
    crate::mem::with_mapper(|mapper, _| {
        for p in 0..(USTACK_SIZE / 4096) {
            let v = base + p * 4096;
            if mapper.translate(VirtAddr(v)).is_none() {
                let frame = mapper.allocate_frame()?;
                mapper
                    .map_page(
                        VirtAddr(v),
                        frame,
                        ENTRY_WRITABLE | ENTRY_NO_EXECUTE | crate::memory::ENTRY_USER,
                        true,
                    )
                    .ok()?;
                crate::mem::invlpg(v);
            }
        }
        Some(base + USTACK_SIZE)
    })?
}

/// Saved-register offsets below the `InterruptFrame` pointer, per
/// `trap_common`'s push order: 9 scratch regs (72 bytes), then vector
/// (8), then error (8), then the CPU frame. So from `&rip`: vector is
/// at -16, error at -8, r11 at -24 ... rax at -88?? No: r11 sits at
/// rsp+0 and rip at rsp+88, so rax (rsp+64) is at frame-24, rcx
/// (rsp+56) at frame-32, rdx (rsp+48) at frame-40, rsi (rsp+40) at
/// frame-48, rdi (rsp+32) at frame-56.
const SAVED_RAX: isize = -24;
const SAVED_RCX: isize = -32;
const SAVED_RDX: isize = -40;
const SAVED_RSI: isize = -48;
const SAVED_RDI: isize = -56;

unsafe fn saved(frame: *const InterruptFrame, off: isize) -> u64 {
    (frame as *const u64).byte_offset(off).read()
}

unsafe fn set_return(frame: *const InterruptFrame, value: u64) {
    (frame as *mut u64).byte_offset(SAVED_RAX).write(value);
}

/// Syscall entry for vector 128, registered in the dispatch table.
/// Runs on the calling task's own kernel stack (TSS.rsp0 was set to
/// it on ring entry), so scheduler calls switch exactly like
/// task-called ones and `iretq` returns to the program.
pub fn syscall_handler(frame: &InterruptFrame, _error: u64) {
    let base = frame as *const InterruptFrame;
    unsafe {
        let num = saved(base, SAVED_RAX);
        let a1 = saved(base, SAVED_RDI);
        let a2 = saved(base, SAVED_RSI);
        match num {
            0 => {
                println!("user exit code {}", a1);
                crate::sched::exit_task();
            }
            1 => {
                let n = user_write(a1, a2);
                set_return(base, n);
            }
            2 => {
                crate::sched::sleep_task(a1);
                set_return(base, 0);
            }
            3 => {
                set_return(base, crate::sched::current_id().as_u64());
            }
            4 => {
                crate::sched::yield_task();
                set_return(base, 0);
            }
            5 => {
                // R-7: read_key — a getter over the K3 keyboard ring
                // buffer, no new machinery. Returns the next raw
                // PS/2 set-1 scancode byte (0..=255, release codes
                // included, NOT decoded ASCII — decoding stays in
                // the console task), or u64::MAX when the buffer is
                // empty (non-blocking; a caller that wants to wait
                // polls, or sleeps/yields between polls). Valid
                // returns are all <= 255, so MAX is unambiguous.
                // Shares the console's buffer: a byte read here is
                // consumed and is not echoed by the console task.
                set_return(base, match crate::interrupts::keyboard_read() {
                    Some(scancode) => scancode as u64,
                    None => u64::MAX,
                });
            }
            n => {
                println!("user bad syscall {} refused", n);
                set_return(base, u64::MAX);
            }
        }
    }
}

/// Serve `write`: validate the whole range is mapped (OS-080),
/// cap one page per call, print it.
unsafe fn user_write(buf: u64, len: u64) -> u64 {
    if len == 0 || len > 4096 {
        return 0;
    }
    if !crate::mem::is_mapped_range(buf, len) {
        println!("user write: unmapped buffer refused");
        return u64::MAX;
    }
    let bytes = core::slice::from_raw_parts(buf as *const u8, len as usize);
    match core::str::from_utf8(bytes) {
        Ok(s) => print!("{}", s),
        Err(_) => print!("[non-utf8 {} bytes]", len),
    }
    len
}

fn read_u16(elf: &[u8], off: usize) -> Option<u16> {
    elf.get(off..off + 2)
        .map(|b| u16::from_le_bytes([b[0], b[1]]))
}
fn read_u32(elf: &[u8], off: usize) -> Option<u32> {
    elf.get(off..off + 4)
        .map(|b| u32::from_le_bytes([b[0], b[1], b[2], b[3]]))
}
fn read_u64(elf: &[u8], off: usize) -> Option<u64> {
    elf.get(off..off + 8).map(|b| {
        u64::from_le_bytes([b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7]])
    })
}

/// Apply RELA relocations (OS-078): static-PIE binaries carry
/// R_X86_64_RELATIVE entries whose slots the file leaves zeroed;
/// the loader must write base + addend. Because we map at the
/// linked base, RELATIVE is identity-preserving, but the WRITE
/// itself is still required (slots start at 0 — found live: an
/// unrelocated GOT slot jumped the first program to address 0).
/// Any other relocation type refuses the load. Runs after all
/// LOADs are mapped, through the physmap like the file copy.
fn apply_relocations(
    elf: &[u8],
    mapper: &mut Mapper<'static, crate::mem::PhysMem>,
    mem: crate::mem::PhysMem,
) -> Result<(), &'static str> {
    // Find PT_DYNAMIC.
    let phoff = read_u64(elf, 32).ok_or("no phoff")? as usize;
    let phentsize = read_u16(elf, 54).ok_or("no phentsize")? as usize;
    let phnum = read_u16(elf, 56).ok_or("no phnum")? as usize;
    let mut dyn_off = None;
    for i in 0..phnum {
        let ph = phoff + i * phentsize;
        if read_u32(elf, ph).ok_or("phdr")? == 2 {
            dyn_off = Some(read_u64(elf, ph + 8).ok_or("dyn off")? as usize);
            break;
        }
    }
    let dyn_off = match dyn_off {
        Some(o) => o,
        None => return Ok(()), // No dynamic section: nothing to do.
    };
    // Scan tags: DT_RELA(7), DT_RELASZ(8), DT_RELAENT(9).
    let mut rela_off = None;
    let mut rela_size = 0usize;
    let mut rela_entsize = 0usize;
    let mut o = dyn_off;
    loop {
        let tag = read_u64(elf, o).ok_or("dyn tag")? as i64;
        let val = read_u64(elf, o + 8).ok_or("dyn val")?;
        match tag {
            0 => break,
            7 => rela_off = Some(val as usize),
            8 => rela_size = val as usize,
            9 => rela_entsize = val as usize,
            _ => {}
        }
        o += 16;
        if o + 16 > elf.len() {
            return Err("dyn overrun");
        }
    }
    let rela_off = match rela_off {
        Some(o) => o,
        None => return Ok(()),
    };
    if rela_entsize != 24 {
        return Err("rela entsize");
    }
    // RELA table lives inside a LOAD: find its file offset.
    let mut rela_file_off = None;
    for i in 0..phnum {
        let ph = phoff + i * phentsize;
        if read_u32(elf, ph).ok_or("phdr")? != 1 {
            continue;
        }
        let p_offset = read_u64(elf, ph + 8).ok_or("phdr off")? as usize;
        let p_vaddr = read_u64(elf, ph + 16).ok_or("phdr vaddr")? as usize;
        let p_filesz = read_u64(elf, ph + 32).ok_or("phdr filesz")? as usize;
        if p_vaddr <= rela_off && rela_off - p_vaddr < p_filesz {
            rela_file_off = Some(p_offset + (rela_off - p_vaddr));
            break;
        }
    }
    let rela_file_off = rela_file_off.ok_or("rela outside loads")?;
    let count = rela_size / 24;
    for i in 0..count {
        let e = rela_file_off + i * 24;
        let r_offset = read_u64(elf, e).ok_or("rela off")?;
        let r_info = read_u64(elf, e + 8).ok_or("rela info")?;
        let r_addend = read_u64(elf, e + 16).ok_or("rela addend")? as i64 as u64;
        if (r_info & 0xFFFFFFFF) != 8 {
            return Err("non-RELATIVE reloc");
        }
        // RELATIVE means "write load-bias + addend". Our bias is
        // ZERO (we map at the linked addresses), so the value is
        // just the addend — NOT location + addend (that bug doubled
        // the base and jumped userspace to 0xC000..., found live).
        // Verify with the file: slot = addend must be a sane linked
        // address, never a doubled base.
        // Write base + addend through the physmap.
        let phys = mapper
            .translate(VirtAddr(r_offset & !0xFFF))
            .ok_or("reloc unmapped")?
            .0 + (r_offset & 0xFFF);
        unsafe {
            ((mem.offset + phys) as *mut u64).write(r_addend);
        }
    }
    Ok(())
}
/// Map one ELF at its linked addresses (OS-078). Every LOAD segment
/// gets fresh frames from the mapper's own allocator, with W/R/X
/// from `p_flags`; covering pages align defensively (the link script
/// page-aligns, but any ELF must load); file bytes copy through the
/// physmap; the BSS tail zeroes. Refuses bad magic, non-executable
/// files, zero entry, address overflow, and any page already mapped.
/// Returns entry.
pub unsafe fn load_elf(
    elf: &[u8],
    mapper: &mut Mapper<'static, crate::mem::PhysMem>,
    mem: crate::mem::PhysMem,
) -> Result<u64, &'static str> {
    if elf.len() < 64 || &elf[0..4] != b"\x7fELF" {
        return Err("bad magic");
    }
    if read_u16(elf, 16) != Some(2) && read_u16(elf, 16) != Some(3) {
        return Err("not ET_EXEC/ET_DYN");
    }
    // ET_DYN (static-PIE) is accepted ONLY because the loader maps
    // at the linked addresses: relative relocations are then
    // identity and need no processing. A relocated load would be
    // a different loader (stated, OS-078).
    if read_u16(elf, 18) != Some(62) {
        return Err("not x86-64");
    }
    let entry = read_u64(elf, 24).ok_or("no entry")?;
    if entry == 0 {
        return Err("zero entry");
    }
    let phoff = read_u64(elf, 32).ok_or("no phoff")? as usize;
    let phentsize = read_u16(elf, 54).ok_or("no phentsize")? as usize;
    let phnum = read_u16(elf, 56).ok_or("no phnum")? as usize;
    if phentsize < 56 {
        return Err("phentsize");
    }
    // Pages this load already mapped (intra-ELF sharing skips).
    let mut already = [0u64; 32];
    let mut already_n = 0usize;
    for i in 0..phnum {
        let ph = phoff + i * phentsize;
        let p_type = read_u32(elf, ph).ok_or("phdr")?;
        if p_type != 1 {
            continue;
        }
        let p_flags = read_u32(elf, ph + 4).ok_or("phdr flags")?;
        let p_offset = read_u64(elf, ph + 8).ok_or("phdr off")? as usize;
        let p_vaddr = read_u64(elf, ph + 16).ok_or("phdr vaddr")?;
        let p_filesz = read_u64(elf, ph + 32).ok_or("phdr filesz")? as usize;
        let p_memsz = read_u64(elf, ph + 40).ok_or("phdr memsz")? as usize;
        if p_memsz == 0 {
            continue;
        }
        // Map whole covering pages (defensive align-down/up; the
        // link script page-aligns, but any ELF must load).
        let first = p_vaddr & !0xFFF;
        let span_end = p_vaddr
            .checked_add(p_memsz as u64)
            .ok_or("segment overflow")?;
        let pages = span_end.saturating_sub(first).div_ceil(4096);
        let writable = p_flags & 2 != 0;
        let executable = p_flags & 1 != 0;
        let mut flags = ENTRY_WRITABLE;
        if !executable {
            flags |= ENTRY_NO_EXECUTE;
        }
        if !writable {
            flags &= !ENTRY_WRITABLE;
        }
        for p in 0..pages {
            let v = first + (p as u64) * 4096;
            // Same page twice inside one ELF (tightly packed
            // segments sharing a covering page): map once. Across
            // ELFs, a mapped page is still a hard refusal below.
            if already.contains(&v) {
                continue;
            }
            if already_n < already.len() {
                already[already_n] = v;
                already_n += 1;
            }
            if mapper.translate(VirtAddr(v)).is_some() {
                return Err("address in use");
            }
            let frame = mapper.allocate_frame().ok_or("out of frames")?;
            mapper
                .map_page(VirtAddr(v), frame, flags | crate::memory::ENTRY_USER, true)
                .map_err(|e| match e {
                    MapError::AlreadyMapped => "address in use",
                    MapError::UnalignedAddress => "unaligned",
                    _ => "map failed",
                })?;
            crate::mem::invlpg(v);
        }
        // Copy file bytes through the physmap, zero the BSS tail.
        let file = elf
            .get(p_offset..p_offset + p_filesz)
            .ok_or("segment outside file")?;
        for (j, byte) in file.iter().enumerate() {
            let v = p_vaddr + j as u64;
            let phys = mapper
                .translate(VirtAddr(v & !0xFFF))
                .ok_or("translate lost")?
                .0 + (v & 0xFFF);
            ((mem.offset + phys) as *mut u8).write(*byte);
        }
        for j in p_filesz..p_memsz {
            let v = p_vaddr + j as u64;
            let phys = mapper
                .translate(VirtAddr(v & !0xFFF))
                .ok_or("translate lost")?
                .0 + (v & 0xFFF);
            ((mem.offset + phys) as *mut u8).write(0);
        }
    }
    // Static-PIE slots start at zero: relocate after mapping.
    apply_relocations(elf, mapper, mem)?;
    // Revalidate the entry: relocation writes must not have unmapped it.
    if mapper.translate(VirtAddr(entry & !0xFFF)).is_none() {
        return Err("entry unmapped");
    }
    Ok(entry)
}

/// Enter userspace (OS-076/079): TSS.rsp0 to this task's kernel
/// stack, then `iretq` with RPL 3 segments. Never returns.
pub unsafe fn enter_userspace(entry: u64, user_sp: u64) -> ! {
    let kstack = crate::sched::current_kstack_top().expect("user: no task");
    set_rsp0(kstack);
    core::arch::asm!(
        "push {ss:r}",
        "push {sp:r}",
        "push {fl:r}",
        "push {cs:r}",
        "push {ip:r}",
        "iretq",
        ss = in(reg) USER_DATA_SELECTOR as u64,
        sp = in(reg) user_sp,
        fl = in(reg) 0x202u64,
        cs = in(reg) USER_CODE_SELECTOR as u64,
        ip = in(reg) entry,
        options(nostack, noreturn),
    );
}

/// Take a user stack slot (max 4 programs, K6 scope + R5-2 readkey;
/// a 5th is refused, not silently shared).
fn take_ustack() -> Option<u64> {
    unsafe {
        if NEXT_USTACK >= 4 {
            return None;
        }
        let top = map_ustack(NEXT_USTACK)?;
        NEXT_USTACK += 1;
        Some(top)
    }
}

/// Load an ELF and enter it. Used as the entry of a kernel task.
unsafe fn run_elf(elf: &'static [u8], name: &str) -> ! {
    let ustack = take_ustack().expect("user: no stack left");
    let magic = read_u32(elf, 0);
    let etype = read_u16(elf, 16);
    let eentry = read_u64(elf, 24);
    println!(
        "user {}: {} bytes magic={:#x} type={:?} entry={:?}",
        name,
        elf.len(),
        magic.unwrap_or(0),
        etype,
        eentry
    );
    let loaded = crate::mem::with_mapper(|mapper, mem| {
        load_elf(elf, mapper, mem)
    });
    match loaded {
        Some(Ok(entry)) => {
            // Debug: dump the first 16 bytes the CPU will fetch.
            let mut head = [0u8; 16];
            for (i, b) in head.iter_mut().enumerate() {
                let v = entry + i as u64;
                let phys = crate::mem::with_mapper(|mapper, _| {
                    mapper.translate(VirtAddr(v & !0xFFF))
                })
                .flatten()
                .map(|p| p.0 + (v & 0xFFF));
                *b = phys
                    .map(|p| unsafe {
                        (crate::mem::phys_offset() + p) as *const u8
                    })
                    .map(|p| unsafe { p.read() })
                    .unwrap_or(0xFF);
            }
            println!(
                "user {}: entry {:#x} head {:02x?}",
                name, entry, head
            );
            enter_userspace(entry, ustack);
        }
        Some(Err(e)) => {
            println!("user {} loader refused: {}", name, e);
            crate::sched::exit_task();
        }
        None => {
            println!("user {}: no mapper yet, task exits", name);
            crate::sched::exit_task();
        }
    }
}

/// Kernel task entries for the three programs.
pub fn task_hello() {
    unsafe { run_elf(HELLO_ELF, "hello") };
}
pub fn task_sleeper() {
    unsafe { run_elf(SLEEPER_ELF, "sleeper") };
}
pub fn task_crasher() {
    unsafe { run_elf(CRASHER_ELF, "crasher") };
}
/// Kernel task entry for the fourth program (R5-2 follow-up).
pub fn task_readkey() {
    unsafe { run_elf(READKEY_ELF, "readkey") };
}
