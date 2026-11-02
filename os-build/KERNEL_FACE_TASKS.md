# KERNEL FACE — the OS boots into Meta OS (boss order 02:27 EST)

The boss's ruling, verbatim in effect: **nothing is off limits.**
The kill list is lifted. The target is one machine: our kernel
boots, and Meta OS appears — the face, on our own OS, demo grade.
Not fully built out. Good enough to demo, honest about what the
windows are. Rowan writes, OpenCode proves on the Mac, Milo
gates, Pax merges. The text boot stays — the face comes AFTER the
alive line, so every proven claim stays true on the same boot.

## A. Graphics path (spike first, evidence decides, ~1 hour)
A1. Route 1: upgrade the bootloader crate to a version whose
    BootInfo carries a framebuffer. Build, boot, record what
    breaks (Cargo.lock pin moves — flag it, do not hide it).
A2. Route 2: UEFI GOP taken directly at boot (no bootloader
    change). Prototype far enough to draw one pixel.
A3. Pick by evidence: which route draws a filled rectangle
    sooner with less breakage. Decision + numbers in
    os-build/face/KERNEL_FACE.md.
A4. Framebuffer driver in kernel/: resolution, pitch, pixel
    format from the boot info; fill_rect + put_pixel proven by
    a QEMU screendump (red screen test, then blue).

## B. Drawing layer
B1. Bitmap font rendering (the console's font, drawn to pixels).
B2. Text: string at x,y with colour; the boot lines re-rendered
    in graphics as the first screen.
B3. Primitives: rect, outline, line. Ribbon needs lines.
B4. Double-buffer or dirty-rectangle redraw — pick what keeps
    the ribbon smooth; measure redraw cost in the log.

## C. The ribbon, live on our kernel
C1. Port the ribbon math from js/logo-background.js (same sine
    family, same blue) into kernel drawing code.
C2. Animate it as a kernel task; frame counter in a corner
    during development, removed for the demo build.
C3. Screendump pair: ribbon at two phases (proof it moves).
C4. Pause on keypress like the console attract does today;
    the R-9 attract logic carries over, graphics edition.

## D. Mouse
D1. PS/2 mouse init; packets parsed; cursor drawn, moves.
D2. Click events with x,y delivered to the compositor.
D3. Screendump: cursor at two positions. Log: packet counts.

## E. Compositor and windows
E1. Desktop = ribbon background + top bar + dock, drawn.
E2. Top bar: ribbon mark (small ribbon), name, clock (uptime-
    derived), per Hana's C5 spec. Bar colour: black default;
    white and blue from settings state.
E3. Window: title bar, close box, drag by title, focus raise.
E4. Two windows overlapping, focus switches by click; proof
    screendumps at each step.
E5. Dock: icon cells drawn (simple glyph icons in the approved
    style), hover/click raises or opens its window.
E6. Light mode: bar white, letters black; dark: bar black,
    letters white. Both screendumped.

## F. The windows are real (demo-grade, honestly scoped)
F1. Terminal window: the REAL shell — the console task's I/O
    routed into the window. help/status/mem/ps/uptime answered
    inside the window, screendumped.
F2. Dashboard window: real kernel state as cards — frames free,
    heap, task count, uptime — refreshed live.
F3. Imperium window: the staged run's record — incident, picture
    refs, receipt id from the committed R5-4 artifacts, labelled
    SIMULATED at the top. It shows the record; it does not fake
    a live camera.
F4. Settings window: mode (light/dark), bar colour, background
    colour, animation pause — each changes the desktop for real.
F5. About window: version, banner string, claim sentence.

## G. Boot into the face
G1. Boot flow: text boot (alive, programs, isolation — the
    proven claims) → graphics face as the final state.
G2. Fallback: if graphics init fails, stay on the text console
    and print why. The machine never bricks on the face.
G3. Full-boot screendump set: text phase, first face frame,
    terminal open, dashboard open. To os-build/captures/.
G4. 60-second QEMU recording of the whole boot into the face
    (demo asset; OpenCode captures).
G5. Soak: face up 30 minutes, ribbon animating, console task
    still answering in its window. Log committed.

## H. Hand-off
H1. KERNEL_FACE.md final: what runs, what each window is, what
    is NOT in (no browser, no Linux apps on the bare metal —
    those live on the carrier face; say it plainly).
H2. Gate.sh unchanged for the text claims; a face boot log
    joins it as a second artifact, never a replacement.

Priority: A–C tonight if the Mac lane allows; the DEMO_SCRIPT
interrupt still applies to OpenCode's capture. Pax is dispatch.
