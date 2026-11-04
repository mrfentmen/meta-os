# Agent pipeline — proof from inside the guest

Date: 2026-11-04 (UTC). Image: `/tmp/metaos.ext4`, booted detached at 1920x1080
with the repo shared read-only on `/mnt/metaos` (tag `metaos_repo`).
Capture: `captures/agent-pipeline-proof-1920x1080-20261104T015819Z.png`
(desktop alone: `captures/desktop-clean-1920x1080-20261104T015819Z.png`).

## What the screen said

```
metaos ~$ bash /mnt/metaos/os-build/tools/proof_agent_pipeline.sh
payload: /usr/share/metaos/agent
state:   /tmp/metaos-agent-proof
agent:   nervus

payload watchman.mjs                           OK
meta-ask present                               OK   /usr/local/bin/meta-ask
watchman --once exits 0                        OK
meta-ask reports the job finished              OK   job proof-1 finished cleanly
a run was started                              OK   1 run(s)
a receipt was written                          OK   { "id": "proof-1", "agent": "nervus"…
nested drain refused                           SKIP no watch job was on the board in this pass
runs stayed bounded                            OK   1 run(s)
no watchman left running                       OK   1 (one is this check's own grep)

RESULT: PASS — a job handed to an agent ran and filed a receipt in the guest
```

That is a person asking for work, the relay picking it up, a worker running,
and a receipt coming back — on the installed payload under `/usr/share/metaos`,
not in a checkout.

## The three bugs this took

1. **Every submitted job died with `failed (exit 1)` and nothing said why.**
   `/usr/share/metaos/agent` is root-owned, so the relay's `mkdir jobs/` threw
   EACCES at startup. `agents/watchman.mjs:406-440` now falls back to the user's
   state dir when its own directory is not writable; a checkout keeps its old
   behaviour.
2. **A `watch` job spawned watchmen until the machine gave up.** The drain
   spawned a `watch` job, which spawned a drain that read the same board and
   found the same order. Each relay now stamps `METAOS_RELAY_DEPTH` into the
   environment its children inherit (`agents/watchman.mjs:420`) and refuses the
   self-drain by name (`:259`). A finished job is also skipped when its receipt
   is newer than the order (`:79`, `:175`), so a restart no longer re-runs the
   audit trail.
3. **Hosted workers could not write either.** `nervus`, `aegis` and
   `handsfree` wrote their ledgers beside their own source. They now resolve a
   writable base through `agents/state-root.mjs:26`; and `agent-layer/stage.sh:254`
   stages the trees the registry actually names — before that, a job for nervus
   started node on a file that was not in the image at all.

## How to re-run it

On the host, before booting:

```
sh os-build/tools/sync_image.sh            # face, dock, icons, prompt
docker run --rm --privileged -v /tmp/metaos.ext4:/disk.img -v "$PWD:/repo" \
  ubuntu:24.04 bash -c 'mkdir -p /mnt; mount -o loop /disk.img /mnt;
  sh /repo/agent-layer/stage.sh /mnt; sh /repo/agent-layer/stage.sh /mnt --check; umount /mnt'
sh os-build/tools/proof_boot.sh --timeout 180
```

In the guest (Alt+F2 → `xfce4-terminal`):

```
bash /mnt/metaos/os-build/tools/proof_agent_pipeline.sh
```

`AGENT=` picks the worker (default `nervus`). Exit 0 only when every row is OK.

## What this does NOT prove

- **No model is involved.** `nervus` is the STUB runner; it says so in its own
  output. The queue service on 8935 (the thing that actually calls a model) is
  not running in this image, so `meta-ask` prints its warning and the job waits
  for the relay instead. That warning is correct behaviour, not a failure.
- **Science Lab workers are not staged.** `os/worlds/science-lab` is 94 MB and
  was left out of the payload; a `research-director` job would fail to find its
  program. Stage it deliberately, or point the registry at `/mnt/metaos`.
- **`aegis/cycle.mjs` still writes under the payload.** It spawns stage scripts
  that write into `os-build/`; that one is not fixed here.
- **No OSV/network pass, no AV, no FIPS.** Nothing here is a security claim.
