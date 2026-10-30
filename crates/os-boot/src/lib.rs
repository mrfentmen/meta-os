//! Crate `os-boot` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B23 — Boot glue & deployment. Owner: Milo.
//! Source files this batch ports:
//! - `os/mos.py`
//! - `os/mos/__init__.py`
//! - `os/mos/cli.py`
//! - `os/os/BASE.md`
//! - `os/os/README-FIRSTBOOT.md`
//! - `os/os/README.md`
//! - `os/os/bin/metaos-boot-checklist`
//! - `os/os/bin/metaos-secrets-sweep`
//! - `os/os/bin/metaos-update`
//! - `os/os/build-all.sh`
//! - `os/os/build-image.sh`
//! - `os/os/build-live.sh`
//! - `os/os/build-packer.sh`
//! - `os/os/firstboot/metaos-firstboot`
//! - `os/os/grub-early.cfg`
//! - `os/os/live-build/auto/config`
//! - `os/os/live-build/config/hooks/live/0900-metaos-services.hook.chroot`
//! - `os/os/live-build/config/package-lists/metaos.list.chroot`
//! - `os/os/packages.txt`
//! - `os/os/packer/metaos.pkr.hcl`
//! - `os/os/preseed.cfg`
//! - `os/os/services/metaos-firstboot.service`
//! - `os/os/services/relay-brief.service`
//! - `os/os/services/relay-bus.service`
//! - `os/os/services/relay-dashboard.service`
//! - `os/os/services/relay-driver@.service`
//! - `os/os/services/relay-drivers.slice`
//! - `os/os/services/relay-jobs.service`
//! - `os/os/services/relay-mcp-gateway.service`
//! - `os/os/services/relay-memory.service`
//! - `os/os/services/relay-overseer.service`
//! - `os/os/services/relay-overseer.timer`
//! - `os/os/services/relay-ready.service`
//! - `os/os/services/relay-uplink.service`
//! - `os/os/services/relay-watchdog.service`
//! - `os/os/services/relay-watchdog.service.d/demo-thresholds.conf`
//! - `os/os/services/relay-watchman-watch.service`
//! - `os/os/services/relay-watchman.service`
//! - `os/os/services/relay-worker@.service`
//! - `os/os/services/relay-workers.slice`
//! - `os/os/services/relay.target`
//! - `os/os/test-boot.sh`
//! - `os/tests/test_mos_acceptance.py`
//! - `os/tests/test_mos_capabilities.py`
//! - `os/tests/test_mos_flow.py`
//! - `os/tests/test_mos_gitops.py`
//!
//! Ported in batch B23 (Milo): the `os/mos/cli.py` command surface
//! (see the `cli` module), a real git backend for the review/merge
//! commands (see the `git` module), and the 39 `os/os/` deployment
//! assets carried byte-identical under `assets/os/` (see the `carried`
//! module and its manifest).

pub mod carried;
pub mod cli;
pub mod git;

