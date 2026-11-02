# Runbook: the Lobster round trip, when a host exists (BF6-04 / F3)

**Every command below is unexecuted as of 2026-11-02.** The first one fails today
at step 2. The runbook exists so the first person with a built host knows exactly
what to run and what a pass looks like — and so nobody has to invent a transcript
to close the task.

## Step 0 — what must already be true

| Check | Command | Must print |
|---|---|---|
| the corpus builds and runs | `./os-build/layer1/run_native.sh` | `ran: 36 programs  RUNS=36  FAILS=0` |
| the exit surface is still five entry points | `grep -h '^export' services/*/entry.goose \| wc -l` | `5` |
| a callable function has been added | `grep -rn '^export "svc_' services/ \| wc -l` | **`0` today** — this is the step that is missing |

## Step 1 — export one callable function (this lane, no Lobster)

Add to `services/logd/logd.goose`:

```
export "svc_log_info" fn svc_log_info(tag: const u8[:], msg: const u8[:]) -> i64 {
    return log_info(tag, msg);
}
```

Build the C and prove the symbol exists:

```sh
goose -o /tmp/logd.c services/logd/entry.goose      # or the corpus build
clang -c /tmp/logd.c -o /tmp/logd.o
nm /tmp/logd.o | grep svc_log_info
```

Expected: one `T svc_log_info` line. **Any output other than a single defined
symbol means the export did not happen** — a `U` line means it was referenced,
not defined.

## Step 2 — a round trip through the C ABI (still this lane)

Write `os-build/layer1/host/dispatch_demo.c` that:

1. defines the ten syscall externs by linking `host_shim.c`,
2. calls `svc_log_info("smoke", "round trip")` from `main`,
3. returns its code as the process exit status.

```sh
clang -o /tmp/dispatch_demo os-build/layer1/host/dispatch_demo.c \
      os-build/layer1/host/host_shim.c /tmp/logd.o
/tmp/dispatch_demo; echo "exit=$?"
```

Expected: the logd line on the serial stream, then **`exit=0`**. This half does
not need Lobster and is worth committing on its own; if it fails, the Lobster
build is not the thing to fix.

## Step 3 — build a host with `svc_call`

The expensive step, and a toolchain task:

```sh
git clone https://github.com/aardappel/lobster /tmp/lobster-src
# register the dispatcher as a builtin (HOST_REQUIREMENTS.md §3), then:
cd /tmp/lobster-src && cmake -B build && cmake --build build -j
```

Failure reads:

- **link error naming `svc_call`** — the builtin was not registered; the build
  finished, the registration did not.
- **`undefined reference to sys_write_serial`** — the host was linked without the
  shim; the ten symbols are the host's obligation, not the service's.
- **build succeeds, `svc_call` returns -1 for every name** — the name table is
  empty; the dispatcher was compiled but no entry was generated.

## Step 4 — run the caller and commit the transcript

```sh
build/lobster os-build/layer1/lobster/CALLER.lobster 2>&1 | tee os-build/logs/L3-lobster-roundtrip.txt
```

Expected, in one file:

```
service answered: 0 (accepted)
[logd] smoke: round trip
fs.stat root: ino=1 code=0
```

Two independent facts in one transcript: the service's own serial line (it ran)
and the caller's return value (the call came back). **A transcript with only the
caller's line is not a round trip** — it is a print statement, and it is exactly
what the NO MOCKS rule exists to reject.

Only after that file is committed does `LOBSTER_BINDING.md` move from NOT BUILT to
RUNS, and only then may any report say a Lobster caller reached a service.
