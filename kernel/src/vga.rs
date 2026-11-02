//! Meta OS kernel, K2: VGA text-mode console (OS-014..OS-027).
//!
//! Path: bootloader 0.9.35 hands over NO pixel framebuffer (see
//! `os-build/research/framebuffer.md`), so this console drives the
//! VGA text buffer at physical 0xB8000 through the bootloader's full
//! physical-memory mapping (`physical_memory_offset + 0xB8000`).
//! 80x25 cells, hardware ROM font, 16 text colors. No `alloc`, `core` only.

/// VGA text buffer address in physical memory.
pub const VGA_PHYS_ADDR: u64 = 0xB8000;
/// Text columns and rows in standard VGA mode 3.
pub const VGA_WIDTH: usize = 80;
/// Text rows in standard VGA mode 3.
pub const VGA_HEIGHT: usize = 25;

/// VGA color codes (attribute nibble). Unused variants are the palette
/// for later sections (panic screen, shell) — kept deliberately.
#[allow(dead_code)]
#[derive(Clone, Copy)]
#[repr(u8)]
pub enum Color {
    Black = 0x0,
    Blue = 0x1,
    Green = 0x2,
    Cyan = 0x3,
    Red = 0x4,
    Magenta = 0x5,
    Brown = 0x6,
    LightGray = 0x7,
    DarkGray = 0x8,
    LightBlue = 0x9,
    LightGreen = 0xA,
    LightCyan = 0xB,
    LightRed = 0xC,
    Pink = 0xD,
    Yellow = 0xE,
    White = 0xF,
}

/// Foreground/background pair packed into one VGA attribute byte.
#[derive(Clone, Copy)]
pub struct ColorSpec(pub Color, pub Color);

impl ColorSpec {
    fn attr(self) -> u8 {
        ((self.1 as u8) << 4) | (self.0 as u8)
    }
}

/// Whole-screen snapshot for the R-9 attract exit: every VGA cell
/// plus the cursor position at snapshot time, so the shell returns
/// exactly as it was.
pub type ScreenSnapshot = ([u16; VGA_WIDTH * VGA_HEIGHT], usize, usize);

/// Text console over the VGA buffer. The buffer pointer is derived
/// once per boot from `physical_memory_offset`; all writes are
/// bounds-checked to 80x25, so a bad offset can corrupt but never
/// overrun the slice arithmetic (see unsafe ledger).
pub struct VgaConsole {
    col: usize,
    row: usize,
    spec: ColorSpec,
    buffer: *mut u16,
}

impl VgaConsole {
    /// Build a console on the given virtual address of the VGA
    /// buffer and clear the screen to `spec`'s background.
    ///
    /// # Safety
    /// `buffer` must point to a writable 80x25 VGA text buffer.
    pub unsafe fn new(buffer: *mut u16, spec: ColorSpec) -> Self {
        let mut console = VgaConsole { col: 0, row: 0, spec, buffer };
        console.clear();
        console
    }

    fn entry(&self, ch: u8) -> u16 {
        (u16::from(self.spec.attr()) << 8) | u16::from(ch)
    }

    /// Fill the screen with spaces in the background color.
    pub fn clear(&mut self) {
        let blank = self.entry(b' ');
        for i in 0..VGA_WIDTH * VGA_HEIGHT {
            // SAFETY: `buffer` is a valid 80x25 VGA buffer by construction.
            unsafe { core::ptr::write_volatile(self.buffer.add(i), blank) };
        }
        self.col = 0;
        self.row = 0;
    }

    /// Change colors; already-drawn cells keep their colors.
    pub fn set_colors(&mut self, spec: ColorSpec) {
        self.spec = spec;
    }

    /// Move the cursor without writing (R-9 attract drawing).
    /// Out-of-range positions clamp to the screen edge.
    pub fn set_pos(&mut self, row: usize, col: usize) {
        self.row = row.min(VGA_HEIGHT - 1);
        self.col = col.min(VGA_WIDTH - 1);
    }

