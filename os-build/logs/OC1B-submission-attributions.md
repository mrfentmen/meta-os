# OC1B-455 — library attributions (everything in the submission not built in the window)

Compiled 2026-11-02 on tree 94010c76 from repo evidence (Cargo files, code
imports, boot logs). Where each is used is named. Completeness is to the
level this lane could verify statically; Pax extends as needed.

## Boot and kernel
- rust-osdev `bootloader` 0.9.x (kernel/Cargo.toml pins `version = "0.9"`,
  features map_physical_memory) — boots the kernel image; see
  kernel/src/main.rs header. NOT built in the window.
- Rust nightly toolchain + `cargo bootimage` — build-time only.
- QEMU system-x86_64 + SeaBIOS (appear in boot logs) — run/test harness only,
  never shipped as product.

## Models and model transport (used at RUNTIME by the Trio/Imperium path)
- Meta Model API (https://api.meta.ai/v1): muse-spark-1.3 (assessments),
  muse-wonder-1.0 (second reader), sam-3.1 (segment), image model (see
  server/queue/models.py). Service, not code; key via SPARK_API_KEY env only.
- No vendored model weights in the repo.

## Web/app runtime (face/console are design reference + demo capture only)
- Node.js 24 (test runner + server/server.mjs runtime).
- Python 3 (queue, patrol, rehearsals, suites).
- No npm dependencies (package.json: "No dependencies, no build step" —
  frontend is dependency-free; verified in package.json description).
- MapLibre under vendor/maplibre (vendored; check vendor dir for version file
  at submit time — noted, not opened here).

## Native shell
- Apple SDKs (SwiftUI/AppKit/AVKit imports in native/Sources) — build-time
  platform frameworks for the macOS shell (now a WKWebView shell).

## Fonts
- System fonts only in the demo/kernel paths (no webfont downloads in the
  suite path; face assets are Hana's lane — not inventoried here).

## Statement for the form
All of the above are standard toolchains, platform SDKs, open-source boot
components, or the event's own model API; all application logic (kernel,
queue, console, labs, packs) was built in the window and is in this repo.
