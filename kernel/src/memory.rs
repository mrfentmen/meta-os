//! Meta OS kernel, milestone K4: memory management (UNWIRED).
//!
//! Status: **WRITTEN, NOT WIRED INTO `main.rs`, NOT A KERNEL-CRATE
//! COMPILE, NOT A BOOT VERDICT.** This file is code, not a running
//! memory system, and no claim is made that it boots or that any page
//! has ever been mapped by it. Per KERNEL_SPEC.md rule 2, it counts
//! only when it builds on the boss's Mac and a QEMU boot shows its
//! behavior. Per ROWAN_LAYER0_TASKS.md RW-L0-02, it is drafted
//! unwired in the R2/R3 pattern, and per RW-L0-01 it is wired into
//! `main.rs` only onto the proven tree, one module per commit, after
//! a K1 boot log exists and `kernel/Cargo.lock` is committed (Q1).
//! Until then it is code, not a running kernel.
//!
//! Authority: boss layer order 2026-11-01 ~08:18, relayed by Pax on
//! room 1 and written into `os-build/LAYERS.md` +
//! `ROWAN_LAYER0_TASKS.md` on main: Rowan owns Layers 1-3 (boot,
//! kernel core, drivers; renumbered to seven layers on the boss's
//! word 2026-11-01 ~09:02, file name and RW-L0-02 ID kept as stable
//! identifiers), and RW-L0-02 assigns Rowan this K4 draft unwired. `kernel/Cargo.lock` is STILL absent on
//! main (checked this run: 404, main tip 91dbbf5), so there is still
//! no resolved bootloader version to write against. What this module
//! does about that, honestly, following the R2/R3 precedent:
//!
//! - It does NOT import any bootloader type and it does NOT depend
//!   on any external crate. Every structure below is local, defined
//!   from the x86_64 long-mode paging layout, and uses `core` only,
//!   no `alloc`, so it cannot drag a dependency question into R5.
//! - It does NOT assert any bootloader API name. The physical memory
//!   map arrives as `MemoryMap`, a plain slice of local
//!   `MemoryRegion` values; the R5 wiring commit is a thin adapter
//!   that translates whatever memory-map accessor Q10 confirms at
//!   the resolved bootloader version into those values. No accessor
//!   name is asserted here, so none can be wrong here.
//! - Page-table access goes through the `TableMemory` trait. The R5
//!   adapter implements it over the physical-memory mapping the
//!   kernel crate already requests (`map_physical_memory` in
//!   `kernel/Cargo.toml`); this file never touches a page table
//!   through a guessed address. A host test can implement the trait
//!   over a map of tables, which is how this module's logic is
//!   exercised before any boot (see the check note below).
//! - The heap allocates only inside a caller-supplied buffer. It
//!   never claims heap memory the kernel does not own; where that
//!   buffer comes from on the real machine (a region the memory map
//!   marks usable, after the kernel image) is Q10's business, and
//!   the R5 commit must say which region it used.
//!
//! Check note (exact words): this module was checked on this VM with
//! standalone `rustc 1.99.1` (`rustc --edition 2021 --crate-type
//! lib`, host target, warnings denied) plus a host test harness in
//! `/tmp` (not shipped) implementing `TableMemory` over a table map
//! and exercising the allocator, mapper, and heap below. That is
//! standalone-clean plus host-exercised logic. It is NOT a kernel
//! crate compile (no `no_std` target, no bootloader crate linked)
//! and NOT a boot verdict. The Mac build + QEMU log remain the proof.
//!
//! Wiring contract (for the R5 commit): `main.rs` gains
//! `mod memory;`, builds a `MemoryMap` from the bootloader memory
//! map, a `FrameAllocator` over a caller-sized bitmap, a `Mapper`
//! rooted at the current top-level table with a `TableMemory`
//! implementation over the physical-memory mapping, and a `Heap`
//! over a usable region. This file needs no other crate item.
//!
//! No mocks (KERNEL_SPEC.md rule 6): every function below moves
//! real frames, real table entries, or real heap bytes in the
//! caller-supplied structures. An allocation that cannot be
//! satisfied returns `None` / `Err`, never a faked address. A frame
//! outside the usable regions is never handed out, and a double
//! free is refused, never silently accepted.
//!
//! Safety contract (for the R5 commit and for callers generally):
//! the caller owns the memory map, the bitmap, the tables, and the
//! heap buffer exclusively while these structures live. `Heap`
//! pointers passed to `dealloc` must come from `Heap::alloc` on
//! the same heap; anything else is refused on a best-effort basis
//! only (range and span checks), and a wild pointer that passes
//! those checks can still corrupt the free list. That is the
//! documented contract, not a guarantee.

