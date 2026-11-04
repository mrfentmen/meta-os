# Lane B — Agent relay console (report)

Date: 2026-11-03. Host: macOS arm64, repo `~/Desktop/meta-os`. Image: `/tmp/metaos.ext4`
(arm64). All image work through `docker run --privileged ubuntu:22.04` with the
image loop-mounted read-write on a free loop device (lane C holds loop0/loop1;
a free device was taken with `losetup -f`, nothing of lane C's touched).
Binaries executed in `chroot /m` (image node v18.19.1, image python 3.12.3).
No boot performed; no `|| true` proofs; no mocked agent output.

Headline: the relay path was broken in two places and is now proven end to
end. `repo:` commands resolved against the **state** dir, so every staged
command (including the `watch` agent itself) died with spawn-error ENOENT; and
`watchman.mjs --once` called `process.exit(0)` before its children finished,
leaving ghost runs (brief + spawn ledger line, no log, no result). Both are
fixed below. B5's proof ran on the image with the image's own binaries.

## B1. Capture every run — PROVEN + INSTALLED

Change (`agents/runtime.mjs`): `spawnAgent` now writes, for every run
(including refused and spawn-error runs):
`runs/<runId>/stdout.log` and `stderr.log` (one ISO-timestamped,
secret-redacted line per line, never truncated), the legacy `output.log`
(redacted, untruncated, kept for old readers), and `meta.json`
(`startTime/startEpochMs/endTime/endEpochMs/durationMs/exitCode/signal/error/refused`).
Redaction replaces any env value whose name looks like a key
(KEY/TOKEN/SECRET/PASSWORD/PRIVATE/BEARER/SESSION/COOKIE/AUTH, length ≥ 8)
plus `sk-…`, `gh[pousr]_…`, `xox[bpas]-…`, `Bearer …` shapes. A failing run
gets a final loud line (`run failed: exit 3 signal null after 37ms`), so a
quiet death still says why. `refused` joined the reconciler's terminal set —
a recovery pass no longer marks a refused run `orphaned`.

Command + output (repo, `SPARK_API_KEY=sk-test-secret-value-12345` set):
`spawnAgent({command: [node, -e, log key + warn + …]})` →
`stdout.log` shows `hello [REDACTED]` + `run finished: exit 0 in 37ms`;
`meta.json` carries start/end/duration/exit; a forced exit-3 run logs
`run failed: exit 3 signal null after 37ms`; a budget refusal writes
`run refused before spawn: budget-cost-cap (estimate 5, cap 0.5)` plus meta.
Redaction check: `sk-live-…` value and `sk-fake-…` shape both read
`[REDACTED]` (2 REDACTED lines, 0 leaks).

INSTALLED: `/usr/share/metaos/agent/agents/runtime.mjs`
md5 `5e4f45c26e11b70061e6a815e4acfc26` (== repo).

## B2. metaosd read API — PROVEN + INSTALLED

Change (`os-build/iso/payload-agent/metaosd.mjs`): new read-only routes,
loopback-only as before, no secrets (logs redacted at write; person-typed
`orders` redacted shape-wise on the way out):
`GET /runs?agent=&limit=` (newest first, agent/start/end/duration/exit/refused/orders-snippet),
`GET /runs/<id>?n=&full=` (agent, orders, lane, meta, exit, matching
`jobs/*.result.json`, ledger tail, stdout/stderr tails),
`GET /ledger?n=` (relay `watchman.jsonl` tail; `?run=` keeps the old per-run
behavior). Kept `/status` and `/agents` shapes (same keys;
`proof_session.sh` checks `stateDir`/`queueUrl`/`agents`) and added only
`draftReason` to agent entries. Also: submit mints the job id server-side and
returns `{ok, id, agent, …}` so the console can track the run; new
`POST /resume` removes `stop/<agent>.STOP`. `METAOS_AGENT_SHARE` is honored
alongside `METAOS_AGENT_DIR` (the login hook and `meta-ask.py` use SHARE).

Command + output (image binaries, throwaway board): `GET /runs/<id>` →
200, `exit: {code: 0, signal: null}`, stdout tail with the two timestamped
lines, ledger events `spawn,exit`, result `{id: b5watch, code: 0}`;
`GET /status` keys `v,at,stateDir,stateDirExists,agentDir,agentDirFound,queueUrl,halted,jobFiles,heartbeat,notices`;
`GET /agents` → `ok: true, live: 16, drafts: 7`.

INSTALLED: `/opt/face/metaosd.mjs` md5 `7a02da51d8e26dd6212438efbfa60157` (== repo).

## B3. agents.html becomes a console — PROVEN + INSTALLED

Change (`os-build/face/agents.html`, full rewrite): every panel reads
18940 — agents (with draft reason + halt/resume buttons), board (`/jobs`
plus halted list), runs (`/runs?limit=30` with per-row state pills:
running / done / failed: exit N / killed / refused: reason), submit box
(`POST /jobs` through metaosd → `agents/submit.mjs`, shows the returned job
id and auto-selects the run it starts), and a run pane (`GET /runs/<id>`
polled every **2 s** while a run is selected, paused when none is —
chosen over SSE: one tiny interval, no port hammering; board/agents/status
refresh every 5 s). Draft rows show `draft — <draftReason>` and never enter
the submit select. No agent name, lane, or job appears from a hardcoded
array (verified by grep: `musica-studio|aegis-cycle|handsfree|imperium`
absent). A refused submit renders `refused: …`, never `accepted`.

Proof: exercised against a live metaosd (submit accepted with id,
draft submit refused with reason, halt wrote `watch.STOP`, resume removed
it, run log polled). INSTALLED: `/opt/face/agents.html` md5
`524cda525fab8ec1bf2ae75ce4a47119` (== repo).

## B4. The 7 drafts — PROVEN (kept draft, explicit refusal everywhere)

Choice per agent — **all 7 stay draft**:
`imperium-patrol` (lives outside this repo; no real command can be named),
`mathematics-researcher`, `chemistry-researcher`, `biology-researcher`,
`physics-researcher`, `hypothesis-generator`, `statistician`
(all: no program in this repo; a placeholder command would do the lane no
work). Reason: the repo's science duties that CAN read real records already
exist as live agents (archivist/director/critic/verifier/analyst/literature/
computational); the six remaining roles have no domain corpus on disk
(`hosted.py` documents exactly this), and a duty that invents findings
would be the forbidden stub-that-pretends-to-think. Math/stats/hypothesis
work over the same cycles would duplicate the live analyst/verifier or
invent science.

Refusal is explicit in all three surfaces: `meta-ask --list` names each
draft with its registry reason; a draft submit exits 1 with
`submit: <name> has no program yet (draft): <reason>; nothing would run`
(`agents/submit.mjs` now quotes `draftReason`); `GET /agents` carries
`draftReason` and the console renders it. `meta-ask --list` output:
16 live, 7 drafts (matches registry 23 = 16 + 7).

## B5. End-to-end proof, offline, in a chroot on the image — PROVEN

Two defects found and fixed first (both pre-existing, both load-bearing):
1. `repo:` resolved against the state root → every staged command was
   ENOENT. `spawnAgent` takes `repoRoot` (default = payload inferred from
   `runtime.mjs`'s location); `watchman.mjs` passes the payload root
   (`dirname(HERE)` = repo checkout, or `/usr/share/metaos/agent` in the
   image). Tests pass `root` only, so their behavior is unchanged.
2. `--once` exited before children finished (ghost runs). It now awaits
   spawned runs before exit; the daemon path is untouched. The nested pass
   intentionally keeps the payload dir as its root (it must not share the
   state ledger, or reconcile would resurrect live runs into a respawn
   chain); its log names the dir it watched — real output, no mock.

Commands (all inside docker, all image binaries via `chroot /m`):
`meta-ask --root /tmp/e2e-b5b "prove the relay runs end to end on the image" --agent watch --id b5watch` →
`asked watch… job b5watch is on the board` (+ honest `queue 8935 not answering` warning, job still written);
`watchman.mjs --root /tmp/e2e-b5b --once` → exit 0;
`runs/watch-mw0n8py9/stdout.log`:
```
2026-11-03T12:08:02.989Z relay-watchman: watching /usr/share/metaos/agent/agents/jobs
2026-11-03T12:08:02.995Z run finished: exit 0 in 81ms
```
result `{"id":"b5watch","agent":"watch","run":"watch-mw0n8py9","code":0,…}`;
`curl 127.0.0.1:18940/runs/watch-mw0n8py9` → 200 with run/agent/exit/orders/stdout/ledger(`spawn,exit`)/result.
Cleanup: test `.job.json` + `.result.json` deleted, nested payload
footprints (`agents/jobs`, heartbeat/state/ledger) removed, state dirs
removed — board empty, verified (`(absent, good)` × 2).

INSTALLED: `agents/watchman.mjs` md5 `3e4c6ce40e0bd83e99a5c7948f7aa59f`,
`agents/submit.mjs` md5 `733801f20f2f8dd6f4399b37532dd728`,
`/usr/local/bin/meta-ask` md5 `31a4b20a4f88aa4dbb4c42cf510bee2e` (all == repo).

## B6. Relay at login — PROVEN + INSTALLED

Verified in the image: `oc2-watchman.service` is a real user unit
(`ExecStart=/usr/bin/node /usr/share/metaos/agent/agents/watchman.mjs --root %h/.local/state/oc2-agent`,
`Restart=on-failure`), enabled via
`/etc/systemd/user/default.target.wants/oc2-watchman.service` (resolves);
login hook `UNITS` includes `oc2-watchman.service`; `oc2-health.service`
ships `META_AGENT_WATCHMAN_RESTART=systemctl --user restart oc2-watchman.service`;
probe `BEAT_REL = .local/state/oc2-agent/watchman.heartbeat.json`
(stale-after 300 s), absent beat = `absent` (not failure) by design.
Enable-link resolution, all OK (7/7):
`oc2-queue/trio/patrol/watchman/metaosd` services + `oc2-patrol/health` timers.
Stale→restart wiring proven with the image probe: a 600 s-old beat yields
`watchman: fail (heartbeat 600s old)`, `restart-watchman: pass (exit 0)`,
probe exit 1 — the row, not silence.
INSTALLED: created the missing enable link
`/etc/systemd/user/default.target.wants/metaosd.service → /usr/lib/systemd/user/metaosd.service`
in the image (provision-all step 7 writes it to the wrong wants dir with the
build-host path baked in — repo file not mine to edit; flagged for the owner).

## B7. No regressed semantics — PARTIAL (2 pre-existing env failures)

Budget ceiling, halt-holds-work, retry-once, proposal rules untouched
(`runtime.mjs` adds files/events only; `reconcileRuns` gained `refused` as
terminal, a fix, not a semantic change). Relay suites after the change:
`agents-runtime` + `agents-runtime-failures` + `agents-code100`: 28/28 pass;
watchman × 4 suites: 15/15 pass; r11 + memory-runtime + restart + jobs × 2:
36/36 pass. Python health suite: 16/16 OK.
Required command `node --test agents/*.test.mjs`:
`tests 15, suites 3, pass 13, fail 2` — the 2 failures are pre-existing
Docker-Desktop environment issues, present before this lane's first edit and
in a file this lane did not touch (`agents/sandbox.mjs`): (1) `--network none`
still exposes the host's net interfaces here (proven: bare
`docker run --rm --network none … ls /sys/class/net` lists
`bonding_masters erspan0 …` instead of `lo`), (2) the 5 s `sleep 60` kill
took 60 s. The suite's
...[truncated 1587 chars]