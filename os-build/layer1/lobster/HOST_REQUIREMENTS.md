# What a Lobster host must provide (BF6-04 / Round 7 F2)

This is the contract, not a plan. A host that satisfies every line below can call
one service function and get an answer back. Nothing here has been run: **there is
no Lobster host in this repository and no `.lobster` file has been compiled.**
`LOBSTER_BINDING.md` says why, and still says it.

## 1. The syscall surface (already fixed, F1 freeze)

A service is a Goose program compiled to C and linked against ten externs. A host
that runs one must supply all ten symbols with these exact signatures — this is
`services/common/sys/sys.goose`, not a preference:

```c
void     sys_exit(int32_t code);                        /* 0 */
int64_t  sys_write_serial(const uint8_t *s, int64_t len);/* 1 */
int64_t  sys_write_console(const uint8_t *s, int64_t len);/* 2 */
int64_t  sys_read_key(uint8_t *out, int64_t cap);        /* 3 */
int64_t  sys_ticks(void);                                /* 4 */
void     sys_yield(void);                                /* 5 */
```

Numbers 6–15 are reserved in `PROPOSALS.md` and are **not** part of this contract:
a host that invents them will link, then disagree with the services at run time.

`slice` arguments are (pointer, length) pairs — never C strings. A host that
passes a `char *` and relies on `strlen` is already wrong for every service that
sends a slice of a larger buffer.

## 2. The entry symbol

Every service program exports exactly one of:

```c
int32_t svc_entry(void);            /* 4 services: bootlog, console, logd, time */
int32_t svc_entry(BootInfo *boot);  /* 1 service: example */
```

The host's spawn path calls `svc_entry`, treats the return as the service's exit
code, and nothing else. `svc_entry` taking no arguments is why a general
"call this service with these arguments" host cannot exist yet: see step 3.

## 3. The callable surface (does not exist)

To call a *function* and not just start a *program*, one symbol per callable
function has to exist. The dispatcher shape a host must be able to find:

```c
/* generated; one entry per exported service fn */
int64_t svc_call_<service>_<fn>(const char *name, int64_t name_len,
                                const uint8_t *args, int64_t args_len,
                                uint8_t *out, int64_t out_cap,
                                int64_t *out_len);
```

No such symbol exists today: `grep -rn '^export fn' services/` returns nothing
beyond the five `svc_entry`s. That is the gap, and it is in this lane, not in the
host.

## 4. What the host must do with a returned code

- `0` (`CODE_OK`) — success.
- A `5xxx` code — a service-level refusal; the code is stable vocabulary from
  `services/common/err/err.goose` and must be passed through, not remapped to -1.
- Negative — an infrastructure failure (bad handle, corrupt input).

A host that collapses every non-zero code to "error" loses the distinction the
whole error vocabulary exists to keep.

## 5. Scheduling and memory

- The host owns the service's memory: the services are built with no allocator
  and their fixed storage is measured in `size_audit.py` (163.8 KiB across 33
  services at last measure). A host that maps a stack per service must reserve at
  least that per running service.
- `sys_yield` must actually yield: `supervisor` and `deps` spin on it, and a host
  that makes it a no-op still passes the tests and hangs on a single core.
- `sys_ticks` must be monotonic. `time.sleep_ticks` gives up after `STALL_LIMIT`
  steady reads by design; a host with a coarse or frozen clock will make every
  sleep return false and every timing test lie.

## 6. What the host may not do

- May not call `svc_entry` twice to "restart" a service: the fixed storage is
  static and re-entry is undefined. Spawn a fresh process or reload the image.
- May not write to a service's buffers after the call returns; several services
  hand back views into their own storage (`logd` flush, `fs` read).
- May not assume the console is a terminal: `sys_write_console` is a byte sink
  and `console` re-renders its own line, exactly like a real terminal expects.
