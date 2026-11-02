#!/usr/bin/env python3
"""abi_check.py — hold the userspace ABI spec to the code.

The spec (`os-build/USERSPACE_ABI.md`) claims things about `kernel/src/user.rs`.
This reads both and fails when they drift: a call the spec names that the
dispatch does not serve, a number served that the spec does not name, a refusal
that stopped refusing, or the frozen table in KERNEL_SPEC.md disagreeing with
the dispatch.

It is a text checker, not a compile and not a boot. It proves the documents and
the source agree; only a boot log proves behaviour.

Exit: 0 in agreement, 1 on any drift, 2 on a missing file.
Usage: abi_check.py  (run from the repo root)
"""

import pathlib
import re
import sys

SPEC_CALLS = {0: "exit", 1: "write", 2: "sleep", 3: "pid", 4: "yield", 5: "read_key"}
RESERVED = set(range(6, 16))


def read(path):
    p = pathlib.Path(path)
    if not p.is_file():
        print(f"abi_check: missing {path}", file=sys.stderr)
        sys.exit(2)
    return p.read_text()


def dispatch_block(src):
    """The syscall_handler body: from its definition to `user_write`."""
    start = src.find("pub fn syscall_handler")
    if start < 0:
        return None
    end = src.find("fn user_write", start)
    return src[start:end if end > 0 else len(src)]


def main():
    src = read("kernel/src/user.rs")
    spec = read("KERNEL_SPEC.md")
    abi = read("os-build/USERSPACE_ABI.md")
    block = dispatch_block(src)
    if block is None:
        print("abi_check: syscall_handler not found in user.rs", file=sys.stderr)
        return 1

    failures = []

    served = sorted({int(n) for n in re.findall(r"^\s+(\d+)\s*=>", block, re.M)})
    print(f"abi_check: dispatch serves {served}")
    if set(served) != set(SPEC_CALLS):
        failures.append(f"served set {served} != spec set {sorted(SPEC_CALLS)}")

    for number, name in SPEC_CALLS.items():
        # The spec table must name every call the code serves.
        if not re.search(rf"\|\s*{number}\s*\|\s*{name}\s*\|", abi):
            failures.append(f"spec table missing row for {number} ({name})")

    # The refusal arm must exist, must print, and must return MAX.
    if "user bad syscall" not in block or "refused" not in block:
        failures.append("refusal arm lost its `user bad syscall ... refused` line")
    if "u64::MAX" not in block:
        failures.append("refusal arm no longer returns u64::MAX")

    # read_key must stay a real getter over the keyboard ring.
    if "keyboard_read" not in block:
        failures.append("read_key no longer reads interrupts::keyboard_read")

    # write: cap and mapping check are the two guarantees the spec makes.
    write_start = src.find("unsafe fn user_write")
    write = src[write_start : write_start + 900] if write_start >= 0 else ""
    if "4096" not in write:
        failures.append("user_write lost its 4096-byte cap")
    if "is_mapped_range" not in write:
        failures.append("user_write no longer validates the buffer range")

    # The wrappers are the other half of the ABI: a bin can call a wrapper the
    # library never defined (readkey did, and the crate stayed red until the
    # missing `sys_read_key` was added), or a wrapper can send the wrong number
    # and quietly reach a different call. Both are drift.
    lib = read("os-build/userspace/user/src/lib.rs")
    wrappers = {
        "sys_exit": 0, "sys_write": 1, "sys_sleep": 2,
        "sys_getpid": 3, "sys_yield": 4, "sys_read_key": 5,
    }
    for name, number in wrappers.items():
        match = re.search(rf"pub fn {name}\s*\([^)]*\)[^{{]*\{{(.*?)\n\}}", lib, re.S)
        if not match:
            failures.append(f"lib.rs has no `{name}` wrapper")
        elif f"syscall({number}" not in match.group(1):
            failures.append(f"lib.rs `{name}` does not call syscall({number})")

    # The frozen table in the spec must still match the dispatch.
    if "0 — exit" not in spec or "5 — read_key" not in spec:
        failures.append("KERNEL_SPEC.md no longer lists the 0-5 frozen table")
    if "6–15 — reserved" not in spec and "6-15 — reserved" not in spec:
        failures.append("KERNEL_SPEC.md lost the 6-15 reserved range")
    for number in sorted(RESERVED):
        if re.search(rf"^\s+{number}\s*=>", block, re.M):
            failures.append(f"reserved number {number} is served in the dispatch")

    if failures:
        print("abi_check: DRIFT")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("abi_check: spec, dispatch and lib.rs wrappers agree "
          "(6 calls, refusal arm, write cap, reserved range)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
