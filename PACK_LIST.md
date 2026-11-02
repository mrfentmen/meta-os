# PACK LIST — pack prerequisites, don't rebuild them (boss 02:28)

The boss's rule: boot, log in, run programs with everything
there. Most of the code already exists — find it, pack it, theme
it. We build the face and the systems; we do NOT build a browser,
a file manager, or a terminal from scratch.

## Pack into the carrier image (existing apps, themed)
- Browser: Chrome where the Mac build allows, else Chromium —
  either way a real browser, our start page = the face home.
- Terminal: the distro's real terminal (GNOME Terminal / xfce4).
- Files: the distro's real file manager (Nautilus / Thunar).
- Code Editor: VS Code OSS build or gedit-class editor — pick
  by image weight, record the pick.
- Notes, Calendar, Calculator: the distro's existing apps,
  themed to the face tokens (Hana's C-section).
- Media: image viewer + video player from the distro.
- Settings plumbing: the distro's network/sound/display panels
  reachable from our Settings window, skinned or framed.
- Drivers/firmware: the distro's wifi + graphics firmware set,
  so the image has a real chance on real hardware later.

## Rules for packed code
1. Open-source or freely distributable only; every packed item
   is named in `THIRD_PARTY.md` with its source and licence —
   the hackathon rules require external work be credited as a
   library, and the credit file is how we prove it.
2. Theme and configure; do not fork-and-claim. Our code is the
   face, the shell glue, and the systems.
3. Same rule inside the kernel face: Rowan starts the graphics
   spike from existing crates (bootloader framebuffer support,
   font crates, PS/2 handling) — study them, adapt them, credit
   them in THIRD_PARTY.md. From-zero only where nothing exists.
4. Every packed app gets a launch proof in the face STATUS.md
   table (OpenCode face list, task 37) — packed and proven, or
   listed as not-yet.

Owner: OpenCode (image lane), Hana (theming tokens), Pax
(THIRD_PARTY.md upkeep on each merge).
