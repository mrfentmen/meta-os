//! Crate `os-misc` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B24 — Bus messaging core. Owner: Buffy.
//! Source files this batch ports:
//! - `os/poll.py`
//! - `os/presence.py`
//! - `os/send.py`
//! - `os/store.py`
//! - `os/watch.py`
//! - `os/watch_nick.py`
//!
//! Batch B25 — Bus messaging extras. Owner: Buffy.
//! Source files this batch ports:
//! - `os/announce.py`
//! - `os/clipboard.py`
//! - `os/edits.py`
//! - `os/forward.py`
//! - `os/paste.py`
//! - `os/saved.py`
//! - `os/tests/test_announce.py`
//! - `os/tests/test_edits.py`
//! - `os/tests/test_forward.py`
//! - `os/tests/test_saved.py`
//!
//! Batch B26 — Bus bridges, digest & admin. Owner: Buffy.
//! Source files this batch ports:
//! - `os/admin.py`
//! - `os/digest.py`
//! - `os/export.py`
//! - `os/health.py`
//! - `os/tests/test_digest.py`
//! - `os/tests/test_export.py`
//! - `os/tests/test_webhook.py`
//! - `os/timecapsule.py`
//! - `os/webhook.py`
//!
//! Batch B27 — World packs. Owner: Buffy.
//! Source files this batch ports:
//! - `os/worlds/README.md`
//! - `os/worlds/dep/PACK.md`
//! - `os/worlds/dep/pack.json`
//! - `os/worlds/doe/PACK.md`
//! - `os/worlds/doe/pack.json`
//! - `os/worlds/dsny/PACK.md`
//! - `os/worlds/dsny/pack.json`
//! - `os/worlds/ems/PACK.md`
//! - `os/worlds/ems/pack.json`
//! - `os/worlds/fdny/PACK.md`
//! - `os/worlds/fdny/pack.json`
//! - `os/worlds/fdny/runtime/par_clock.py`
//! - `os/worlds/hospital/PACK.md`
//! - `os/worlds/hospital/pack.json`
//! - `os/worlds/mta/PACK.md`
//! - `os/worlds/mta/pack.json`
//! - `os/worlds/nypd/PACK.md`
//! - `os/worlds/nypd/pack.json`
//! - `os/worlds/validate_pack.py`
//!
//! Batch B28 — OS docs, roles & root docs. Owner: Buffy.
//! Source files this batch ports:
//! - `os/.gitignore`
//! - `os/INSTANCES.md`
//! - `os/README.md`
//! - `os/ROADMAP.md`
//! - `os/_redirects`
//! - `os/docs/DEPLOY_RUNBOOK.md`
//! - `os/docs/DSH-035-CROSS-BROWSER-CHECK.md`
//! - `os/docs/ROWAN_OS_SCOUT_20261026.md`
//! - `os/docs/briefs-gallery.md`
//! - `os/docs/mos-operations.md`
//! - `os/roles/builder.md`
//! - `os/roles/documenter.md`
//! - `os/roles/overseer.md`
//! - `os/roles/planner.md`
//! - `os/roles/reviewer.md`
//! - `os/roles/tester.md`
//!
//! Batch B29 — Crew dirs & demo/submission assets. Owner: Buffy.
//! Source files this batch ports:
//! - `os/crew/README.md`
//! - `os/crew/buffy/README.md`
//! - `os/crew/hana/README.md`
//! - `os/crew/milo/README.md`
//! - `os/crew/pax/README.md`
//! - `os/crew/rowan/README.md`
//! - `os/demo-assets/audio/LICENSES.md`
//! - `os/demo-assets/audio/TAKE_LOG.md`
//! - `os/demo-assets/audio/TIMING.md`
//! - `os/demo-assets/audio/dem014-final-mix.mp3`
//! - `os/demo-assets/audio/dem015-caption-watchdog-moment.mp3`
//! - `os/demo-assets/audio/dem017-ambient-bed.mp3`
//! - `os/demo-assets/audio/wdg030-watchdog-segment-take1.mp3`
//! - `os/demo-assets/audio/wdg030-watchdog-segment-take2.mp3`
//! - `os/demo-assets/audio/wdg031-opening-framing-take1.mp3`
//! - `os/demo-assets/audio/wdg031-opening-framing-take2.mp3`
//! - `os/demo-assets/audio/wdg033-fallback-full-demo.mp3`
//! - `os/demo-assets/audio/wdg033-fallback-script.txt`
//! - `os/demo-assets/audio/wdg034-alert-sting.mp3`
//! - `os/demo-assets/audio/wdg034-success-sting.mp3`
//! - `os/submission-assets/audio/os039-boot-sting.mp3`
//! - `os/submission-assets/audio/os039-boot-voice-line.mp3`
//!
//! Batch B30 — Lane plans. Owner: Buffy.
//! Source files this batch ports:
//! - `os/plan/DEMO.md`
//! - `os/plan/LAYER_PLAN.md`
//! - `os/plan/MASTER_PLAN.md`
//! - `os/plan/META_OS.md`
//! - `os/plan/META_WORLD.md`
//! - `os/plan/SCHEDULE.md`
//! - `os/plan/lanes/BUFFY.md`
//! - `os/plan/lanes/DALE.md`
//! - `os/plan/lanes/HANA.md`
//! - `os/plan/lanes/MILO.md`
//! - `os/plan/lanes/PAX.md`
//! - `os/plan/lanes/ROWAN.md`
//!
//! Skeleton only: no logic yet. The Python/Node sources listed above are
//! the spec — port behavior, do not redesign. See BATCHES.md for the
//! compile gates and the parity rule.
