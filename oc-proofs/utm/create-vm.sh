#!/bin/sh
# NC-086: create-and-configure the Meta OS UTM VM from VM_SPEC.md.
# Builds the VM but DOES NOT START it. Idempotent: refuses if the VM
# already exists. Tested with `sh -n` (dry-parse) only — no image file
# exists on this Mac, so creation itself is untested by design.
set -eu
IMG="${1:?usage: $0 <path-to-metaos-img> [vm-name]}"
NAME="${2:-metaos-20261101}"
[ -f "$IMG" ] || { echo "no image file: $IMG"; exit 2; }
if utmctl list 2>/dev/null | grep -q "$NAME"; then
  echo "VM $NAME already exists; refusing (delete it first)"
  exit 3
fi
echo "WOULD create VM $NAME:"
echo "  arch=x86_64 cpu=max(memory-model, NOT qemu64) ram=4096 vcpus=2"
echo "  disk=$IMG (copy to working copy first; golden stays read-only)"
echo "  serial console enabled, serial log on, shared network"
echo "NOTE: scripted creation beyond this point needs a UTM release whose"
echo "utmctl supports full VM authoring; as of UTM 5.0.8 the reliable path"
echo "is the GUI Import flow with the settings in VM_SPEC.md. This script"
echo "deliberately stops before inventing utmctl flags that may not exist."
