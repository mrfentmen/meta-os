//! KF-10 desktop icons: hand-drawn 16x16 pixel bitmaps for the
//! kernel-drawn desktop's dock (framebuffer.rs `draw_shell_desktop`
//! paints the desktop and the shell window; main.rs calls
//! `draw_dock` below to add the dock).
//!
//! Why bitmaps in code: the bare-metal kernel has no image loader —
//! no PNG/SVG decoder exists in kernel/src, and the repo's existing
//! icon assets (Papirus SVGs under metaos-theme/ and iso/theme/) are
//! for the Linux carrier's theme, not for a kernel framebuffer. So
//! the icons are data the kernel paints itself, one scaled pixel
//! block at a time, through the same `Framebuffer::write_pixel` path
//! as everything else on this desktop. Palette and rendering live in
//! framebuffer.rs (`draw_bitmap`); this file is the icon set and the
//! dock layout only.
//!
//! The set is the desktop's app list (Del's dock list): Terminal,
//! Files, Dashboard, Code Editor, Notes, Calendar, Calculator,
//! Settings, Trash, and Imperium. Icons are decorative at this
//! milestone — there is no mouse or click handling in the kernel
//! yet (that is KF-12/KF-13 territory), and no claim is made that
//! clicking one does anything.
//!
//! Status: this file compiles standalone with framebuffer.rs
//! (rustc 1.99.1, core-only lib check, Pax, this VM). The full
//! kernel build and a QEMU screendump showing the dock remain the
//! Mac-side proof, owed together with the KF-10 window proof.

use crate::framebuffer::FramebufferConsole;