    /// Snapshot the whole screen: every cell plus the cursor, so
    /// an attract exit can redraw the shell exactly as it was (R-9).
    pub fn snapshot(&self) -> ScreenSnapshot {
        let mut cells = [0u16; VGA_WIDTH * VGA_HEIGHT];
        for i in 0..VGA_WIDTH * VGA_HEIGHT {
            // SAFETY: index is inside the 80x25 buffer by construction.
            cells[i] = unsafe { core::ptr::read_volatile(self.buffer.add(i)) };
        }
        (cells, self.col, self.row)
    }

    /// Restore a snapshot taken by `snapshot` (R-9 attract exit).
    pub fn restore(&mut self, snap: ScreenSnapshot) {
        let (cells, col, row) = snap;
        for i in 0..VGA_WIDTH * VGA_HEIGHT {
            // SAFETY: index is inside the 80x25 buffer by construction.
            unsafe { core::ptr::write_volatile(self.buffer.add(i), cells[i]) };
        }
        self.col = col;
        self.row = row;
    }

    fn newline(&mut self) {
        self.col = 0;
        self.row += 1;
        if self.row >= VGA_HEIGHT {
            self.scroll();
            self.row = VGA_HEIGHT - 1;
        }
    }

    fn scroll(&mut self) {
        for row in 1..VGA_HEIGHT {
            for col in 0..VGA_WIDTH {
                let from = row * VGA_WIDTH + col;
                let to = (row - 1) * VGA_WIDTH + col;
                // SAFETY: both indices are inside the 80x25 buffer.
                unsafe {
                    let v = core::ptr::read_volatile(self.buffer.add(from));
                    core::ptr::write_volatile(self.buffer.add(to), v);
                }
            }
        }
        let blank = self.entry(b' ');
        for col in 0..VGA_WIDTH {
            // SAFETY: last row is inside the buffer.
            unsafe {
                core::ptr::write_volatile(
                    self.buffer.add((VGA_HEIGHT - 1) * VGA_WIDTH + col),
                    blank,
                )
            };
        }
    }

    /// Erase the cell left of the cursor (R-2 backspace): move back
    /// one cell and blank it. At column 0, wrap to the previous
    /// row's last cell; at the top-left cell, a no-op. The caller
    /// prints the serial erase sequence separately; this method is
    /// the screen side only.
    pub fn backspace(&mut self) {
        if self.col > 0 {
            self.col -= 1;
        } else if self.row > 0 {
            self.row -= 1;
            self.col = VGA_WIDTH - 1;
        } else {
            return;
        }
        let blank = self.entry(b' ');
        let idx = self.row * VGA_WIDTH + self.col;
        // SAFETY: row < 25 and col < 80 by the logic above.
        unsafe { core::ptr::write_volatile(self.buffer.add(idx), blank) };
    }

    /// Write one byte. `\n` newlines, `\r` returns to column zero,
    /// `\x08` backspaces (R-2), printable Latin-1 bytes draw through
    /// the VGA ROM font, other control bytes are ignored rather than
    /// drawn as noise.
    pub fn write_byte(&mut self, byte: u8) {
        match byte {
            b'\n' => self.newline(),
            b'\r' => self.col = 0,
            0x08 => self.backspace(),
            0x20..=0xFF => {
                let x = self.col;
                let y = self.row;
                // SAFETY: x < 80 and y < 25 by the scroll/newline logic.
                unsafe {
                    core::ptr::write_volatile(
                        self.buffer.add(y * VGA_WIDTH + x),
                        self.entry(byte),
                    )
                };
                self.col += 1;
                if self.col >= VGA_WIDTH {
                    self.newline();
                }
            }
            _ => {}
        }
    }

    /// Write a string, byte by byte. Non-ASCII UTF-8 bytes render as
    /// their Latin-1 VGA glyphs; this is a byte console, stated, not hidden.
    pub fn write_str(&mut self, s: &str) {
        for byte in s.bytes() {
            self.write_byte(byte);
        }
    }
}

impl core::fmt::Write for VgaConsole {
    fn write_str(&mut self, s: &str) -> core::fmt::Result {
        VgaConsole::write_str(self, s);
        Ok(())
    }
}
