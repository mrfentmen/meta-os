#!/usr/bin/env python3
"""The two userspace build pipelines must agree, or one of them is lying.

There are now two ways to link a userspace program at its base:

  os-build/userspace/build.sh            every bin, bases from bases.txt,
                                         RUSTFLAGS -T link.ld --defsym=__base
  os-build/userspace/build_userspace.py  the four BINS, bases hardcoded in
                                         a PROGRAMS table, generated link-<bin>.ld

Both feed the same `kernel/build.rs` staging step. A change to one and not
the other produces a tree where `build.sh` proves 36 disjoint images while the
kernel actually embeds four images linked by the other script -- or worse, the
same program at two different addresses depending on which script ran last.

This gate compares them at the source level, where the disagreement would
start: names, bases, linker template and the flags that apply it. It does not
rebuild both and diff bytes (they share one target directory, so the second
run overwrites the first); each script already verifies its own ELF headers.

Exit 0 only when every shared assumption matches.
"""

import argparse
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = "x86_64-unknown-none"
DEFAULT_BASES = os.path.join(HERE, "bases.txt")
DEFAULT_BUILDER = os.path.join(HERE, "build_userspace.py")
DEFAULT_BUILD_SH = os.path.join(HERE, "build.sh")
DEFAULT_LINK_LD = os.path.join(HERE, "user", "link.ld")
DEFAULT_LINK_BASE = os.path.join(HERE, "user", "link-base.ld")


def load_bases(path):
    bases = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    bases[parts[0]] = int(parts[1], 16)
                except ValueError:
                    pass
    return bases


def load_python_programs(path):
    """Import the builder and read PROGRAMS. Safe: main is guarded."""
    spec = importlib.util.spec_from_file_location("_build_userspace_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.PROGRAMS)


def rustc_has_core():
    """Would the rustc on PATH build for the bare-metal target?

    build_userspace.py invokes plain `cargo`, which resolves `rustc` from PATH.
    On this Mac that is Homebrew's rustc, which ships no `core` for
    x86_64-unknown-none; the pipeline dies with E0463. build.sh pins RUSTC to a
    toolchain that has core, so the two scripts do not actually have the same
    prerequisites. Returns (has_core, detail).
    """
    try:
        libdir = subprocess.check_output(
            ["rustc", "--print", "target-libdir", "--target", TARGET],
            text=True, stderr=subprocess.DEVNULL, timeout=30,
        ).strip()
    except Exception as exc:  # rustc missing, too old, or no such target
        return False, f"rustc probe failed: {exc}"
    if not os.path.isdir(libdir):
        return False, f"target libdir does not exist: {libdir}"
    rlibs = [f for f in os.listdir(libdir) if f.startswith("libcore-") and f.endswith(".rlib")]
    if not rlibs:
        version = subprocess.run(["rustc", "-V"], capture_output=True,
                                 text=True).stdout.strip()
        return False, f"{version or 'rustc'} has no core for {TARGET} at {libdir}"
    return True, libdir


def main(argv=None):
    ap = argparse.ArgumentParser(description="compare the two link-base pipelines")
    ap.add_argument("--require-python-buildable", action="store_true",
                    help="fail when the python pipeline cannot build with PATH rustc")
    ap.add_argument("--bases", default=DEFAULT_BASES)
    ap.add_argument("--builder", default=DEFAULT_BUILDER)
    ap.add_argument("--build-sh", default=DEFAULT_BUILD_SH)
    ap.add_argument("--link-ld", default=DEFAULT_LINK_LD)
    ap.add_argument("--link-base", default=DEFAULT_LINK_BASE)
    args = ap.parse_args(argv)

    problems = []
    for label, path in [
        ("bases.txt", args.bases),
        ("build_userspace.py", args.builder),
        ("build.sh", args.build_sh),
        ("link.ld", args.link_ld),
        ("link-base.ld", args.link_base),
    ]:
        if not os.path.exists(path):
            problems.append(f"{label}: missing at {path}")
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return 1

    bases = load_bases(args.bases)
    programs = load_python_programs(args.builder)
    if not programs:
        problems.append("build_userspace.py: PROGRAMS is empty")
    if len({b for _n, b in programs}) != len(programs):
        problems.append("build_userspace.py: two programs share one base")

    print(f"{'program':<12} {'build.sh':>18} {'build_userspace.py':>20}  agree")
    for name, py_base in programs:
        sh_base = bases.get(name)
        if sh_base is None:
            problems.append(f"{name}: built by build_userspace.py, absent from bases.txt")
            shown = "—"
            agree = "NO"
        else:
            shown = f"0x{sh_base:016x}"
            agree = "yes" if sh_base == py_base else "NO"
            if sh_base != py_base:
                problems.append(
                    f"{name}: build.sh 0x{sh_base:016x} vs python 0x{py_base:016x}"
                )
        print(f"{name:<12} {shown:>18} {f'0x{py_base:016x}':>20}  {agree}")

    # The templates must each carry exactly the substitution their script expects.
    link_text = open(args.link_ld, "r", encoding="utf-8").read()
    if "DEFINED(__base)" not in link_text:
        problems.append("link.ld: no `DEFINED(__base)` fallback; --defsym would be ignored")
    base_text = open(args.link_base, "r", encoding="utf-8").read()
    placements = base_text.count(". = BASE;")
    if placements != 1:
        problems.append(
            f"link-base.ld: expected exactly 1 `. = BASE;` placement, found {placements}"
        )

    sh_text = open(args.build_sh, "r", encoding="utf-8").read()
    for flag in ("link-arg=-T", "link-arg=--defsym=__base="):
        if flag not in sh_text:
            problems.append(f"build.sh: missing `{flag}` (link base not applied)")

    py_text = open(args.builder, "r", encoding="utf-8").read()
    if "_build_userspace_placeholder_" in py_text:  # never true; keeps py_text used
        pass

    # Coverage is a fact, not a failure: the python pipeline is BINS-scoped.
    sh_slots = len(bases)
    print()
    print(f"coverage: build.sh {sh_slots} slots; build_userspace.py {len(programs)} programs")
    buildable, detail = rustc_has_core()
    if buildable:
        print(f"buildable: build_userspace.py finds core at {detail}")
    else:
        print(f"NOTE build_userspace.py is NOT buildable here: {detail}")
        print("     its bases above are compared statically, not from an ELF it produced")
        if args.require_python_buildable:
            problems.append("build_userspace.py is not buildable with the rustc on PATH")
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        print(f"\n{len(problems)} disagreement(s) — the pipelines would stage different bases")
        return 1
    print("agreement: shared bases match, both templates apply their base, no duplicate slots")
    return 0


if __name__ == "__main__":
    sys.exit(main())
