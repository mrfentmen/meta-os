# OC3B-006 — no Apple-adjacent assets on the start page
- Method: case-insensitive scan of OC3B-startpage.html for apple, macos,
  iphone, cupertino, San Francisco font references, plus a manual review
  of every glyph used in the ASCII mark (dots only — no logo shapes, no
  brand letterforms).
- Result: 0 hits. Palette is tokens.json (blue/pink/violet/cyan on
  near-black), type is DejaVu/Verdana/system-ui. No images at all.
- Milo original-asset self-check remains the merge gate; this file is
  the author-side evidence, not the verdict.