// ---------------------------------------------------------------------------
// Addresses
// ---------------------------------------------------------------------------

/// One page: 4096 bytes. All frames and pages in this module are
/// this size; huge pages are recognised on translate, never created
/// by `Mapper::map_page`.
pub const PAGE_SIZE: usize = 4096;

/// Same value as a `u64`, for address arithmetic.
pub const PAGE_SIZE_U64: u64 = 4096;

/// Entries in one page table (512 x 8 bytes = one page).
pub const ENTRIES_PER_TABLE: usize = 512;

/// A physical address. A plain `u64` wrapper: no paging structure
/// is hidden inside it, and no address is ever dereferenced by this
/// module (table access goes through `TableMemory`).
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub struct PhysAddr(pub u64);

impl PhysAddr {
    /// Wrap a raw address.
    pub const fn new(addr: u64) -> PhysAddr {
        PhysAddr(addr)
    }

    /// The raw address.
    pub const fn as_u64(self) -> u64 {
        self.0
    }

    /// True when this address is a page boundary.
    pub const fn is_page_aligned(self) -> bool {
        self.0 % PAGE_SIZE_U64 == 0
    }

    /// Round down to the page boundary at or below this address.
    pub const fn align_down(self) -> PhysAddr {
        PhysAddr(self.0 & !(PAGE_SIZE_U64 - 1))
    }

    /// Round up to the page boundary at or above this address, or
    /// `None` on overflow.
    pub fn align_up(self) -> Option<PhysAddr> {
        let aligned = (self.0.checked_add(PAGE_SIZE_U64 - 1)?) & !(PAGE_SIZE_U64 - 1);
        Some(PhysAddr(aligned))
    }

    /// Add a byte offset, or `None` on overflow.
    pub fn checked_add(self, bytes: u64) -> Option<PhysAddr> {
        Some(PhysAddr(self.0.checked_add(bytes)?))
    }
}

/// A virtual address. Page-table indices are derived from it, never
/// from a guessed layout: level 4 takes bits 39..47, level 3 bits
/// 30..38, level 2 bits 21..29, level 1 bits 12..20.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub struct VirtAddr(pub u64);

impl VirtAddr {
    /// Wrap a raw address.
    pub const fn new(addr: u64) -> VirtAddr {
        VirtAddr(addr)
    }

    /// The raw address.
    pub const fn as_u64(self) -> u64 {
        self.0
    }

    /// True when this address is a page boundary.
    pub const fn is_page_aligned(self) -> bool {
        self.0 % PAGE_SIZE_U64 == 0
    }

    /// Byte offset inside its page.
    pub const fn page_offset(self) -> usize {
        (self.0 as usize) & (PAGE_SIZE - 1)
    }

    /// Index into the level-4 table (bits 39..47).
    pub const fn p4_index(self) -> usize {
        ((self.0 >> 39) & 0x1ff) as usize
    }

    /// Index into the level-3 table (bits 30..38).
    pub const fn p3_index(self) -> usize {
        ((self.0 >> 30) & 0x1ff) as usize
    }

    /// Index into the level-2 table (bits 21..29).
    pub const fn p2_index(self) -> usize {
        ((self.0 >> 21) & 0x1ff) as usize
    }

    /// Index into the level-1 table (bits 12..20).
    pub const fn p1_index(self) -> usize {
        ((self.0 >> 12) & 0x1ff) as usize
    }

    /// Index into the table at `level` (4, 3, 2, or 1; anything else
    /// reads as level 1, so a bad level cannot index out of range).
    pub const fn index_at_level(self, level: u8) -> usize {
        match level {
            4 => self.p4_index(),
            3 => self.p3_index(),
            2 => self.p2_index(),
            _ => self.p1_index(),
        }
    }
}

// ---------------------------------------------------------------------------
// Physical memory map (local taxonomy; the R5 adapter fills it in)
// ---------------------------------------------------------------------------

/// What a physical region may be used for. This is OUR taxonomy, not
/// a bootloader's: the R5 adapter maps every region the bootloader
/// reports onto exactly one of these, and only `Usable` regions are
/// ever handed out by the frame allocator. Anything the adapter
/// cannot classify lands in `Other`, which is never allocated.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum RegionKind {
    /// Free RAM the kernel may hand out as frames or heap.
    Usable,
    /// RAM the kernel must not hand out (kernel image, tables,
    /// firmware reservations, anything already owned).
    Reserved,
    /// Reported but unclassified by the adapter. Never allocated.
    Other,
}

/// One contiguous physical region: `[start, end)`, end exclusive.
/// A region with `end <= start` is empty and contributes nothing.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct MemoryRegion {
    /// First byte of the region.
    pub start: PhysAddr,
    /// First byte past the region.
    pub end: PhysAddr,
    /// What the region may be used for.
    pub kind: RegionKind,
}

