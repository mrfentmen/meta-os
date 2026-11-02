# Flock-style deployment: what this build does not have (BF4-23)

Facts only, no pitch. Scope: if Meta OS were deployed the way a fleet product is deployed — many
devices in the field, updates pushed from a server, staged rollout, rollback when a build is bad —
what is missing from this tree today.

"Flock-style" is read here as **fleet deployment of an OS image**: signed releases, staged rollout,
remote health, rollback, and a device identity to address. If the boss means a specific vendor's
model, the gaps below still hold, because every one of them is a gap against the generic pattern,
not against a feature list.

Everything in the "have" column is in this tree and has a test or a command. Everything in the
"missing" column is absent from the tree; a `grep` for it returns nothing.

## The one table

| A fleet deployment needs | This build has | Missing, concretely |
|---|---|---|
| **An image to ship** | Nothing. The kernel is a crate; the services are Goose sources; there is no image, no initramfs, no disk image build step | an image builder and a reproducible artifact |
| **A device identity** | Nothing. No device key, no certificate, no serial identity beyond whatever the firmware reports | a key that survives reflash, and where it lives |
| **A trust root** | Nothing. `updater` verifies **integrity** (SHA-256 per file) and nothing verifies **authenticity** | a signature over the manifest itself, and a key the device already trusts |
| **Signed updates** | `updater` parses a manifest, refuses unknown keys, duplicate paths, short digests and `..` in paths (`services/updater/README.md`), then verifies each file's digest | no signature field, no signer identity, no revocation |
| **A/B slots and rollback** | `updater` has `upd_plan(m, active_slot)` with slots `a`/`b`, and a rollback record (`upd_record_*`) encoded into 512 bytes and persisted through storage | no bootloader support for selecting a slot: nothing at boot reads that record |
| **A transport** | Nothing. `sys_net_send`/`sys_net_recv` are refused by the host shim and no driver exists | TCP/QUIC/TLS on the device, retry, resumption, bandwidth control |
| **Remote health** | `logd` formats and rotates records; `watchdog` has its state machine; the audit service records events | no exporter, no uploader, no consent model for what leaves a device |
| **Staged rollout control** | Nothing. A manifest names one version and one slot; there is no cohort, ring, pause or percentage | a fleet-side controller and a device-side policy to obey it |
| **Key rotation / revocation** | Nothing | any PKI at all |
| **Fleet inventory** | Nothing | a registry of which device runs which build |
| **Provisioning at scale** | Nothing | first-boot enrolment, factory keys, recovery images |

## What the code actually proves, so the gap list is not oversold

- **Digest verification runs.** `tests/t58_updater` (35 checks) verifies per-file SHA-256 against the
  manifest and refuses a mismatch. Integrity checking is real code, tested natively.
- **The apply plan is a real decision.** `upd_plan` refuses a manifest aimed at the **running** slot
  (`E_STATE`), which is the A/B invariant that matters: never overwrite the system you are running.
  `upd_record_confirm`/`upd_record_safe_slot` decide what happens after a boot that did not confirm.
- **The rollback record survives.** It is encoded to a 512-byte block and pushed through the storage
  contract, so it survives a remount within a process — not a reboot (storage is RAM).
- **Logs are structured enough to ship.** `copy`/`format` in `logd` emit fixed fields; `rotate`
  names segments by service and day, so an uploader would not have to parse prose.

## What that means in one paragraph

This layer has the **inside** half of an update system — verify, plan, record — and none of the
**outside** half: no identity, no signature, no transport, no fleet, no bootloader cooperation. That
is a coherent place for a services tier to stop, because the outside half is a platform and
security decision (who signs, what the device trusts, what leaves the device), and the KERNEL_SPEC
does not rule on any of it yet. The honest sentence for a demo is: "the updater decides correctly
whether an update is intact; nothing yet proves who sent it or gets it there."

## The three cheapest steps toward a real deployment

In dependency order, smallest first — none of them is new feature work for the services lane:

1. **Add a signature field to the manifest and refuse an unknown one.** The parser already refuses
   unknown keys precisely so a v2 cannot add a signature that v1 silently ignores
   (`services/updater/README.md`). The code path is designed for this; there is no key material.
2. **Have the bootloader read the safe-slot record.** The record exists and is persisted; nothing at
   boot consumes it, so today rollback is a decision with no actor.
3. **One transport, one endpoint, one uploader.** Until `sys_net_send` exists on the kernel side,
   every fleet feature is a document.

## What this note deliberately does not say

- It does not recommend a vendor, a protocol or a PKI product. That is a ruling, not a research
  finding.
- It does not estimate effort. The only measured number in it is the size of the pieces that exist:
  the updater is one file with 35 passing checks, and the rollback record is 512 bytes.
- It does not claim a fleet has been tested. No device has ever run this OS.
