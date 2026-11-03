# Gap records — R13-016 fs

## R13-016-G1 — no heartbeat line

- **Claim:** `fs` emits a heartbeat line a supervisor can watch.
- **Reality:** there is no heartbeat, timer, uptime or last-progress field in any `fs` source
  file. The only status call is `fs_stats`, which returns free blocks and a write counter.
- **Evidence:** `grep -nEi 'heartbeat|health|alive|uptime' services/fs/*.goose` returns no
  matches; `services/fs/fs.goose:440-443`.
- **Impact:** a mounted but non-progressing filesystem produces no output. The supervisor's
  liveness rule cannot cover `fs` without a call-and-compare probe, which does not exist in the
  service contract.
- **Owner:** fs observability; supervisor liveness contract.

## R13-016-G2 — unmounted state is shaped like a zero reading

- **Claim:** `fs_stats` distinguishes “not mounted” from “mounted with no free blocks”.
- **Reality:** unmounted returns `(0, 0, E_STATE)`. A caller that reads only the first two fields
  sees zeros, the same shape as a mounted filesystem with no free blocks and no writes.
- **Evidence:** `services/fs/fs.goose:440-443`.
- **Impact:** a status renderer that ignores the code prints “0 free, 0 writes” for an unmounted
  filesystem. The third field is the only discriminator, and the README does not document the
  tuple.
- **Owner:** fs stats contract.