impl MemoryRegion {
    /// Length in bytes, or 0 for an empty/inverted region.
    pub const fn len(self) -> u64 {
        self.end.0.saturating_sub(self.start.0)
    }

    /// True when the region covers no bytes.
    pub const fn is_empty(self) -> bool {
        self.end.0 <= self.start.0
    }

    /// First page-aligned frame start inside the region, or `None`
    /// when the region holds no whole frame.
    pub fn first_frame(self) -> Option<PhysAddr> {
        let first = self.start.align_up()?;
        if first.0 < self.end.0 {
            Some(first)
        } else {
            None
        }
    }

    /// Number of whole frames inside the region.
    pub fn frame_count(self) -> usize {
        match self.first_frame() {
            None => 0,
            Some(first) => ((self.end.0 - first.0) / PAGE_SIZE_U64) as usize,
        }
    }

    /// True when `addr` is a page-aligned frame start inside this
    /// region (not merely inside it: an unaligned address, or an
    /// address in the head sliver before the first aligned frame,
    /// is not a frame of this region).
    pub fn contains_frame(self, addr: PhysAddr) -> bool {
        if !addr.is_page_aligned() {
            return false;
        }
        match self.first_frame() {
            None => false,
            Some(first) => addr.0 >= first.0 && addr.0 < self.end.0,
        }
    }
}

/// A caller-supplied slice of regions, in the order the adapter
/// reports them. Frame numbering follows slice order: region 0's
/// frames first, then region 1's, and so on. Overlapping usable
/// regions would double-count frames; the adapter must not report
/// any (two regions covering the same frame is a map error the
/// allocator cannot detect from the slice alone, and it is stated
/// here rather than papered over).
pub struct MemoryMap<'a> {
    /// The regions, in adapter order.
    pub regions: &'a [MemoryRegion],
}

impl<'a> MemoryMap<'a> {
    /// Wrap a region slice.
    pub const fn new(regions: &'a [MemoryRegion]) -> MemoryMap<'a> {
        MemoryMap { regions }
    }

    /// Total usable frames across all usable regions.
    pub fn total_usable_frames(&self) -> usize {
        let mut total: usize = 0;
        for region in self.regions {
            if region.kind == RegionKind::Usable {
                total = total.saturating_add(region.frame_count());
            }
        }
        total
    }

    /// The `index`-th usable frame in slice order, or `None` when
    /// `index` is past the last usable frame.
    pub fn frame_at(&self, index: usize) -> Option<PhysAddr> {
        let mut remaining = index;
        for region in self.regions {
            if region.kind != RegionKind::Usable {
                continue;
            }
            let count = region.frame_count();
            if remaining < count {
                let first = region.first_frame()?;
                return Some(PhysAddr(first.0 + (remaining as u64) * PAGE_SIZE_U64));
            }
            remaining -= count;
        }
        None
    }

    /// Index of a usable frame start, or `None` when `addr` is not
    /// a usable frame start (unaligned, reserved, other, or outside
    /// every region).
    pub fn frame_index(&self, addr: PhysAddr) -> Option<usize> {
        let mut base: usize = 0;
        for region in self.regions {
            if region.kind != RegionKind::Usable {
                continue;
            }
            if region.contains_frame(addr) {
                let first = region.first_frame()?;
                let offset = ((addr.0 - first.0) / PAGE_SIZE_U64) as usize;
                return Some(base + offset);
            }
            base = base.saturating_add(region.frame_count());
        }
        None
    }

    /// True when `addr` is a usable frame start.
    pub fn is_usable_frame(&self, addr: PhysAddr) -> bool {
        self.frame_index(addr).is_some()
    }
}

// ---------------------------------------------------------------------------
// Frame allocator (bitmap over the usable frames)
// ---------------------------------------------------------------------------

/// A bitmap frame allocator. One bit per usable frame, in
/// `MemoryMap` order; bit set means allocated. The bitmap is
/// caller-supplied and is cleared by `new` (every covered frame
/// starts free). Frames past the bitmap's coverage are never handed
/// out: a bitmap too small for the map silently shrinks the usable
/// pool to `covered_frames()`, and the adapter must size it with
/// `required_bitmap_words` instead of guessing.
pub struct FrameAllocator<'a> {
    map: &'a MemoryMap<'a>,
    bitmap: &'a mut [u64],
    /// Frames the bitmap covers (<= total usable frames).
    covered: usize,
    /// Frames currently allocated (only covered frames count).
    used: usize,
}

impl<'a> FrameAllocator<'a> {
    /// Bitmap words needed to cover `total_frames` frames.
    pub const fn required_bitmap_words(total_frames: usize) -> usize {
        (total_frames + 63) / 64
    }