/// One dock icon: a short label and a 16x16 bitmap, one string per
/// pixel row, one character per pixel (palette in framebuffer.rs;
/// `.` is transparent and leaves whatever is underneath).
pub struct Icon {
    pub label: &'static str,
    pub rows: [&'static str; 16],
}

pub const ICONS: &[Icon] = &[
    Icon {
        label: "Terminal",
        rows: [
            "................",
            ".BBBBBBBBBBBBBB.",
            ".BKKKKKKKKKKKKB.",
            ".BKKKKKKKKKKKKB.",
            ".BKKWWKKKKKKKKB.",
            ".BKKKWWKKKKKKKB.",
            ".BKKKKWWKKKKKKB.",
            ".BKKKWWKKKKKKKB.",
            ".BKKWWKKKKKKKKB.",
            ".BKKKKKKKKKKKKB.",
            ".BKKKKNNNNKKKKB.",
            ".BKKKKKKKKKKKKB.",
            ".BKKKKKKKKKKKKB.",
            ".BKKKKKKKKKKKKB.",
            ".BBBBBBBBBBBBBB.",
            "................",
        ],
    },
    Icon {
        label: "Files",
        rows: [
            "................",
            "................",
            "..bbbb..........",
            "..bbbbbb........",
            "..bbbbbbbbbbbbb.",
            "..bBBBBBBBBBBBb.",
            "..BLLLLLLLLLLB..",
            "..BBBBBBBBBBBB..",
            "..BBBBBBBBBBBB..",
            "..BBBBBBBBBBBB..",
            "..BBBBBBBBBBBB..",
            "..BBBBBBBBBBBB..",
            "..BBBBBBBBBBBB..",
            "..BBBBBBBBBBBB..",
            "................",
            "................",
        ],
    },
    Icon {
        label: "Dash",
        rows: [
            "................",
            ".KKKKKKKKKKKKKK.",
            ".KWWWWWWWWWWWWK.",
            ".KWWWWWWWWWWWWK.",
            ".KWWWWWWWWWWRRK.",
            ".KWWWWWWWWWWRRK.",
            ".KWWWWNNWWWWRRK.",
            ".KWWWWNNWWWWRRK.",
            ".KWWWWNNWYYWRRK.",
            ".KWBBWNNWYYWRRK.",
            ".KWBBWNNWYYWRRK.",
            ".KWBBWNNWYYWRRK.",
            ".KDBBDNNDYYDRRK.",
            ".KKKKKKKKKKKKKK.",
            "................",
            "................",
        ],
    },
    Icon {
        label: "Code",
        rows: [
            "................",
            ".DDDDDDDDDDDDDD.",
            ".DKKKKKKKKKKKKD.",
            ".DKKKKKKKKKKKKD.",
            ".DKKKKKKKKKKKKD.",
            ".DKKWWKKLLWWKKD.",
            ".DKWWKKLLKKWWKD.",
            ".DWWKKLLKKKKWWD.",
            ".DKWWKKKKKKWWKD.",
            ".DKKWWKKKKWWKKD.",
            ".DKKKKKKKKKKKKD.",
            ".DKKKKKKKKKKKKD.",
            ".DKKKKKKKKKKKKD.",
            ".DDDDDDDDDDDDDD.",
            "................",
            "................",
        ],
    },
    Icon {
        label: "Notes",
        rows: [
            "................",
            "..KKKKKKKKKKKK..",
            "..KWWWWWWWWWGK..",
            "..KWWWWWWWGGK...",
            "..KWWWWWWWWWWK..",
            "..KWBBBBBBBWWK..",
            "..KWBBBBBBBWWK..",
            "..KWBBBBBBBWWK..",
            "..KWBBBBBBBWWK..",
            "..KWBBBBWWWWWK..",
            "..KWWWWWWWWWWK..",
            "..KWBBBBBBBWWK..",
            "..KWBBBBBBBWWK..",
            "..KWWWWWWWWWWK..",
            "..KKKKKKKKKKKK..",
            "................",
        ],
    },
    Icon {
        label: "Calendar",
        rows: [
            "................",
            "..KKKKKKKKKKKK..",
            "..KRRRRRRRRRRK..",
            "..KRRRRRRRRRRK..",
            "..KWWWWWWWWWWK..",
            "..KWWWWWWWWWWK..",
            "..KWDWWDWWDWWK..",
            "..KWWWWWWWWWWK..",
            "..KWDWWBWWDRWK..",
            "..KWWWWWWWWWWK..",
            "..KWDWWDWWDWWK..",
            "..KWWWWWWWWWWK..",
            "..KWDWWDWWDWWK..",
            "..KWWWWWWWWWWK..",
            "..KKKKKKKKKKKK..",
            "................",
        ],
    },
    Icon {
        label: "Calc",
        rows: [
            "................",
            "..DDDDDDDDDDDD..",
            "..DGGGGGGGGGGD..",
            "..DGNNNNNNNNGD..",
            "..DGGGGGGGGGGD..",
            "..DGWWGWWGWWD...",
            "..DGWWGWWGWWD...",
            "..DGGGGGGGGGGD..",
            "..DGWWGWWGWWD...",
            "..DGWWGWWGWWD...",
            "..DGGGGGGGGGGD..",
            "..DGWWGWWGOOD...",
            "..DGGGGGGGGGGD..",
            "..DGGGGGGGGGGD..",
            "..DDDDDDDDDDDD..",
            "................",
        ],
    },
    Icon {
        label: "Settings",
        rows: [
            "................",
            ".......BB.......",
            ".......BB.......",
            "..B....BB....B..",
            "..BB..BBBB..BB..",
            "...BBBBBBBBBB...",
            ".B.BBBBBBBBBB.B.",
            ".B.BBBKKKKBBB.B.",
            "...BBKWWWWKBB...",
            "...BBKWWWWKBB...",
            ".B.BBBKKKKBBB.B.",
            ".B.BBBBBBBBBB.B.",
            "...BBBBBBBBBB...",
            "..BB..BBBB..BB..",
            "..B....BB....B..",
            ".......BB.......",
        ],
    },
    Icon {
        label: "Trash",
        rows: [
            "................",
            "................",
            "......KKKK......",
            "...DDDDDDDDDD...",
            "....DDDDDDDD....",
            "....DGDGGDGD....",
            "....DGDGGDGD....",
            "....DGDGGDGD....",
            "....DGDGGDGD....",
            "....DGDGGDGD....",
            "....DGDGGDGD....",
            ".....DGDGGD.....",
            ".....DDDDDD.....",
            "................",
            "................",
            "................",
        ],
    },
    Icon {
        label: "Imperium",
        rows: [
            "................",
            "...BBBBBBBBBB...",
            "..BBBBBBBBBBBB..",
            "..BBLLLLLLLLBB..",
            "..BLLLLLLLLLLB..",
            "..BLLLWWWWLLLB..",
            "..BLLWWWWWWLLB..",
            "..BLLLWWWWLLLB..",
            "...BLLWWWWLLB...",
            "....BLLWWLLB....",
            ".....BLWWLB.....",
            "......BWWB......",
            ".......BB.......",
            "................",
            "................",
            "................",
        ],
    },
];

/// Dock bar background (matches the desktop's light face) and the
/// label ink drawn on it.
const DOCK_BG: (u8, u8, u8) = (232, 238, 246);
const DOCK_EDGE: (u8, u8, u8) = (120, 135, 155);
const INK: (u8, u8, u8) = (20, 20, 20);

/// Paint the dock along the bottom of the desktop: a light bar, the
/// ten icons at 2x scale (32x32 px), and a label under each. Uses
/// only the console's pixel methods, so the shell window's view
/// region and cursor are untouched. On a screen too narrow for the
/// full row, nothing is painted rather than a clipped dock.
pub fn draw_dock(console: &mut FramebufferConsole) {
    let (sw, sh) = console.screen_size();
    const SLOT: usize = 72;
    let total = SLOT * ICONS.len();
    if sw < total + 32 || sh < 160 {
        return;
    }
    let start_x = (sw - total) / 2;
    let bar_y = sh - 80;
    console.fill_rect_px(start_x - 14, bar_y, total + 28, 76, DOCK_BG);
    console.fill_rect_px(start_x - 14, bar_y, total + 28, 2, DOCK_EDGE);
    for (i, icon) in ICONS.iter().enumerate() {
        let cx = start_x + i * SLOT + SLOT / 2;
        console.draw_bitmap_px(cx - 16, bar_y + 6, 2, &icon.rows);
        let label_w = icon.label.len() * 8;
        console.draw_text_px(cx - label_w / 2, bar_y + 46, icon.label, INK, DOCK_BG);
    }
}
