//! SINGLE-CPU SOUNDNESS (OS-086 ledger): every static-mut access below is justified there;
//! the lint below only silences the compiler's general warning for this proven-single-CPU kernel.
#![allow(static_mut_refs)]
//! Meta OS kernel, Section D (K4): memory wiring (OS-045..OS-060).
//!
//! Converts the bootloader's memory map into `memory.rs` regions,
//! builds the bitmap frame allocator, roots a mapper at the live CR3
//! through the physical-memory offset, proves one fresh mapping with
//! a write/read-back, and brings up the linked-list heap as the
//! global allocator (Box/Vec). `core` + `alloc` only.

use alloc::boxed::Box;
use alloc::vec::Vec;
use core::alloc::{GlobalAlloc, Layout};

use crate::memory::{
    FrameAllocator, Heap, Mapper, MemoryMap, MemoryRegion,
    PhysAddr, RegionKind, TableMemory, VirtAddr, ENTRY_NO_EXECUTE,
    ENTRY_WRITABLE,
};

/// Heap backing store: 256 KiB inside the kernel image (marked
/// Kernel, never in the usable map, so the allocator can't hand it
/// out as frames).
static mut HEAP_BUF: [u8; 256 * 1024] = [0; 256 * 1024];
/// Frame bitmap: 2048 words cover 131072 frames = 512 MiB of RAM.
static mut BITMAP: [u64; 2048] = [0; 2048];
/// Converted regions (bootloader map is small; 64 slots is plenty).
static mut REGIONS: [MemoryRegion; 64] = [MemoryRegion {
    start: PhysAddr(0),
    end: PhysAddr(0),
    kind: RegionKind::Other,
}; 64];
static mut HEAP: Option<Heap> = None;
static mut MAP: Option<MemoryMap<'static>> = None;
static mut MAPPER: Option<Mapper<'static, PhysMem>> = None;
/// The bootloader's physical-memory offset, latched at init for
/// latecomers (the userspace loader runs long after `mem_init`).
static mut PHYS_OFFSET: u64 = 0;

/// Page-table access through the bootloader's full-physical mapping.
#[derive(Clone, Copy)]
pub struct PhysMem {
    /// The bootloader's physical-memory offset (virtual = phys + this).
    pub offset: u64,
}

impl TableMemory for PhysMem {
    fn read_entry(&self, table: PhysAddr, index: usize) -> u64 {
        assert!(index < 512);
        unsafe { ((self.offset + table.0) as *const u64).add(index).read_volatile() }
    }
    fn write_entry(&mut self, table: PhysAddr, index: usize, value: u64) {
        assert!(index < 512);
        unsafe {
            ((self.offset + table.0) as *mut u64).add(index).write_volatile(value)
        };
    }
}

/// Global allocator over the Section D heap. Interrupts never
/// allocate (handlers only print and count), and K4 is single-CPU,
/// so the `static mut` heap behind a `Sync` shell is sound here.
struct KernelAlloc;
unsafe impl Sync for KernelAlloc {}
unsafe impl GlobalAlloc for KernelAlloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let heap = &mut *core::ptr::addr_of_mut!(HEAP);
        match heap.as_mut() {
            Some(heap) => heap
                .alloc(layout.size(), layout.align())
                .unwrap_or(core::ptr::null_mut()),
            None => core::ptr::null_mut(),
        }
    }
    unsafe fn dealloc(&self, ptr: *mut u8, _layout: Layout) {
        let heap = &mut *core::ptr::addr_of_mut!(HEAP);
        if let Some(heap) = heap.as_mut() {
            heap.dealloc(ptr);
        }
    }
}

#[global_allocator]
static ALLOC: KernelAlloc = KernelAlloc;

fn cr3() -> u64 {
    let value: u64;
    unsafe {
        core::arch::asm!("mov {}, cr3", out(reg) value,
            options(nomem, nostack, preserves_flags));
    }
    value
}

/// Invalidate one translation. Wiring (unmap/new map) calls this;
/// the mapper itself never touches the TLB (see `unmap_page`).
pub fn invlpg(addr: u64) {
    unsafe {
        core::arch::asm!("invlpg [{}]", in(reg) addr,
            options(nostack, preserves_flags));
    }
}

