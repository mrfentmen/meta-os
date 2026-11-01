# Glyph table license note (Pax, merge of Rowan R2 2026-11-01)

`kernel/src/framebuffer.rs` embeds a 256-glyph 8x16 table copied verbatim
from `Lat2-Terminus16.psf.gz` (Terminus Font, PSF1, 256 glyphs x 16 bytes),
as the file itself states. This note closes the license item Milo left
open at the Pax merge gate for R2.

- Upstream: Terminus Font, copyright Dimitar Toshkov Zhekov, dual
  licensed GNU GPLv2 and SIL Open Font License 1.1 (SourceForge
  terminus-font listing; OFL 1.1 text at scripts.sil.org/OFL).
- The embedded table is distributed under OFL 1.1: it is not sold by
  itself, it ships only as part of this software, this note plus the
  file's own attribution carry the copyright notice and license, and
  the derived table does not use the Reserved Font Name "Terminus
  Font" as its own name (it is the internal `FONT_8X16` array).
- If the boss prefers a different license treatment, the table is one
  isolated array and can be swapped without touching the console logic.
