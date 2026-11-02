#!/usr/bin/env python3
"""os-build/layer1/gen_services.py -- BF4-11 (manifest) and BF4-07 (syscall map).

Both documents are generated from the corpus, not written by hand, for one
reason: a hand-written map is a claim about code that nobody re-reads. This
walks `services/`, follows imports transitively, finds every `extern fn sys_*`
a service can actually reach, and joins that against the native run table.

Outputs
  os-build/layer1/services.json       machine-readable: name, entry, status,
                                      test, pass count, syscalls, class
  os-build/layer1/SERVICES_SYSCALL_MAP.md  the human table, three classes

Exit status: 0 always; this is a reporting tool, not a gate. A service with no
run row is reported as NOT RUN rather than quietly omitted.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVICES = os.path.join(ROOT, "services")
LAYER1 = os.path.join(ROOT, "os-build", "layer1")
ROWS = os.path.join(LAYER1, "host", "run_rows.txt")

# The F1 freeze, from BUFFY_TASKS_ROUND4.md: (0 exit, 1 write, 2 sleep, 3 pid,
# 4 yield, 5 read_key, 6-15 reserved). Anything a service calls that is not in
# this table needs a proposal before the kernel can be said to support it.
FREEZE = {
    "sys_exit": (0, "end the process"),
    "sys_write_serial": (1, "write to the serial line"),
    "sys_write_console": (1, "write to the console"),
    "sys_yield": (4, "give the CPU back"),
    "sys_read_key": (5, "read one key event"),
}
RESERVED = (6, "reserved, 6-15")

IMPORT = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)\s*;", re.M)
EXTERN = re.compile(r"^\s*extern\s+fn\s+(sys_[a-z_0-9]+)\s*\(", re.M)


def module_files(path):
    """Every .goose file under a service directory, as paths relative to services/."""
    out = []
    for base, _dirs, files in os.walk(path):
        for f in files:
            if f.endswith(".goose") and not f.startswith("."):
                out.append(os.path.relpath(os.path.join(base, f), SERVICES))
    return sorted(out)


def resolve(module):
    """`fs.fsck` -> services/fs/fsck.goose, or None if it is not in the corpus."""
    rel = module.replace(".", os.sep) + ".goose"
    cand = os.path.join(SERVICES, rel)
    return rel if os.path.exists(cand) else None


def closure(start_files):
    """Transitive set of service-relative files reachable from start_files."""
    seen = set()
    stack = list(start_files)
    while stack:
        rel = stack.pop()
        if rel in seen:
            continue
        seen.add(rel)
        full = os.path.join(SERVICES, rel)
        try:
            text = open(full, encoding="utf-8").read()
        except OSError:
            continue
        for mod in IMPORT.findall(text):
            r = resolve(mod)
            if r and r not in seen:
                stack.append(r)
    return seen


def externs(files):
    found = {}
    for rel in sorted(files):
        try:
            text = open(os.path.join(SERVICES, rel), encoding="utf-8").read()
        except OSError:
            continue
        for name in EXTERN.findall(text):
            found.setdefault(name, rel)
    return found


def read_rows():
    rows = {}
    if not os.path.exists(ROWS):
        return rows
    for line in open(ROWS, encoding="utf-8"):
        parts = line.rstrip("\n").split("|")
        if len(parts) >= 4:
            label, status, ok, bad = parts[0], parts[1], parts[2], parts[3]
            note = parts[4] if len(parts) > 4 else ""
            rows[label] = (status, int(ok or 0), int(bad or 0), note)
    return rows


def service_dirs():
    out = []
    for name in sorted(os.listdir(SERVICES)):
        p = os.path.join(SERVICES, name)
        if not os.path.isdir(p) or name in ("tests", "build"):
            continue
        if any(f.endswith(".goose") for f in os.listdir(p)):
            out.append(name)
    return out


def test_for(name, rows):
    """The native run that drives this service, if there is one."""
    best = None
    for label, (status, ok, bad, _note) in rows.items():
        if not label.startswith("tests/"):
            continue
        base = label.split("/", 1)[1]
        stem = re.sub(r"^t\d+_", "", base)
        if stem == name or stem.startswith(name + "_") or name in stem.split("_"):
            if best is None or ok > rows[best][1]:
                best = label
    return best


def classify(names):
    # Three classes, and the middle one is the honest default: a module that makes no
    # kernel call at all is a library, not a service that "runs on the ABI". Saying it
    # runs would overstate a file that never touches the kernel.
    if not names:
        return "library (no kernel calls)"
    outside = [n for n in names if n not in FREEZE]
    return "needs a proposal" if outside else "runs on the proven ABI"


def main():
    rows = read_rows()
    services = []
    for name in service_dirs():
        files = module_files(os.path.join(SERVICES, name))
        reach = closure(files)
        calls = externs(reach)
        # Only `entry.goose` is an entry point: it exports svc_entry. Everything else in
        # a service directory is a module the entry (or another service) imports.
        entry = None
        if os.path.exists(os.path.join(SERVICES, name, "entry.goose")):
            entry = "services/%s/entry.goose" % name
        row = None
        if entry:
            row = rows.get("entry/" + name)
        test = test_for(name, rows)
        tro = rows.get(test) if test else None
        services.append({
            "name": name,
            "path": "services/" + name,
            "entry": entry,
            "entry_status": (row[0] if row else "no entry"),
            "test": test,
            "test_status": (tro[0] if tro else "no native run"),
            "checks": (tro[1] if tro else 0),
            "failures": (tro[2] if tro else 0),
            "syscalls": sorted(calls),
            "reachable_modules": len(reach),
            "class": classify(sorted(calls)),
        })

    manifest = {
        "generated_by": "os-build/layer1/gen_services.py",
        "source_of_truth": "services/**, os-build/layer1/host/run_rows.txt",
        "abi_freeze": {k: v[0] for k, v in FREEZE.items()},
        "reserved": list(range(6, 16)),
        "services": services,
    }
    with open(os.path.join(LAYER1, "services.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=False)
        fh.write("\n")

    # ---- the human map (BF4-07) ----
    abi = [s for s in services if s["class"] == "runs on the proven ABI"]
    prop = [s for s in services if s["class"] == "needs a proposal"]
    lib = [s for s in services if s["class"] == "library (no kernel calls)"]
    outside = sorted({n for s in services for n in s["syscalls"] if n not in FREEZE})

    L = []
    A = L.append
    A("# Services against the frozen ABI (BF4-07)")
    A("")
    A("Generated by `os-build/layer1/gen_services.py` — do not edit by hand.")
    A("Regenerate after any change under `services/`, and the table follows.")
    A("")
    A("**What this measures.** For each service, the `sys_*` externs reachable from its")
    A("sources through `import` (not the ones it merely mentions in a comment), and the")
    A("native run that drives it, if there is one. A service whose calls are all inside")
    A("the freeze is *runs on the proven ABI*. A service that reaches an extern outside")
    A("it is *needs a proposal* — the kernel cannot run it today, and no amount of green")
    A("native output changes that, because the host shim is substituting for a kernel.")
    A("")
    A("## The freeze, as the code uses it")
    A("")
    A("| F1 | call | declared in | services reaching it |")
    A("|---|---|---|---|")
    for name, (num, what) in sorted(FREEZE.items(), key=lambda kv: kv[1][0]):
        users = [s["name"] for s in services if name in s["syscalls"]]
        A("| %d | `%s` — %s | `services/common/sys/sys.goose` | %d |" % (num, name, what, len(users)))
    A("")
    A("| reserved | call | why it is not in the freeze |")
    A("|---|---|---|")
    why = {
        "sys_ticks": "clock read; F1 has no slot for it, and the services poll it in every wait loop",
        "sys_net_send": "device output; no NIC in the freeze",
        "sys_net_recv": "device input; no NIC in the freeze",
        "sys_spawn": "process creation; no address space in the freeze",
        "sys_kill": "process signal; no address space in the freeze",
    }
    for name in outside:
        where = ""
        for s in services:
            if name in s["syscalls"]:
                where = s["name"]
                break
        A("| 6-15 | `%s` | %s |" % (name, why.get(name, "not in the freeze; see the source")))
    A("")
    A("## Class 1 — runs on the proven ABI (%d services)" % len(abi))
    A("")
    A("| service | entry | entry proof | native run | checks | calls |")
    A("|---|---|---|---|---|---|")
    for s in abi:
        A("| `%s` | %s | %s | %s | %d | %s |" % (
            s["name"],
            "`entry.goose`" if s["entry"] else "—",
            s["entry_status"],
            s["test"] or "none",
            s["checks"],
            ", ".join("`%s`" % c for c in s["syscalls"]) or "—"))
    A("")
    A("## Class 1b — modules with no kernel calls at all (%d)" % len(lib))
    A("")
    A("These are libraries every other service links against. They make no `sys_*` call,")
    A("so \"runs on the ABI\" would be a claim about nothing; what they have is a native")
    A("run that proves the logic, and a caller one layer up that does the syscalls.")
    A("")
    A("| module | native run | checks |")
    A("|---|---|---|")
    for s in lib:
        A("| `%s` | %s | %d |" % (s["name"], s["test"] or "none", s["checks"]))
    A("")
    A("## Class 2 — needs a proposal (%d services)" % len(prop))
    A("")
    A("| service | outside the freeze | native run | checks | what it would take |")
    A("|---|---|---|---|---|")
    for s in prop:
        gaps = [c for c in s["syscalls"] if c not in FREEZE]
        A("| `%s` | %s | %s | %d | %s |" % (
            s["name"],
            ", ".join("`%s`" % c for c in gaps),
            s["test"] or "none",
            s["checks"],
            "BF4-08 §" + gaps[0] if gaps else "—"))
    A("")
    A("## Class 3 — host-only forever")
    A("")
    A("There is no service in this corpus whose *purpose* is host-only. The host-only")
    A("surface is the shim itself (`os-build/layer1/host/host_shim.c`), which refuses")
    A("five calls on purpose rather than faking them; that refusal is what makes the")
    A("native runs evidence. Nothing in `services/` is classified here, and this section")
    A("says so instead of listing a fake entry.")
    A("")
    A("## What this table cannot tell you")
    A("")
    A("- A green native run does not mean the service ran on the kernel ABI. It ran")
    A("  against `host_shim.c`, a linker-level substitute. The `sys_*` column is the")
    A("  part that transfers.")
    A("- `sys_ticks` is used by almost every waiting service and is **not** in F1. Until")
    A("  a proposal lands, \"runs on the proven ABI\" means \"its calls are all in the")
    A("  freeze\", not \"the freeze is sufficient to boot it\".")
    A("")
    with open(os.path.join(LAYER1, "SERVICES_SYSCALL_MAP.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))

    print("services: %d  class1: %d  class2: %d  outside freeze: %s"
          % (len(services), len(abi), len(prop), ", ".join(outside)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