fn kind_of(t: bootloader::bootinfo::MemoryRegionType) -> RegionKind {
    use bootloader::bootinfo::MemoryRegionType::*;
    match t {
        Usable => RegionKind::Usable,
        Kernel | KernelStack | PageTable | Bootloader | BootInfo | FrameZero | InUse
        | Reserved => RegionKind::Reserved,
        _ => RegionKind::Other,
    }
}

/// First mapping probe: high, PML4 index 14, almost certainly free;
/// `translate` says for sure before anything is written.
const PROBE_VADDR: u64 = 0x0000_7000_0000_0000;

/// Bring up frames, mapper, and heap. Prints the map counts, the
/// mapping proof, the Box/Vec proof, the 10k stress result, and the
/// memory summary (OS-045/048/050/051/053).
///
/// # Safety
/// Call once, after the IDT is live (a stray fault must print, not
/// triple-fault), on the single boot CPU.
pub unsafe fn mem_init(boot_info: &'static bootloader::BootInfo) {
    let offset = boot_info.physical_memory_offset;
    let mut n = 0usize;
    let mut usable = 0u64;
    let mut reserved = 0u64;
    let mut other = 0u64;
    for r in boot_info.memory_map.iter() {
        if n >= REGIONS.len() {
            break;
        }
        let kind = kind_of(r.region_type);
        // 0.9.35 reports frame numbers, not byte addresses.
        let start = r.range.start_frame_number * 4096;
        let end = r.range.end_frame_number * 4096;
        let len = end.saturating_sub(start);
        match kind {
            RegionKind::Usable => usable += len,
            RegionKind::Reserved => reserved += len,
            RegionKind::Other => other += len,
        }
        REGIONS[n] = MemoryRegion {
            start: PhysAddr(start),
            end: PhysAddr(end),
            kind,
        };
        n += 1;
    }
    for (i, r) in REGIONS[..n].iter().enumerate() {
        let tag = match r.kind {
            RegionKind::Usable => "usable",
            RegionKind::Reserved => "reserved",
            RegionKind::Other => "other",
        };
        println!(
            "mem region {}: {:#x}-{:#x} {}",
            i,
            r.start.0,
            r.end.0,
            tag
        );
    }
    println!(
        "mem map: {} regions, usable {}K reserved {}K other {}K",
        n,
        usable / 1024,
        reserved / 1024,
        other / 1024
    );

    let regions: &'static [MemoryRegion] =
        unsafe { &*core::ptr::addr_of!(REGIONS) };
    MAP = Some(MemoryMap::new(regions));
    let map: &'static MemoryMap<'static> =
        unsafe { (*core::ptr::addr_of!(MAP)).as_ref().unwrap() };
    println!("mem frames: {} usable total", map.total_usable_frames());
    let bitmap: &'static mut [u64] =
        unsafe { &mut *core::ptr::addr_of_mut!(BITMAP) };
    let mut allocator = FrameAllocator::new(map, bitmap);
    println!(
        "mem allocator: {} covered frames, {} free",
        allocator.covered_frames(),
        allocator.free_frames()
    );

    let root = PhysAddr(cr3() & 0x000f_ffff_ffff_f000);

    // One fresh mapping, proven by write/read-back (OS-048). The
    // probe frame comes from the same allocator the mapper owns.
    let virt = VirtAddr(PROBE_VADDR);
    let frame = allocator.allocate().expect("mem: out of frames");
    let mut mapper = Mapper::new(root, PhysMem { offset }, allocator);
    assert!(mapper.translate(virt).is_none());
    mapper
        .map_page(virt, frame, ENTRY_WRITABLE | ENTRY_NO_EXECUTE, false)
        .expect("mem: probe map failed");
    invlpg(PROBE_VADDR);
    assert!(mapper.translate(virt).is_some());
    (PROBE_VADDR as *mut u64).write_volatile(0x4d454d4f53505242);
    let back = (PROBE_VADDR as *const u64).read_volatile();
    assert!(back == 0x4d454d4f53505242);
    println!("mem probe page ok");

    #[cfg(feature = "guard-test")]
    {
        use crate::memory::VirtAddr as V;
        let _ = mapper.unmap_page(V(PROBE_VADDR));
        invlpg(PROBE_VADDR);
        // Must fault with the probe address in CR2 (OS-052).
        core::ptr::read_volatile(PROBE_VADDR as *const u8);
    }

    // Heap + global allocator (OS-049/050).
    let heap = Heap::init(&mut HEAP_BUF).expect("mem: heap init failed");
    println!("mem heap: {}K total", heap.total_size() / 1024);
    HEAP = Some(heap);
    let boxed = Box::new(42u64);
    assert!(*boxed == 42);
    let mut vec = Vec::new();
    for i in 0u64..16 {
        vec.push(i);
    }
    let sum: u64 = vec.iter().sum();
    assert!(sum == 120);
    println!("mem Box+Vec ok (box {}, vec sum {})", *boxed, sum);

    // 10k alloc/free stress (OS-051).
    for i in 0u32..10_000 {
        let b = Box::new(i);
        assert!(*b == i);
    }
    if let Some(heap) = unsafe { &mut *core::ptr::addr_of_mut!(HEAP) }.as_mut() {
        println!(
            "mem stress 10k ok, heap free {}K",
            heap.free_bytes() / 1024
        );
    }

    MAPPER = Some(mapper);
    PHYS_OFFSET = offset;
    println!("mem summary: K4 up");
}