    /// Build an allocator over `map` with `bitmap`. The bitmap is
    /// zeroed, so every covered frame starts free regardless of
    /// what the caller left in the slice.
    pub fn new(map: &'a MemoryMap<'a>, bitmap: &'a mut [u64]) -> FrameAllocator<'a> {
        for word in bitmap.iter_mut() {
            *word = 0;
        }
        let total = map.total_usable_frames();
        let covered = core::cmp::min(total, bitmap.len() * 64);
        FrameAllocator {
            map,
            bitmap,
            covered,
            used: 0,
        }
    }

    /// Usable frames in the map (covered or not).
    pub fn total_frames(&self) -> usize {
        self.map.total_usable_frames()
    }

    /// Frames this allocator can hand out (bitmap coverage).
    pub fn covered_frames(&self) -> usize {
        self.covered
    }

    /// Frames currently allocated.
    pub fn used_frames(&self) -> usize {
        self.used
    }

    /// Covered frames currently free.
    pub fn free_frames(&self) -> usize {
        self.covered - self.used
    }

    /// Hand out one usable frame: the lowest-numbered free covered
    /// frame. Returns `None` when no covered frame is free (pool
    /// exhausted, or bitmap coverage exhausted, both reported the
    /// same honest way: no frame).
    pub fn allocate(&mut self) -> Option<PhysAddr> {
        for (word_index, word) in self.bitmap.iter_mut().enumerate() {
            if *word == u64::MAX {
                continue;
            }
            let bit = (!*word).trailing_zeros() as usize;
            let index = word_index * 64 + bit;
            if index >= self.covered {
                // Free bits past coverage can only sit in the last
                // partially-covered word; later indices are larger,
                // so nothing later can be valid either.
                return None;
            }
            *word |= 1u64 << bit;
            self.used += 1;
            return self.map.frame_at(index);
        }
        None
    }

    /// Return a frame. Returns `false` (and changes nothing) when
    /// `frame` is not a usable frame start, is past bitmap
    /// coverage, or is already free (double free refused).
    pub fn deallocate(&mut self, frame: PhysAddr) -> bool {
        let index = match self.map.frame_index(frame) {
            Some(index) => index,
            None => return false,
        };
        if index >= self.covered {
            return false;
        }
        let word = &mut self.bitmap[index / 64];
        let mask = 1u64 << (index % 64);
        if *word & mask == 0 {
            return false;
        }
        *word &= !mask;
        self.used -= 1;
        true
    }
}

// ---------------------------------------------------------------------------
// Page tables (x86_64 long-mode layout, local types only)
// ---------------------------------------------------------------------------

/// Entry is present.
pub const ENTRY_PRESENT: u64 = 1;
/// Entry is writable.
pub const ENTRY_WRITABLE: u64 = 1 << 1;
/// Entry is accessible from userspace (see the note in `map_page`:
/// intermediate entries are created without this bit; the R5 commit
/// must OR it in for userspace mappings).
pub const ENTRY_USER: u64 = 1 << 2;
/// Write-through caching.
pub const ENTRY_WRITE_THROUGH: u64 = 1 << 3;
/// Caching disabled.
pub const ENTRY_NO_CACHE: u64 = 1 << 4;
/// Set by the CPU on first access.
pub const ENTRY_ACCESSED: u64 = 1 << 5;
/// Set by the CPU on first write.
pub const ENTRY_DIRTY: u64 = 1 << 6;
/// Huge page (1 GiB at level 3, 2 MiB at level 2). Recognised on
/// translate, never created by `map_page`.
pub const ENTRY_HUGE: u64 = 1 << 7;
/// Global (not flushed by a page-table switch).
pub const ENTRY_GLOBAL: u64 = 1 << 8;
/// Execute disabled.
pub const ENTRY_NO_EXECUTE: u64 = 1 << 63;
/// Address bits of an entry (bits 12..51).
pub const ENTRY_ADDR_MASK: u64 = 0x000f_ffff_ffff_f000;

/// One page-table entry: a frame address plus flag bits. Built with
/// `new`, which masks the frame to the address field, so stray low
/// bits in a caller-supplied frame cannot leak into the flags.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct PageTableEntry(pub u64);

impl PageTableEntry {
    /// Build an entry for `frame` with `flags`. `frame` must be
    /// page-aligned; unaligned low bits are dropped by the mask,
    /// which is a safety net, not permission to pass one (see
    /// `map_page`, which rejects unaligned frames outright).
    pub const fn new(frame: PhysAddr, flags: u64) -> PageTableEntry {
        PageTableEntry((frame.0 & ENTRY_ADDR_MASK) | flags)
    }

    /// The raw entry value.
    pub const fn raw(self) -> u64 {
        self.0
    }

