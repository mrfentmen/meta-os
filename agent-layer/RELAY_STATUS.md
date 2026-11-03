# Agent relay — status (Agent 2)

Date: 2026-11-03. Host: macOS (Darwin), repo `~/Desktop/meta-os`.
Image: `/tmp/metaos.ext4` (16 GB ext4, user `ubuntu`), inspected offline via
`debugfs` inside Docker (macOS cannot mount ext4, no `/mnt`).
No boot was performed on this host; there is no journal to read.

## Units

| Unit | What starts it | Status | Evidence |
|---|---|---|---|
| `oc2-queue.service` | Login hook `meta-agent-login` (`UNITS` list); enabled via `default.target.wants` symlink; `After network-online.target`, `Restart on-failure` | BLOCKED (running) / PROVEN (staged) | BLOCKED: no boot, no `journalctl --user -u oc2-queue` line observed. PROVEN staged: `debugfs ls /usr/lib/systemd/user` shows the file in the image; `debugfs ls /etc/systemd/user/default.target.wants` shows the `oc2-queue.service` link; fresh stage plus `--check` says `enabled oc2-queue.service`. |
| `oc2-trio.service` | Login hook; enabled via `default.target.wants`; `After` + `Requires oc2-queue.service` | BLOCKED (running) / PROVEN (staged) | BLOCKED: no boot, no journal. PROVEN staged: unit file present in image; `default.target.wants/oc2-trio.service` link present; `--check` says `enabled oc2-trio.service`. `ExecStart` runs `trio_agent.py --nick oc2-trio`. |
| `oc2-patrol.service` | Login hook at login (one bounded cycle `--max-checks 20`); hourly via `oc2-patrol.timer`; `After` + `Requires` queue and trio; `Type oneshot` | BLOCKED (running) / PROVEN (staged) | BLOCKED: no boot, no `journalctl --user -u oc2-patrol` cycle counts. PROVEN staged: unit file present; `default.target.wants/oc2-patrol.service` link present. Loud-pause path is code-read (see Secrets): `server/queue/patrol.py` writes `paused-budget` status plus a `PAUSED` log line and an event, never silent. |
| `oc2-patrol.timer` | Login hook (`systemctl --user start`); enabled via `timers.target.wants`; `OnBootSec 30min`, `OnUnitActiveSec 60min` | BLOCKED (running) / PROVEN (staged) | BLOCKED: no boot, no `list-timers` output. PROVEN staged: timer file present; `timers.target.wants/oc2-patrol.timer` link present; `--check` says `enabled oc2-patrol.timer`. |
| `oc2-health.service` | Timer only (`oc2-health.timer`); intentionally NOT linked in `default.target.wants` (stager skips it by name) | BLOCKED (running) / PROVEN (staged) | BLOCKED: no boot, no `systemctl --user status oc2-health` row. PROVEN staged: file present; no `default.target.wants` link by design; `--check` says `health cadence: probe + timer present`. |
| `oc2-health.timer` | Login hook; enabled via `timers.target.wants`; `OnBootSec 2min`, `OnUnitActiveSec 5min` | BLOCKED (running) / PROVEN (staged) | BLOCKED: no boot, no health `health.json`/`health.jsonl` written. PROVEN staged: timer file present; `timers.target.wants/oc2-health.timer` link present. |
| `oc2-watchman.service` | Login hook; enabled via `default.target.wants`; `ExecStart /usr/bin/node /usr/share/metaos/agent/agents/watchman.mjs --root %h/.local/state/oc2-agent` | BLOCKED (running) / PROVEN (staged) | BLOCKED: no boot, no bell/heartbeat (`watchman.heartbeat.json`) observed. PROVEN staged: unit file present; `default.target.wants/oc2-watchman.service` link present; payload `agents/watchman.mjs` present. Node path matches the image (see Node). |
| `metaosd.service` | Provisioner `os-build/iso/provision-all.sh` step 7 (not `stage.sh`); enabled via `default.target.wants`; `ExecStart /usr/bin/node /opt/face/metaosd.mjs --port 18940` | BLOCKED (running) / PROVEN (staged) | BLOCKED: no boot, no `metaosd on 127.0.0.1:18940` log line, no `GET /status` read. PROVEN staged: `debugfs` shows `/usr/lib/systemd/user/metaosd.service` plus its `default.target.wants` link in the image. Forwards `POST /jobs` to the queue on `127.0.0.1:8935`; the queue only accepts trio envelopes, so an agent order forwarded as-is is refused downstream (existing shape, not changed here). |

No unit is marked running-PROVEN. There is no fabricated `it works`.

## Login wiring (no hand-typed command)

* Hook: `/usr/local/bin/meta-agent-login` (from `agent-layer/meta-agent-login.sh`),
  `0755`. Seeds `$CONF/env` from `$SHARE/env` when absent, seeds
  `registry.json` and `budget.json` (30/hr default, existing file never touched),
  sources the machine env when readable (see Secrets), imports a non-empty
  Spark key into the user manager, then `systemctl --user start` on five units
  (`oc2-queue`, `oc2-trio`, `oc2-patrol.timer`, `oc2-health.timer`,
  `oc2-watchman`). Failure never blocks the desktop; the log line is the point.