/// The bootloader's physical-memory offset (for direct phys reads).
pub fn phys_offset() -> u64 {
    unsafe { PHYS_OFFSET }
}

/// Run `f` with the live mapper and a `PhysMem` reader. `None` when
/// memory is not up yet (never in practice: userspace starts after
/// `mem_init`, but the loader refuses instead of assuming).
pub fn with_mapper<R>(
    f: impl FnOnce(&mut Mapper<'static, PhysMem>, PhysMem) -> R,
) -> Option<R> {
    unsafe {
        let mapper = (*core::ptr::addr_of_mut!(MAPPER)).as_mut()?;
        let mem = PhysMem { offset: PHYS_OFFSET };
        Some(f(mapper, mem))
    }
}

/// Heap free bytes for the status command (OS-207).
pub fn heap_free_bytes() -> u64 {
    unsafe {
        match (*core::ptr::addr_of!(HEAP)).as_ref() {
            Some(heap) => heap.free_bytes() as u64,
            None => 0,
        }
    }
}

/// Heap total bytes for the mem command (R-5). Mirrors
/// `heap_free_bytes`; 0 before `mem_init` brings the heap up.
pub fn heap_total_bytes() -> u64 {
    unsafe {
        match (*core::ptr::addr_of!(HEAP)).as_ref() {
            Some(heap) => heap.total_size() as u64,
            None => 0,
        }
    }
}

/// Usable frames in the converted memory map for the mem command
/// (R-5): the same count `mem_init` prints as "usable total".
pub fn frames_total() -> u64 {
    unsafe {
        match (*core::ptr::addr_of!(MAP)).as_ref() {
            Some(map) => map.total_usable_frames() as u64,
            None => 0,
        }
    }
}

/// Covered frames still free in the frame allocator for the mem
/// command (R-5), via the mapper that owns the allocator. 0 when
/// the mapper is not up yet.
pub fn frames_free() -> u64 {
    with_mapper(|mapper, _| mapper.free_frames()).unwrap_or(0) as u64
}
/// True when every page of `[start, start+len)` is currently mapped.
/// Used to validate userspace buffers (OS-080): an unmapped byte
/// refuses the call instead of faulting the kernel.
pub fn is_mapped_range(start: u64, len: u64) -> bool {
    if len == 0 || len > 4096 {
        return false;
    }
    let mut page = start & !0xFFF;
    let end = start.saturating_add(len);
    unsafe {
        match MAPPER.as_ref() {
            Some(mapper) => {
                while page < end {
                    if mapper.translate(VirtAddr(page)).is_none() {
                        return false;
                    }
                    page = match page.checked_add(4096) {
                        Some(p) => p,
                        None => return false,
                    };
                }
                true
            }
            None => false,
        }
    }
}