    /// True when the present bit is set.
    pub const fn is_present(self) -> bool {
        self.0 & ENTRY_PRESENT != 0
    }

    /// True when the huge-page bit is set.
    pub const fn is_huge(self) -> bool {
        self.0 & ENTRY_HUGE != 0
    }

    /// The frame this entry points at (address field only).
    pub const fn frame(self) -> PhysAddr {
        PhysAddr(self.0 & ENTRY_ADDR_MASK)
    }

    /// The flag bits (everything outside the address field).
    pub const fn flags(self) -> u64 {
        self.0 & !ENTRY_ADDR_MASK
    }
}

/// How a `Mapper` reaches page-table memory. The R5 adapter
/// implements this over the physical-memory mapping; a host test
/// implements it over a table map. The trait is the whole hardware
/// boundary for paging: nothing else in this file reads or writes
/// a table, and no implementation detail of the adapter leaks in.
/// Index is always < 512 (callers pass `VirtAddr` indices); an
/// implementation may ignore out-of-range indices, but the mapper
/// never generates one.
pub trait TableMemory {
    /// Read entry `index` of the table at physical address `table`.
    fn read_entry(&self, table: PhysAddr, index: usize) -> u64;
    /// Write entry `index` of the table at physical address `table`.
    fn write_entry(&mut self, table: PhysAddr, index: usize, value: u64);
}

/// Why a mapping failed. Every failure leaves the tables exactly as
/// they were except for one documented case: `OutOfFrames` mid-walk
/// can leave freshly allocated (but empty, all-zero) intermediate
/// tables linked in. Those tables map nothing, so the failure is
/// still safe, and the next `map_page` for the same address reuses
/// them instead of allocating again.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum MapError {
    /// Virtual or physical address is not page-aligned.
    UnalignedAddress,
    /// The leaf entry is already present.
    AlreadyMapped,
    /// An intermediate entry is a huge page, so the address range
    /// it covers cannot hold 4 KiB mappings.
    HugePageConflict,
    /// No free frame for a new intermediate table.
    OutOfFrames,
}

/// A page-table mapper rooted at one top-level table. The root is a
/// physical frame address supplied by the caller (on the real
/// machine, the frame the CPU's top-level-table register points
/// at; this file never reads that register, so it never asserts
/// which register or value the bootloader left there).
pub struct Mapper<'a, T: TableMemory> {
    root: PhysAddr,
    mem: T,
    allocator: FrameAllocator<'a>,
}