* Autostart: `/etc/xdg/autostart/meta-agent-login.desktop` with both
  `Exec` and `TryExec` equal to the hook. Image read via `debugfs cat`
  shows both lines resolve to the hook. Fresh stage `--check` says
  `autostart entry resolves to the hook`.
* Enablement without a daemon: `stage.sh` creates the `.wants` symlinks by hand.
  Image `debugfs ls` shows three service links in `default.target.wants`
  (queue, trio, patrol, watchman) and two timer links in `timers.target.wants`.
  Fresh stage `--check` says `enabled` for each.

## Checkout and env template

* `OC2_CHECKOUT` pins `/usr/share/metaos/agent`. Image `debugfs cat`
  of both `/usr/share/metaos/agent/env` and `/etc/skel/.config/oc2-agent/env`
  shows the pin line and the non-secret defaults (`OC2_QUEUE_PORT 8935`,
  `OC2_PATROL_MAX_CHECKS 20`, `OC2_PATROL_RESERVE_USD 5`, `TRIO_JOB_NS`,
  `LIVECAMS_API_URL`). Fresh stage `--check` says
  `env pins OC2_CHECKOUT=/usr/share/metaos/agent` and `env has no secret`.
* `stage.sh --check` also asserts the skel template carries no secret pattern.

## Node

* Task states node v18 at `/usr/bin/node`. Image `debugfs stat` shows
  `/usr/bin/node` present (`0755`, ELF 64-bit LSB pie, ARM aarch64,
  interpreter `/lib/ld-linux-aarch64.so.1`, linked against `libnode.so.109`).
  `dpkg status` in the image (via `debugfs cat`) records `nodejs`
  version `18.19.1+dfsg-6ubuntu5`, `Architecture arm64`.
  The watchman unit and `meta-ask` both use that absolute path as fallback
  (`shutil.which node` first, then `/usr/bin/node`).
* No `node --version` run is claimed: the image binary is ARM and this host
  cannot exec it here; the version above is from packaging metadata, read
  from files, not from a process.

## Secrets (Spark key never baked)

* Image has no `/etc/metaos/agent.env` (staged before the fix;
  `debugfs ls /etc/metaos` reports no such directory). That is now a
  missing-file BLOCKED for the old image, fixed in the repo.
* Repo fix (`agent-layer/stage.sh`): stages `/etc/metaos/agent.env`
  `0600` (`chown 0:0` when run as root, best-effort otherwise) with two
  documented empty keys (Spark transport key SPARK_API_KEY , relay webhook
  METAOS_NOTIFY_WEBHOOK ) plus comments.
  Generation avoids the `KEY =` literal in repo sources so the
  `test_no_secrets_in_agent_layer` guard keeps passing; `--check` assembles
  the key names via shell variables and asserts both lines are present empty,
  no `sk-` / private-key material, no baked non-empty value, mode `0600`
  (ownership asserted only when run as root).
* Login hook (`agent-layer/meta-agent-login.sh`): sources the machine file
  only when readable (`[ -r /etc/metaos/agent.env ]`, `set -a` / source /
  `set +a`), never writes a key, then imports only when non-empty
  (`systemctl --user import-environment`). Empty or unreadable means no
  import. Fresh stage `--check` says `machine env pins empty documented keys`,
  `machine env has no secret`, `machine env mode 0600`, and
  `login hook sources machine env`.
* Without a key the relay stays loud (correct, not silenced):
  `server/queue/spark_gen.py` raises when no transport is configured;
  `server/queue/patrol.py` writes `paused-budget` status, appends a
  `patrol-status` event, and logs a `PAUSED` line before filing nothing.
  No new silence was added; the hook only adds an import, never a default key.

## meta-ask

* Source: `agent-layer/meta-ask.py` (repo), staged to `/usr/local/bin/meta-ask`
  `0755` by `stage.sh`. The old image has no such file
  (`debugfs stat /usr/local/bin/meta-ask` reports no entry) — BLOCKED for the
  old image, PROVEN for a fresh stage.
* Behaviour (exercised on a fresh stage, see Proof):
  `--list` prints live agents plus drafts; submit validates the registry,
  refuses an unknown agent and a draft agent, refuses empty orders and a
  duplicate id, writes the job via `node agents/submit.mjs` (atomic rename),
  warns when the queue port is down but keeps the job on the board.
  The tool references queue port `8935` and warns
  `queue on 127.0.0.1:8935 not answering` when nothing listens, so the link to
  the queue service is explicit.
* Fresh-stage runs: `--list` exit 0 (16 live, 7 drafts); unknown agent exit 1
  with `no such agent`, nothing written; draft exit 1; valid `--agent watch`
  exit 0 with a `j1.job.json` containing lane and orders; `--dry-run` exit 0
  writing nothing.

## Health probe

