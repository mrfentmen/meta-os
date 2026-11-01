# Image intake + rollback (NC-092, NC-094)

## Intake (on arrival, before any boot)

1. Copy the .img to this Mac (golden base, e.g. ~/metaos-images/).
2. Verify sha256 against the build record:
   `c22df0ae1351e684864ba1c52a6dd2745d307bea0df4aae2323b4d063a7c91c5`
   (`shasum -a 256 metaos-2026-11-01.img` must print exactly that).
   Mismatch = stop, tell the builder, boot nothing.
3. `chmod 444` the golden base (read-only from here on).
4. `cp` to a working copy for UTM; only the copy is ever attached.

## Rollback (if a boot corrupts the working copy)

1. Delete the VM (utmctl or GUI remove, including its working disk).
2. Re-copy from the golden base (never "repair" the working copy).
3. Re-run intake step 2 on the golden base (paranoia is free).
4. Recreate from create-vm.sh. Total cost: one copy.

## Disk headroom (NC-091)

This Mac: 736 GiB free. Image (~6 GiB) + working copy (~6 GiB) + logs
needs about 13 GiB. Headroom: ~723 GiB. Not a constraint.