impl<'a, T: TableMemory> Mapper<'a, T> {
    /// Build a mapper. `root` must be a usable frame holding the
    /// top-level table; this constructor does not check that (the
    /// table's contents are read on first use, and a bad root reads
    /// whatever the `TableMemory` implementation returns for it).
    pub fn new(root: PhysAddr, mem: T, allocator: FrameAllocator<'a>) -> Mapper<'a, T> {
        Mapper {
            root,
            mem,
            allocator,
        }
    }

    /// The root table's physical address.
    pub fn root(&self) -> PhysAddr {
        self.root
    }

    /// Hand out one usable frame from the backing allocator.
    /// Mac-build addition (opencode/os-build, OS-078): the userspace
    /// loader needs frames without owning the allocator; the mapper
    /// is the only owner, so the method lives here. Delegates
    /// directly; no policy, no caching.
    pub fn allocate_frame(&mut self) -> Option<PhysAddr> {
        self.allocator.allocate()
    }

    /// Covered frames still free in the backing allocator.
    pub fn free_frames(&self) -> usize {
        self.allocator.free_frames()
    }

    /// Translate a virtual address to the physical address it maps
    /// to, or `None` when any level is not present. Huge pages at
    /// level 3 (1 GiB) and level 2 (2 MiB) are honoured: the result
    /// is the huge frame plus the offset inside the huge page.
    pub fn translate(&self, virt: VirtAddr) -> Option<PhysAddr> {
        let mut table = self.root;
        for level in [4u8, 3, 2, 1] {
            let entry = PageTableEntry(self.mem.read_entry(table, virt.index_at_level(level)));
            if !entry.is_present() {
                return None;
            }
            if level == 1 {
                return entry.frame().checked_add(virt.page_offset() as u64);
            }
            if entry.is_huge() {
                // Huge page: level 3 spans 1 GiB, level 2 spans 2 MiB.
                let span: u64 = PAGE_SIZE_U64 << (9 * (level as u64 - 1));
                let offset = virt.as_u64() & (span - 1);
                return entry.frame().checked_add(offset);
            }
            table = entry.frame();
        }
        None
    }

    /// Map one 4 KiB page: `virt` (page-aligned) to `frame`
    /// (page-aligned) with `flags` (the present bit is always set
    /// by this function, even if the caller forgot it). Missing
    /// intermediate tables are allocated from the frame allocator
    /// and zeroed; their entries carry PRESENT | WRITABLE only.
    /// The caller ORs in USER / NO_EXECUTE / GLOBAL as the mapping
    /// requires. Returns `Err` without changing the leaf entry on
    /// every failure path (see `MapError` for the one exception:
    /// empty intermediate tables may stay linked after
    /// `OutOfFrames`).
    ///
    /// Mac-build addition (opencode/os-build, OS-079): `user`
    /// marks USER (U/S) on the leaf AND every intermediate table
    /// created for it — ring-3 code faults without the bit at any
    /// level (found live: first userspace entry faulted 0x15).
    pub fn map_page(
        &mut self,
        virt: VirtAddr,
        frame: PhysAddr,
        flags: u64,
        user: bool,
    ) -> Result<(), MapError> {
        if !virt.is_page_aligned() || !frame.is_page_aligned() {
            return Err(MapError::UnalignedAddress);
        }
        let mut table = self.root;
        for level in [4u8, 3, 2] {
            let index = virt.index_at_level(level);
            let entry = PageTableEntry(self.mem.read_entry(table, index));
            if entry.is_present() {
                if entry.is_huge() {
                    return Err(MapError::HugePageConflict);
                }
                table = entry.frame();
            } else {
                let new_table = match self.allocator.allocate() {
                    Some(frame) => frame,
                    None => return Err(MapError::OutOfFrames),
                };
                for i in 0..ENTRIES_PER_TABLE {
                    self.mem.write_entry(new_table, i, 0);
                }
                let table_flags = if user {
                    ENTRY_PRESENT | ENTRY_WRITABLE | ENTRY_USER
                } else {
                    ENTRY_PRESENT | ENTRY_WRITABLE
                };
                let entry_value =
                    PageTableEntry::new(new_table, table_flags).raw();
                self.mem.write_entry(table, index, entry_value);
                table = new_table;
            }
        }
        let leaf = PageTableEntry(self.mem.read_entry(table, virt.p1_index()));
        if leaf.is_present() {
            return Err(MapError::AlreadyMapped);
        }
        let leaf_flags = if user {
            flags | ENTRY_PRESENT | ENTRY_USER
        } else {
            flags | ENTRY_PRESENT
        };
        let entry_value = PageTableEntry::new(frame, leaf_flags).raw();
        self.mem.write_entry(table, virt.p1_index(), entry_value);
        Ok(())
    }

    /// Remove a 4 KiB mapping, returning the frame it pointed at,
    /// or `None` when the address is not mapped at 4 KiB granularity
    /// (unmapped, or under a huge page, which this function refuses
    /// to split). The frame is NOT freed: the caller owns it and
    /// returns it to the allocator explicitly. This function does
    /// NOT flush the translation cache: the R5 wiring must issue
    /// the invalidation after unmapping, or the stale entry stays
    /// live in the CPU. That step is hardware action, not table
    /// bookkeeping, so it belongs to the wiring, and it is stated
    /// here so it is not forgotten there.
    pub fn unmap_page(&mut self, virt: VirtAddr) -> Option<PhysAddr> {
        let mut table = self.root;
        for level in [4u8, 3, 2, 1] {
            let index = virt.index_at_level(level);
            let entry = PageTableEntry(self.mem.read_entry(table, index));
            if !entry.is_present() {
                return None;
            }
            if level == 1 {
                self.mem.write_entry(table, index, 0);
                return Some(entry.frame());
            }
            if entry.is_huge() {
                return None;
            }
            table = entry.frame();
        }
        None
    }
}

// ---------------------------------------------------------------------------
// Heap (linked-list allocator over a caller-supplied buffer)
// ---------------------------------------------------------------------------

/// Alignment of a heap block header (8 bytes on 64-bit). Every
/// header in a heap sits on this alignment: the heap start is
/// rounded up to it in `init`, payloads are at least this aligned
/// in `alloc` (a smaller caller alignment is strengthened to this,
/// which still satisfies it), and every split point is rounded up
/// to it. Without this, a header written at an arbitrary payload
/// offset would be a misaligned access.
const HEADER_ALIGN: usize = core::mem::align_of::<BlockHeader>();

/// Bytes a header occupies.
const HEADER_SIZE: usize = core::mem::size_of::<BlockHeader>();

/// A split remainder smaller than this is not worth a new free
/// block (it could not hold a header plus a usable payload), so the
/// whole block is consumed instead and the slack becomes internal
/// fragmentation of the allocation.
const MIN_SPLIT_REMAINDER: usize = HEADER_SIZE + 8;

/// One heap block header. `span` is the whole block in bytes, from
/// the block's start to the next block's start, header included.
/// `wasted` is the prefix between the block's start and this header
/// (0 for every free block, whose header sits at the block start;
/// nonzero for an allocated block whose payload alignment pushed
/// its header forward). `next` links the address-ordered free list
/// (null at the end) for free blocks, and is null and meaningless
/// for allocated blocks. Keeping the free list address-ordered is
/// what makes coalescing a neighbour check instead of a search.
///
/// The `wasted` field is what makes aligned allocation recoverable:
/// on free, the header is relocated to the block's start (the
/// prefix bytes are part of the freed block, so writing there is
/// safe), `wasted` resets to 0, and the block rejoins the free
/// list at its true start. Without it, the prefix would leak on
/// every aligned allocation and neighbouring blocks could never
/// coalesce across it.
#[repr(C)]
struct BlockHeader {
    span: usize,
    wasted: usize,
    next: *mut BlockHeader,
}

/// Round `value` up to `align` (a power of two), or `None` on
/// overflow. Used for heap addresses only; page alignment has its
/// own helpers above.
fn align_up_usize(value: usize, align: usize) -> Option<usize> {
    let aligned = value.checked_add(align - 1)? & !(align - 1);
    Some(aligned)
}

/// A heap over one caller-supplied buffer. `init` takes the buffer
/// and never touches memory outside it: every header, payload, and
/// split point is computed from the buffer's own bounds, and
/// `alloc` returns `None` rather than a pointer outside it. The
/// heap owns the buffer exclusively: aliasing it (a second heap,
/// or direct writes into it) breaks every invariant below, and
/// the caller must not do it.
pub struct Heap {
    /// Aligned start of the heap region (first header lives here).
    start: usize,
    /// End of the heap region (buffer end, not necessarily aligned).
    end: usize,
    /// Head of the address-ordered free list (null when empty).
    /// Every node sits at its block's start (`wasted` == 0).
    free_list: *mut BlockHeader,
}

impl Heap {
    /// Build a heap over `buffer`. The start is rounded up to
    /// header alignment, so a buffer whose start is unaligned loses
    /// a few bytes at the head; a buffer too small to hold one
    /// header plus 8 payload bytes yields `None`, never a heap
    /// that cannot allocate anything. The initial free list is a
    /// single block covering the whole aligned region.
    pub fn init(buffer: &mut [u8]) -> Option<Heap> {
        let base = buffer.as_mut_ptr() as usize;
        let buf_end = base.checked_add(buffer.len())?;
        let start = align_up_usize(base, HEADER_ALIGN)?;
        if start >= buf_end {
            return None;
        }
        let span = buf_end - start;
        if span < HEADER_SIZE + 8 {
            return None;
        }
        let header = start as *mut BlockHeader;
        unsafe {
            (*header).span = span;
            (*header).wasted = 0;
            (*header).next = core::ptr::null_mut();
        }
        Some(Heap {
            start,
            end: buf_end,
            free_list: header,
        })
    }

