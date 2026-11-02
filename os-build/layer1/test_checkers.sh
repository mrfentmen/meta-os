#!/usr/bin/env bash
# os-build/layer1/test_checkers.sh — prove the checkers fail when they should.
#
# A checker that has only ever printed PASS is unverified. This copies the files
# each checker reads into a temp tree, introduces one drift of each kind, and
# requires the checker to exit non-zero — then restores the file and requires it
# to pass again. Nothing in the repo is modified: the mutations live in $TMP.
#
# Exit: 0 every drift was caught, 1 one slipped through, 2 setup failed.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
ROOT="$(pwd)"
TMP="$(mktemp -d)" || exit 2
trap 'rm -rf "$TMP"' EXIT

copy_tree() {
    mkdir -p "$TMP/kernel/src" "$TMP/os-build/layer1" \
             "$TMP/os-build/userspace/user/src"
    cp "$ROOT/kernel/src/user.rs" "$TMP/kernel/src/user.rs" || exit 2
    cp "$ROOT/KERNEL_SPEC.md" "$TMP/KERNEL_SPEC.md" || exit 2
    cp "$ROOT/os-build/USERSPACE_ABI.md" "$TMP/os-build/USERSPACE_ABI.md" || exit 2
    cp "$ROOT/os-build/layer1/BOOT_ORDER.md" "$TMP/os-build/layer1/BOOT_ORDER.md" || exit 2
    cp "$ROOT/os-build/BOOT_MANIFEST.md" "$TMP/os-build/BOOT_MANIFEST.md" || exit 2
    cp "$ROOT/os-build/boot-manifest.json" "$TMP/os-build/boot-manifest.json" || exit 2
    cp "$ROOT/os-build/userspace/user/src/lib.rs" \
       "$TMP/os-build/userspace/user/src/lib.rs" || exit 2
}

run_abi() { ( cd "$TMP" && python3 "$ROOT/os-build/layer1/abi_check.py" >/dev/null 2>&1 ); }
run_manifest() { ( cd "$TMP" && python3 "$ROOT/os-build/layer1/boot_manifest_check.py" >/dev/null 2>&1 ); }

FAILED=0
expect() { # expect <name> <wanted:pass|fail> <function>
    if "$3"; then got=pass; else got=fail; fi
    if [ "$got" = "$2" ]; then
        echo "  ok    $1 ($got, as expected)"
    else
        echo "  BAD   $1 (got $got, wanted $2)"
        FAILED=1
    fi
}

copy_tree

echo "== abi_check =="
expect "clean tree" pass run_abi
sed -i.bak 's/syscall(5, 0, 0, 0)/syscall(4, 0, 0, 0)/' \
    "$TMP/os-build/userspace/user/src/lib.rs"
expect "lib.rs wrapper calls the wrong number" fail run_abi
cp "$ROOT/os-build/userspace/user/src/lib.rs" "$TMP/os-build/userspace/user/src/lib.rs"

sed -i.bak 's/user bad syscall/user bad call/' "$TMP/kernel/src/user.rs"
expect "refusal line renamed" fail run_abi
cp "$ROOT/kernel/src/user.rs" "$TMP/kernel/src/user.rs"

echo "== boot_manifest_check =="
expect "clean tree" pass run_manifest
sed -i.bak 's/| 7 | console | bootlog | no | \*\*yes\*\* |/| 7 | console | bootlog | no | no |/' \
    "$TMP/os-build/BOOT_MANIFEST.md"
expect "console marked degradable" fail run_manifest
cp "$ROOT/os-build/BOOT_MANIFEST.md" "$TMP/os-build/BOOT_MANIFEST.md"

python3 - "$TMP/os-build/boot-manifest.json" <<'PY'
import json, sys
path = sys.argv[1]
doc = json.load(open(path))
for entry in doc["services"]:
    if entry["id"] == "storage":
        entry["fatal_in_effect"] = False
json.dump(doc, open(path, "w"), indent=2)
PY
expect "json claims storage is not fatal" fail run_manifest
cp "$ROOT/os-build/boot-manifest.json" "$TMP/os-build/boot-manifest.json"

echo
if [ "$FAILED" -eq 0 ]; then
    echo "test_checkers: PASS (every drift was caught)"
else
    echo "test_checkers: FAIL (a checker did not catch its drift)"
fi
exit "$FAILED"
