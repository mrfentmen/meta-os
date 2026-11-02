#!/usr/bin/env bash
# os-build/layer1/run_native.sh — build and run the service corpus on a host.
#
# BF4-01. Each test program in services/tests/ is a driver for one service: it
# imports the service's logic and asserts against it. This script builds each one
# for real (Goose -> C -> clang), runs it, and records the transcript. The
# syscall surface is provided by host/host_shim.c, which implements the ten
# `sys_*` externs and refuses the four a host cannot honestly provide.
#
# What a pass means: the service logic ran, against real memory and a real clock.
# What it does not mean: that anything booted. No scheduler, no address space.
#
# Exit status: 0 only when every program builds and runs to exit 0.
#
# Usage: os-build/layer1/run_native.sh [-v] [name...]

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2

SHIM=os-build/layer1/host/host_shim.c
OUT=os-build/layer1/host/build
mkdir -p "$OUT"

verbose=0
if [ "${1:-}" = "-v" ]; then verbose=1; shift; fi

tmp="services/.run_XXXXXX.goose"
cleanup() { rm -f services/.run_*.goose; }
trap cleanup EXIT

pass=0
fail=0
skipped=0
failed=()
declare -a ROWS

# Build and run one root program. $1 = label, $2 = source path relative to services/
run_one() {
    local label="$1" src="$2" base c exe log
    base="$(basename "$src" .goose)"
    c="$OUT/$base.c"
    exe="$OUT/$base"
    log="$OUT/$base.log"

    cp "$src" "services/.run_$base.goose"
    if ! goose -o "$c" --standalone "services/.run_$base.goose" >"$log.gen" 2>&1; then
        fail=$((fail + 1)); failed+=("$label (codegen)")
        ROWS+=("$label|CODEGEN-FAIL|0|0|$(grep -m1 'error:' "$log.gen" | cut -c1-90)")
        return
    fi
    rm -f "services/.run_$base.goose"

    if ! clang -O1 -w "$c" "$SHIM" -o "$exe" >"$log.cc" 2>&1; then
        fail=$((fail + 1)); failed+=("$label (cc)")
        ROWS+=("$label|CC-FAIL|0|0|$(grep -m1 'error:' "$log.cc" | cut -c1-90)")
        return
    fi

    "$exe" >"$log" 2>&1
    local rc=$?
    # A test ends with "pass=<N> fail=<M>" or "passed <N>"; read whichever is there.
    local p f
    p=$(grep -oE 'pass=[0-9]+' "$log" | tail -1 | cut -d= -f2)
    [ -z "$p" ] && p=$(grep -oE 'passed [0-9]+' "$log" | tail -1 | awk '{print $2}')
    [ -z "$p" ] && p=$(grep -c '^ok   ' "$log")
    f=$(grep -oE 'fail=[0-9]+' "$log" | tail -1 | cut -d= -f2)
    [ -z "$f" ] && f=$(grep -c '^FAIL ' "$log")
    [ -z "$f" ] && f=0

    local firstfail
    firstfail=$(grep -m1 '^FAIL ' "$log" | cut -c1-90)

    if [ "$rc" -eq 0 ]; then
        pass=$((pass + 1))
        ROWS+=("$label|RUNS|$p|$f|")
        printf '  RUNS    %-22s exit 0  pass=%s fail=%s\n' "$label" "$p" "$f"
    else
        fail=$((fail + 1)); failed+=("$label (exit $rc)")
        ROWS+=("$label|FAILS|$p|$f|exit $rc ${firstfail}")
        printf '  FAILS   %-22s exit %s  pass=%s fail=%s  %s\n' "$label" "$rc" "$p" "$f" "$firstfail"
    fi
    if [ "$verbose" = 1 ]; then sed 's/^/          /' "$log" | tail -5; fi
}

echo "== libraries and non-entry services (services/root.goose)"
echo "   (not runnable as a program: no main; exercised through the drivers below)"

echo
echo "== drivers (services/tests)"
if [ "$#" -gt 0 ]; then
    for n in "$@"; do run_one "tests/$n" "services/tests/$n.goose"; done
else
    for t in services/tests/*.goose; do
        run_one "tests/$(basename "$t" .goose)" "$t"
    done
fi

echo
echo "== entry points (services/*/entry.goose)"
# An entry point exports svc_entry, not main, so it is not a program on its own.
# It is built (codegen + compile) to prove the entry file compiles, and NOT run,
# because a host process has no supervisor to call svc_entry.
for e in services/*/entry.goose; do
    [ -e "$e" ] || continue
    svc="$(basename "$(dirname "$e")")"
    c="$OUT/entry_$svc.c"
    # An entry whose svc_entry takes a BootInfo cannot be driven from a host process:
    # there is no kernel to hand it the block. Fabricating one would mean running the
    # service against a fake boot record and then reporting the result as a run, so those
    # entries are typechecked (check_services.sh covers the whole corpus) and NOT run.
    if grep -q 'service_main(boot' "$e"; then
        skipped=$((skipped + 1))
        ROWS+=("entry/$svc|TYPECHECKS (not run)|0|0|svc_entry takes a kernel BootInfo; no host boot block")
        printf '  TYPECHECKS %-19s (svc_entry takes BootInfo; not run)\n' "entry/$svc"
        continue
    fi
    {
        printf 'import %s.entry;\n\nfn main() {\n    let rc = service_main();\n    if rc != 0 { sys_exit(rc); }\n}\n' "$svc"
        printf 'import common.sys.sys;\n'
    } > "services/.run_entry_$svc.goose"
    if goose -o "$c" --standalone "services/.run_entry_$svc.goose" >"$c.gen" 2>&1 \
       && clang -O1 -w "$c" "$SHIM" -o "$OUT/entry_$svc" >"$c.cc" 2>&1; then
        skipped=$((skipped + 1))
        ROWS+=("entry/$svc|BUILDS (not run)|0|0|svc_entry; no supervisor on a host")
        printf '  BUILDS  %-22s (svc_entry; not run: no supervisor)\n' "entry/$svc"
    else
        fail=$((fail + 1)); failed+=("entry/$svc (build)")
        ROWS+=("entry/$svc|BUILD-FAIL|0|0|$(grep -m1 'error:' "$c.gen" "$c.cc" 2>/dev/null | cut -c1-90)")
        printf '  FAILS   %-22s build\n' "entry/$svc"
    fi
    rm -f "services/.run_entry_$svc.goose"
done

echo
printf 'ran: %d programs  RUNS=%d  FAILS=%d  built-not-run=%d\n' \
    "$((pass + fail))" "$pass" "$fail" "$skipped"
if [ "${#failed[@]}" -gt 0 ]; then
    printf 'failed: %s\n' "${failed[*]}"
fi

# Machine-readable row set, for the report table (label|status|pass|fail|note).
#
# A FILTERED run writes somewhere else. `run_native.sh t65_fs` used to overwrite this
# file with its one row, so the table the docs are generated from silently shrank to the
# last test anybody ran by hand -- and every generator downstream then reported "no native
# run" for 26 programs that were green an hour earlier. The full table is only written by
# a full run.
if [ "$#" -eq 0 ]; then
    {
        printf '%s\n' "${ROWS[@]}"
    } > os-build/layer1/host/run_rows.txt
else
    {
        printf '%s\n' "${ROWS[@]}"
    } > os-build/layer1/host/run_rows.last_filtered.txt
fi

[ "$fail" -eq 0 ]