    /// Total heap bytes (aligned region, head rounding included).
    pub fn total_size(&self) -> usize {
        self.end - self.start
    }

    /// Payload bytes currently free (free spans minus their
    /// headers). After every allocation is freed and coalesced,
    /// this returns to `total_size() - HEADER_SIZE`.
    pub fn free_bytes(&self) -> usize {
        let mut total: usize = 0;
        let mut cur = self.free_list;
        while !cur.is_null() {
            let (span, next) = unsafe { ((*cur).span, (*cur).next) };
            total = total.saturating_add(span.saturating_sub(HEADER_SIZE));
            cur = next;
        }
        total
    }

    /// Allocate `size` payload bytes at `align` alignment (a power
    /// of two, else `None`; zero size is `None`, never a pointer).
    /// Payloads are at least header-aligned, so a smaller caller
    /// alignment is strengthened, never weakened. The header for
    /// the allocation sits immediately before the returned payload
    /// (`payload - HEADER_SIZE`) and records the wasted prefix, so
    /// `dealloc` can recover the whole block. A remainder that can
    /// hold a header plus payload becomes a new free block;
    /// anything smaller is consumed whole.
    pub fn alloc(&mut self, size: usize, align: usize) -> Option<*mut u8> {
        if size == 0 || align == 0 || (align & (align - 1)) != 0 {
            return None;
        }
        let effective_align = core::cmp::max(align, HEADER_ALIGN);
        let mut prev: *mut BlockHeader = core::ptr::null_mut();
        let mut cur = self.free_list;
        while !cur.is_null() {
            let (block_addr, block_span, next) =
                unsafe { (cur as usize, (*cur).span, (*cur).next) };
            let block_end = block_addr.checked_add(block_span)?;
            let payload = align_up_usize(block_addr + HEADER_SIZE, effective_align)?;
            let header_addr = payload.checked_sub(HEADER_SIZE)?;
            let consumed_end = payload.checked_add(size)?;
            if consumed_end <= block_end {
                // This block fits. Split point is header-aligned;
                // a split is worthwhile only when the remainder can
                // hold a header plus payload.
                let split_end = align_up_usize(consumed_end, HEADER_ALIGN)?;
                let split_ok =
                    split_end <= block_end && (block_end - split_end) >= MIN_SPLIT_REMAINDER;
                let wasted = header_addr - block_addr;
                if split_ok {
                    let new_header = split_end as *mut BlockHeader;
                    unsafe {
                        (*new_header).span = block_end - split_end;
                        (*new_header).wasted = 0;
                        (*new_header).next = next;
                    }
                    if prev.is_null() {
                        self.free_list = new_header;
                    } else {
                        unsafe {
                            (*prev).next = new_header;
                        }
                    }
                    let alloc_header = header_addr as *mut BlockHeader;
                    unsafe {
                        (*alloc_header).span = split_end - block_addr;
                        (*alloc_header).wasted = wasted;
                        (*alloc_header).next = core::ptr::null_mut();
                    }
                } else {
                    // Consume the whole block, slack included.
                    if prev.is_null() {
                        self.free_list = next;
                    } else {
                        unsafe {
                            (*prev).next = next;
                        }
                    }
                    let alloc_header = header_addr as *mut BlockHeader;
                    unsafe {
                        (*alloc_header).span = block_end - block_addr;
                        (*alloc_header).wasted = wasted;
                        (*alloc_header).next = core::ptr::null_mut();
                    }
                }
                return Some(payload as *mut u8);
            }
            prev = cur;
            cur = next;
        }
        None
    }