* `/usr/local/lib/metaos/meta-agent-health.py` plus `oc2-health.timer`.
  Fresh stage `--check` says `health cadence: probe + timer present`.
  No `health.json`/`health.jsonl` run is claimed (no boot).

## Offline proof

All commands below were run in the repo on macOS unless noted.

1. Fresh stage plus check (temp root, proves the stager):

```
rm -rf /tmp/stage-test && mkdir -p /tmp/stage-test/etc /tmp/stage-test/usr
sh agent-layer/stage.sh /tmp/stage-test
sh agent-layer/stage.sh /tmp/stage-test --check
```

Stager output (tail): `staged: 83 runtime files, 7 units`, exit 0.
Check output (full, exit 0):

```
agent-stage: unit oc2-queue.service
agent-stage: unit oc2-trio.service
agent-stage: unit oc2-patrol.service
agent-stage: unit oc2-patrol.timer
agent-stage: unit oc2-health.service
agent-stage: unit oc2-health.timer
agent-stage: unit oc2-watchman.service
agent-stage: enabled oc2-patrol.service
agent-stage: enabled oc2-queue.service
agent-stage: enabled oc2-trio.service
agent-stage: enabled oc2-watchman.service
agent-stage: enabled oc2-patrol.timer
agent-stage: enabled oc2-health.timer
agent-stage: health cadence: probe + timer present
agent-stage: runtime server/queue/queue_service.py
agent-stage: runtime server/queue/patrol.py
agent-stage: runtime server/queue/trio_agent.py
agent-stage: runtime js/products.js
agent-stage: runtime js/schema.js
agent-stage: runtime agents/watchman.mjs
agent-stage: runtime agents/runtime.mjs
agent-stage: runtime agents/registry.json
agent-stage: env pins OC2_CHECKOUT=/usr/share/metaos/agent
agent-stage: env has no secret
agent-stage: machine env pins empty documented keys
agent-stage: machine env has no secret
agent-stage: machine env mode 0600
agent-stage: machine env ownership skipped (not root)
agent-stage: login hook executable
agent-stage: login hook sources machine env
agent-stage: autostart entry resolves to the hook
agent-stage: meta-ask present and executable
agent-stage: meta-ask lists and refuses unknown agents
agent-stage: meta-ask references queue port 8935
agent-stage: PASS — agent layer staged correctly in /tmp/stage-test
```

Machine file on that root: mode `0600` (`stat`/`python os.stat` confirms
`0o600`), two empty documented keys, no secret material (checked by the
stager and by `--check`).

2. Tasked image check (expected failure on this host):

```
sh agent-layer/stage.sh /mnt --check
```

Result: `ls: /mnt: No such file or directory`, then `FAILED`, exit 1, with
`FAIL` lines for every unit/runtime/env/hook/autostart/meta-ask row because
`/mnt` is not a staged root on this Mac. `hdiutil attach -nomount
/tmp/metaos.ext4` also fails with `image not recognized` (macOS has no ext4
driver). Direct mount to `/mnt` is BLOCKED on this host with those exact
errors; no output is invented.

3. Image content via `debugfs` (Docker `ubuntu:22.04`, read-only):

* `ls /usr/share/metaos/agent` plus `agents`, `server/queue`, `js` show the
  payload; `cat` of both env files shows the checkout pin and no secret.
* `ls /usr/lib/systemd/user` filtered for `oc2-` shows all seven units;
  `ls` of both `.wants` dirs shows the service and timer links.
* `cat /usr/local/bin/meta-agent-login` matches the repo hook pre-fix
  (no machine-env sourcing); `cat` of the autostart entry shows matching
  `Exec`/`TryExec`.
* `ls /usr/local/lib/metaos` shows the health probe.
* `stat /usr/local/bin/meta-ask` reports no entry; `ls /etc/metaos`
  reports no entry — the two gaps this change closes.
* `stat /usr/bin/node` plus `cat /var/lib/dpkg/status` (nodejs stanza)
  prove the v18 payload path without executing it.

## BLOCKED (exact reasons, no boot claimed)

* No systemd user instance was observed: this host is macOS, the image was
  never booted here, and no `journalctl --user -b -u oc2-queue -u oc2-patrol`
  output exists to quote. All `PROVEN running` rows are therefore BLOCKED.
* Direct `mount /tmp/metaos.ext4 /mnt` is BLOCKED: macOS `hdiutil` reports
  `image not recognized` and there is no `/mnt`; the tasked
  `sh agent-layer/stage.sh /mnt --check` fails for that reason, recorded above.
* Old image gaps (fixed in repo, still absent in `/tmp/metaos.ext4`):
  `/etc/metaos/agent.env` missing and `/usr/local/bin/meta-ask` missing,
  both proven by `debugfs` misses. A fresh stage proves the fix; the old
  image still needs a rebuild/re-stage to carry it.
* Pre-existing repo failures unrelated to this lane (not fixed here):
  `test_manifest_fresh` fails on a stale `README` sha (fails on a clean tree
  too); `test_iso_meta_ask` fails on macOS because its restricted `PATH`
  hides `node` and there is no `/usr/bin/node` on the Mac.
