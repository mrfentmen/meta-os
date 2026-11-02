# OC2B-415 image magic-byte checks (OC2B-413/414)

Both files verified with `models.detect_image_format` (magic bytes,
not extensions):

- `lab-scene-GENERATED.webp`: 303,184 bytes, magic `RIFF....WEBP` →
  `webp`. Extension matches. (Muse Image, 11,870 ms.)
- `workshop-scene-GENERATED.webp`: 360,310 bytes, magic
  `RIFF....WEBP` → `webp`. Extension matches. (Muse Image, 12,347 ms.)

Both filenames carry GENERATED; both are concept renders, never
measurements. Receipts: scratch file `receipts-image.jsonl` (copied
into `OC2B-model-receipts-index.md`).