    /// Free a pointer from `alloc` on this heap. Returns `false`
    /// (and changes nothing) for a null pointer, a pointer whose
    /// header falls outside the heap, a header with an impossible
    /// span, or a block already on the free list (double free).
    /// On success the block's header is relocated to the block's
    /// true start (recovering the alignment prefix), the block
    /// rejoins the address-ordered free list, and it coalesces
    /// with any free neighbour on either side, so a fully freed
    /// heap is one block again. A wild pointer that passes the
    /// range/span checks is NOT caught: the caller contract (see
    /// the module header) forbids it.
    pub fn dealloc(&mut self, ptr: *mut u8) -> bool {
        if ptr.is_null() {
            return false;
        }
        let header_addr = match (ptr as usize).checked_sub(HEADER_SIZE) {
            Some(addr) => addr,
            None => return false,
        };
        if header_addr < self.start || header_addr % HEADER_ALIGN != 0 {
            return false;
        }
        let (span, wasted) = unsafe {
            let header = &*(header_addr as *const BlockHeader);
            (header.span, header.wasted)
        };
        if span < HEADER_SIZE + 1 || wasted >= span {
            return false;
        }
        let block_start = match header_addr.checked_sub(wasted) {
            Some(start) if start >= self.start => start,
            _ => return false,
        };
        let block_end = match block_start.checked_add(span) {
            Some(end) if end <= self.end => end,
            _ => return false,
        };
        // Insertion point: first free block at or after this one.
        // Free blocks sit at their block starts, so comparison is
        // against block_start, not the header address.
        let mut prev: *mut BlockHeader = core::ptr::null_mut();
        let mut cur = self.free_list;
        while !cur.is_null() && (cur as usize) < block_start {
            prev = cur;
            cur = unsafe { (*cur).next };
        }
        if !cur.is_null() && (cur as usize) == block_start {
            return false; // already free: double free refused
        }
        // Relocate the header to the block's true start. When
        // wasted == 0 this rewrites the header in place.
        let header = block_start as *mut BlockHeader;
        unsafe {
            (*header).span = span;
            (*header).wasted = 0;
            (*header).next = cur;
        }
        if prev.is_null() {
            self.free_list = header;
        } else {
            unsafe {
                (*prev).next = header;
            }
        }
        // Coalesce with the next block, if adjacent.
        if !cur.is_null() && block_end == (cur as usize) {
            let (next_span, next_next) = unsafe { ((*cur).span, (*cur).next) };
            unsafe {
                (*header).span = span + next_span;
                (*header).next = next_next;
            }
        }
        // Coalesce with the previous block, if adjacent.
        if !prev.is_null() {
            let prev_addr = prev as usize;
            let prev_span = unsafe { (*prev).span };
            if prev_addr + prev_span == block_start {
                let header_span = unsafe { (*header).span };
                unsafe {
                    (*prev).span = prev_span + header_span;
                    (*prev).next = (*header).next;
                }
            }
        }
        true
    }
}
