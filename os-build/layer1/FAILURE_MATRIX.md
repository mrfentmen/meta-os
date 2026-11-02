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
| `input` | t56 (overlong key) | t61 | — | t49 (editor full) | — | — |
| `logfmt` | t96 (levels, clamping, tag and message truncation, padded column, refusals) | t61 | — | — | — | — |
| `logd` | t72, t74 (level, long record) | t61 | — | **t74** (ring full, counted) | — | t74 (tampered trail is audit's, see below) |
| `watchdog` | t53 (zero handle, negative period/grace/allowance) | t61 | — | t53 (past allowance is dead) | — | — |
| `audit` | t60 (bad offset, read past end), t72 | t61 | — | t60 (writer refuses, drops counted) | — | **t60 + t74** (flipped byte, truncation) |
| `netcfg` | t57 (bad config file) | t61 | — | — | — | — |
| `net` | t67 (bad header, bad length) | t61 | — | t67 (queue) | — | — |
| `display` | t56 (clipped draw) | t61 | — | — | — | — |
| `session` | t77 (owner 0, missing user id, missing agent handle, three wrong tokens, empty expected token), t76 | t61 | — | t77 (table stops at `SES_CAP`, `E_NO_SPACE` past it) | — | — |
| `dhcp` | t57 (bad option, bad length) | t61 | — | — | — | — |
| `dns` | t57 (bad label, compression loop) | t61 | — | — | — | — |
| `socket` | t77 (unbound send, privileged port, port 70000, zero-length, past MTU, 0.0.0.0, port 0, closed handle) | t61 | — | t77 (two queued is the limit, table cap is hard) | — | — |
| `timesync` | t77 (short packet, client mode, stratum 0, leap 3, no transmit time, two days out, negative delay) | t61 | — | — | — | t77 (a corrupt reply is refused, a good one after it still applies) |
| `updater` | t58 (unknown key, dup path, short digest) | t61 | t58 (rollback record) | t58 (slot refusal) | — | t58 (digest mismatch) |
| `agenthost` | t59 (grant on a dead agent, ungranted bit), t97 (quota on a dead handle, impossible quota, blocked call, blocked byte, over-release, table full) | t61 | t59 (agent exit is recorded), t97 (stop twice) | t97 (call rate, window reset, backwards clock, storage limit, row table) | — | — |

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

## The face layer, added in R7

Six services joined the boot order this round, and each has a column here because each was
driven, not sketched. The failures chosen are the ones that would be silent: a limit that
clamps instead of refusing, a counter that reads as success, a format that parses itself.

| service | failure driven | driver | result |
|---|---|---|---|
| `settings` | out-of-range value, unknown key, control byte in text, corrupt import | `t86` (67 checks) | Refused whole; the import stages and commits at the end, so a bad line changes nothing. |
| `wallpaper` | fps 0 and 61, duplicate name, ninth wallpaper, pause counted per tick | `t87` (56 checks) | Refuses at `WL_MAX`, and a fullscreen pause is counted once, not once per tick. |
| `dock` | double click inside 1500 ms, launch that never reports, unpin while running | `t88` | Second click is `E_BUSY` and is not a launch; a pending launch past 5000 ms becomes a failure; unpin while running is refused. |
| `dashboard` | never sampled, exactly-at-window age, unknown kind, clock going backwards | `t89` (50 checks) | `DF_NEVER` and `DF_STALE` are returned instead of a zero; kind 5 is refused rather than clamped onto `net`. |
| `updater_client` | STOP file, bad digest, bad signature, rollback, re-check inside 60 s, apply failure | `t90` | Four distinct refusal codes above the error range; a failed apply stays `FAILED` until `uc_retry`. |
| `board` | full log, fifth room, comma in text, truncated export, bad import line | `t91` (58 checks) | Refuses rather than drops; the import is atomic; the export/import round trip preserves ids and counters. |

Two of these found defects on their first run: the board parser read `P,<id>,…` one field
off, and the six new services were outside the manifest, the boot table and the matrix at
once. Both are recorded in `SERVICES_FINAL.md`'s defect list.

## The face layer's quiet failures, added with `t94`

`t93` walks the happy path through all six face services. `t94_face_failures` (88 checks)
drives the failure each one would fail *silently* with, and asserts the state did not move
after the refusal, because a refusal that leaves half of something behind is the defect and
not the refusal.

| service | failure driven | result |
|---|---|---|
| `settings` | an import valid up to its last line and corrupt in it; an out-of-range value mid-file; a blank line; a 32-byte hostname; a hostname with a space | Nothing applied. The staging copy is committed only after the whole blob validates, so the wallpaper and hostname before the bad line survive. |
| `wallpaper` | ninth registration, 20-byte name, fps 0 and 61, duplicate name, select of an id the registry does not have | Refuses at `WL_MAX` without consuming an id; a select the registry cannot honour leaves the previous wallpaper current, so the screen is never blank. |
| `settings` → `wallpaper` | an index inside the store's range and inside the registry ceiling that this registry has no entry for | `E_NOTFOUND`, last good wallpaper still current. The store cannot validate against a registry it does not own, so the check belongs at the select. |
| `dock` | a result for a launch nobody requested, an id that does not exist, thirteenth pin, duplicate and 16-byte names, a restart | `E_STATE` on the unmatched result and the app does not start; `E_NO_SPACE` at `DK_MAX`; a restart empties the dock and ids restart at 1, which is why a result must be matched to a request and not to a number. |
| `dashboard` | 140% CPU, negative byte rate, kind 5, zero and 60001 ms windows, a sample stamped in the past, a producer restart, a read on a backwards clock | Refused with `E_INVAL` / `E_STATE`; the refused sample never lands; age floors at 0 so no frame can look fresh from the future; a restart leaves all four metrics `DF_NEVER`. |
| `board` | an unknown record kind (the format has no version byte, so another build's file shows up as a kind this one does not know), a post in a room the file does not define, a post with no text field, fifth room | `E_CORRUPT` / `E_NO_SPACE` and the live board is byte-for-byte what it was; the id counter does not move. |
| `updater_client` | a STOP file that appears **after** the update was offered, a re-check 1 ms inside the 60 s window, a backwards clock | **A defect.** STOP was consulted on `uc_check` only, so an offer made before the stop could still be applied — `uc_apply` takes no STOP argument and the state stayed `AVAILABLE`. Fixed: a STOP check now withdraws the offer, and `uc_apply` afterwards is `E_STATE`. The rate window is unchanged. |

The STOP defect is the one worth reading twice: every rule in that file was true at the
moment it was written and false one call later. The test is what made the window visible.

## What is still unexercised, named

- ~~**`session`** has a driver but no *second* path~~ — **closed in R7**: `t84_session_deep`
  opens and uses an agent session, and drives double attach, input to a locked session and a
  session closed twice. What is still missing is a session that outlives a supervisor restart:
  `ses_init` resets every slot, which is stated in `contracts/session.md` and not proven.
- **Hang** is only exercised for `console`, and only by the rehearsal's timeout. No service is
  instrumented to prove it was stopped by the layer.
- **Crash and restart** is exercised as a decision (`t52`, and `t92` runs a budget to
  exhaustion under load), never as an event: no process is spawned or killed anywhere in the
  corpus. `PROPOSALS.md` § P3a asks for the four slots that would change that.
- **Corrupt storage** covers the superblock and the audit trail. The inode table, the bitmap and the
  directory blocks are checked by `fsck` (`t65`) but not corrupted deliberately in a test.
- **`net`** is no longer bad-input only: `t85_net_deep` drives a truncated frame, a bad
  checksum, an ARP for an unknown address and a full link queue. **`dhcp`, `dns`, `updater`**
  are still exercised for bad input only — nothing drives a dropped packet or a retry, which is
  what a network does when the peer is simply absent.

## How to reproduce

```sh
./os-build/layer1/run_native.sh t74_failure t52_supervisor t58_updater t65_fs t67_net t77_gaps \
                               t93_face_walkthrough t94_face_failures
./os-build/layer1/boot_rehearsal.sh 5
```

The first command is the matrix's evidence; the second is the hang. Everything else in the table is
in `SERVICE_RUNS.md`.
