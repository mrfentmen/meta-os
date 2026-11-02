# Failure matrix (BF5-02)

For every service that appears in the boot order: the ways it can fail, and whether something
drives that failure natively. Written 2026-11-02 against the tree at the Round-5 close.

The columns are not "we thought about this". **EXERCISED** means a test asserts the outcome and the
run is green (`SERVICE_RUNS.md`); **UNEXERCISED** means the code path exists and nothing drives it,
which is the honest word for a promise. Every cell marked EXERCISED names the test.

| Service | Bad config / bad input | Missing dependency | Crash and restart | Quota / full | Hang | Corrupt storage |
|---|---|---|---|---|---|---|
| `bootlog` | t72 (format cases) | t61 (DAG) | — | — | — | — |
| `devices` | t77 (kind 0, empty name, 25-byte name, illegal transition, full table), t77/hotplug (empty mask, unknown event, queue full) | t61 | — | t77 (table stops at `DEV_MAX`, `E_NOROOM` past it) | — | — |
| `time` | t51 (bad epoch, bad day) | t61 | — | — | — | — |
| `storage` | t54 (out of range both ends) | t61 | — | t54 (quota, seal) | — | t65 (bad superblock) |
| `callmatrix` | t69 (unknown caller/callee, denied edge) | t61 | — | — | — | — |
| `supervisor` | t52 (bad name, bad transition) | t52 (`can_start` reason) | **t52** (never/on-fail/always, cap, backoff), t74 | — | **t74/rehearsal** | — |
| `console` | t49 (line editing) | t61 | — | t49 (editor full) | **BOOT_REHEARSAL** (hangs on `read_key`) | — |
| `input` | t56 (overlong key), t102 (NUL key, unmatched dead key, layout hole) | t61 | — | t49 (editor full) | — | — |
| `logfmt` | t72 (truncated record) | t61 | — | — | — | — |
| `logd` | t72, t74 (level, long record) | t61 | — | **t74** (ring full, counted) | — | t74 (tampered trail is audit's, see below) |
| `watchdog` | t53 (zero handle, negative period/grace/allowance) | t61 | — | t53 (past allowance is dead) | — | — |
| `audit` | t60 (bad offset, read past end), t72 | t61 | — | t60 (writer refuses, drops counted) | — | **t60 + t74** (flipped byte, truncation) |
| `netcfg` | t57 (bad config file), t101 (every prefix 0-32 contiguous, /33 refused) | t61 | — | — | — | — |
| `net` | t67 (bad header, bad length), t101 (route refusals, broadcast MAC) | t61 | — | t67 (queue) | — | — |
| `display` | t56 (clipped draw) | t61 | — | — | — | — |
| `session` | t77 (owner 0, missing user id, missing agent handle, three wrong tokens, empty expected token), t76 | t61 | — | t77 (table stops at `SES_CAP`, `E_NO_SPACE` past it) | — | — |
| `dhcp` | t57 (bad option, bad length) | t61 | — | — | — | — |
| `dns` | t57 (bad label, compression loop) | t61 | — | — | — | — |
| `socket` | t77 (unbound send, privileged port, port 70000, zero-length, past MTU, 0.0.0.0, port 0, closed handle) | t61 | — | t77 (two queued is the limit, table cap is hard) | — | — |
| `timesync` | t77 (short packet, client mode, stratum 0, leap 3, no transmit time, two days out, negative delay) | t61 | — | — | — | t77 (a corrupt reply is refused, a good one after it still applies) |
| `updater` | t58 (unknown key, dup path, short digest) | t61 | t58 (rollback record) | t58 (slot refusal) | — | t58 (digest mismatch) |
| `agenthost` | t59 (grant on a dead agent, ungranted bit) | t61 | t59 (agent exit is recorded) | — | — | — |

`t62`–`t64` (bytes, str, hex) and `t45`–`t48` (format, ring, cfg, boot record) are the libraries the
rows above run on; a library failure shows up as the service's failure, so they are not rows.

## The second cache of empty cells: the four services with no driver, closed by `t77`

`devices`, `session`, `socket` and `timesync` each had an entire blank row because no test
imported them. `services/tests/t77_gaps.goose` imports all four (plus `devices/hotplug`) and
drives the failures that matter, which turned up three real defects rather than a clean audit:

| Service | What was claimed | What the driver found |
|---|---|---|
| `session` | `login_submit` opens a session for the user | **A defect.** It called `ses_open` with `user_id = 0`, which `ses_open` refuses for `OWNER_USER`; the correct token could not log anyone in. |
| `devices/hotplug` | `delivered + dropped == raised` | **A defect.** The delivered counter was incremented on raise, so a full queue reported more delivered than the queue ever held. |
| `timesync` | offsets are measured to the millisecond | **A defect.** The NTP fraction was scaled by 2^32/1000, truncating the sub-second field; a 10 ms server turnaround measured as 5 ms and every offset was that much out. |

`devices` and `socket` came out clean — the table caps, the state machine and the queue limits
all refused correctly on the first run. That is the useful half of the result: it says the
refusals in those two files are real and not aspirational.

## The four cells that were empty before this task, and what closed them

| Cell | What was claimed and not driven | What drives it now | Result |
|---|---|---|---|
| `logd` full ring | "records refused are counted" | `t74`: 200 records against a 64-slot ring | **A defect.** The drop was counted, but an ERROR record was dropped before the flush that exists to make room for it — the priority policy was dead code on a full ring. Fixed in `logd.goose`: an error flushes and retries once before the loss is counted. |
| `storage` corrupt superblock | "mount validates the superblock" | `t74`: bad magic, then a single flipped byte under a good magic | Refuses with `E_INVAL`, then `E_VERIFY`. The CRC is what catches the bit flip; magic alone would have mounted it. |
| `audit` tampered record | "a changed byte breaks the chain" | `t74`: one body byte flipped, and a truncated buffer | Verification stops at the tampered record and reports the sequence it stopped at; a truncated trail verifies fewer records rather than reading past the end. |
| `console` hang | the start timeout (unbuilt) | `BOOT_REHEARSAL.md`: `console` starts, prints its banner, and loops on `read_key` forever | **Hangs.** Killed by the rehearsal's 5-second bound, not by the supervisor, because the start timeout does not exist. |

## What is still unexercised, named

- **`session`** has a driver but no *second* path: `t77` covers the user login end to end, the
  agent session (`ses_open(OWNER_AGENT, ...)`) is only driven for its refusal, never opened and
  used. The agent's session is the one an agent host will actually hold.
- **Hang** is only exercised for `console`, and only by the rehearsal's timeout. No service is
  instrumented to prove it was stopped by the layer.
- **Crash and restart** is exercised as a decision (`t52`), never as an event: no process is
  spawned or killed anywhere in the corpus.
- **Corrupt storage** covers the superblock and the audit trail. The inode table, the bitmap and the
  directory blocks are checked by `fsck` (`t65`) but not corrupted deliberately in a test.
- **`net`, `dhcp`, `dns`, `updater`** are exercised for bad input only. Nothing drives a *dropped*
  packet, a timeout, or a retry — the failure modes a network has when the peer is simply absent.

## How to reproduce

```sh
./os-build/layer1/run_native.sh t74_failure t52_supervisor t58_updater t65_fs t67_net t77_gaps
./os-build/layer1/boot_rehearsal.sh 5
```

The first command is the matrix's evidence; the second is the hang. Everything else in the table is
in `SERVICE_RUNS.md`.
