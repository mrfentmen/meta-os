# OPENCODE 2 — 300 TASKS (the ISO agent-runtime lane, Phase 2)

Owner: OpenCode 2. Branch: your lane branch (never push main; Pax merges).
Status file: keep your own section log; UNPROVEN/BLOCKED named, never hidden.
This list is the ISO-integration phase and SUPERSEDES nothing from
`os-build/OPENCODE2_TASKS_500.md` — that work stands merged; this is what
ships it inside MetaOS 1.0.

START ORDER: §1 packaging first, then §2 autostart, then §3–§7 live proofs
in numeric order, §9 cross-check one per session alongside everything else.
A section blocked on another lane (Goose runner = Buffy, base image =
Hana/Carrier) is recorded BLOCKED with the missing piece named, and you
move on — never idle, never wait, never padded.

KEY RULE: the ONLY model key path is the runtime env on the target
machine, read into the environment at service start. Never print it,
never log it, never commit it. Log an outage once, work offline items,
never retry-loop.

FENCES (obey in every task):
- No web-facing features beyond localhost. The agent subscriber binds
  127.0.0.1 only. No non-loopback URL is ever contacted by your code.
- No mock results presented as live. Every receipt is a real run or it
  is labelled SIMULATED/STUB with the reason.
- No padded counts. Every number comes from the command the proof names.
- Every proof is a committed file. Uncommitted = not done.
- BLOCKED is a verdict with an owner and a reason, never an excuse to stop.

## §1 Runtime packaging (OC2B-001..OC2B-025)

- **OC2B-001** Inventory every Python module the agent runtime needs:
  server/queue/*.py, models, crew, patrol, queue_service, livecams,
  guardrail deps. Proof: os-build/logs/OC2B-runtime-inventory.md.
- **OC2B-002** Record the exact Python version + pip package set the
  runtime is verified against on the build host. Proof:
  os-build/logs/OC2B-runtime-pins.txt with versions.
- **OC2B-003** Write the install manifest: each file, its source path in
  the repo, its destination under /usr/share/metaos/. Proof:
  os-build/logs/OC2B-install-manifest.md.
- **OC2B-004** Confirm no runtime file imports anything outside the
  manifest + stdlib + pinned packages. Proof: the import scan output
  in os-build/logs/OC2B-import-scan.txt.
- **OC2B-005** Package the queue service entry point with an
  executable bit and a --help that exits 0. Proof:
  os-build/logs/OC2B-queue-entry.txt.
- **OC2B-006** Package the patrol entry point the same way.
  Proof: os-build/logs/OC2B-patrol-entry.txt.
- **OC2B-007** Package the trio_agent entry point the same way.
  Proof: os-build/logs/OC2B-trio-entry.txt.
- **OC2B-008** Package the livecams assess-one path with a --help.
  Proof: os-build/logs/OC2B-livecams-entry.txt.
- **OC2B-009** Record every config file the runtime reads at startup
  with defaults for each. Proof: os-build/logs/OC2B-runtime-config.md.
- **OC2B-010** Verify no config path is absolute to a developer home
  directory. Proof: the grep output in os-build/logs/OC2B-config-paths.txt.
- **OC2B-011** Write the data-directory contract: where receipts,
  ledgers, and caches live under /var/lib/metaos. Proof:
  os-build/logs/OC2B-datadir.md.
- **OC2B-012** Confirm the runtime creates its data dir if missing
  (or fails with a named error, never silently). Proof:
  os-build/logs/OC2B-datadir-test.txt.
- **OC2B-013** Record file permissions/ownership for every installed
  file. Proof: os-build/logs/OC2B-permissions.txt.
- **OC2B-014** Verify no installed file is world-writable.
  Proof: os-build/logs/OC2B-perms-scan.txt.
- **OC2B-015** List every Python package dependency with license.
  Proof: os-build/logs/OC2B-licenses.md.
- **OC2B-016** Confirm all licenses permit redistribution on an ISO.
  Proof: the license verdict per package in OC2B-licenses.md.
- **OC2B-017** Write the uninstall story: one command removes the
  runtime cleanly. Proof: os-build/logs/OC2B-uninstall.md.
- **OC2B-018** Test the install manifest against a scratch chroot or
  container (no VM needed). Proof: os-build/logs/OC2B-install-test.txt.
- **OC2B-019** Measure installed size on disk. Proof:
  os-build/logs/OC2B-install-size.txt with the du output.
- **OC2B-020** Record startup time of each entry point cold
  (time to first log line). Proof: os-build/logs/OC2B-startup-time.txt.
- **OC2B-021** Document the log locations and rotation policy.
  Proof: os-build/logs/OC2B-logging.md.
- **OC2B-022** Confirm logs contain no secrets at any level.
  Proof: the scan output in os-build/logs/OC2B-logscan.txt.
- **OC2B-023** Write the version-string contract (every component
  reports its version on --version). Proof:
  os-build/logs/OC2B-versions.txt.
- **OC2B-024** Record the rollback story: previous version restorable
  in one command. Proof: os-build/logs/OC2B-rollback.md.
- **OC2B-025** Commit the §1 artifacts. Proof: the commit sha recorded
  in your lane status.

## §2 Autostart + services (OC2B-026..OC2B-050)

- **OC2B-026** Write the XDG autostart entry for the queue service.
  Proof: os-build/logs/OC2B-autostart-queue.desktop.
- **OC2B-027** Write the autostart entry for the patrol daemon.
  Proof: os-build/logs/OC2B-autostart-patrol.desktop.
- **OC2B-028** Write the autostart entry for the agent status tray.
  Proof: os-build/logs/OC2B-autostart-tray.desktop.
- **OC2B-029** Confirm every autostart entry uses TryExec pointing at
  its real binary (degraded-off if missing, never a boot failure).
  Proof: os-build/logs/OC2B-tryexec-check.txt.
- **OC2B-030** Write the systemd user units as an alternative to
  XDG autostart, disabled by default. Proof:
  os-build/logs/OC2B-systemd-units.md.
- **OC2B-031** Record the start order and dependencies between
  services. Proof: os-build/logs/OC2B-service-order.md.
- **OC2B-032** Define the health-check endpoint/contract per service.
  Proof: os-build/logs/OC2B-health-contract.md.
- **OC2B-033** Write the watchdog: restarts a dead service, logs
  every restart with cause. Proof: os-build/logs/OC2B-watchdog.md.
- **OC2B-034** Prove the watchdog never restart-loops: max restarts
  then a named BLOCKED state. Proof: os-build/logs/OC2B-watchdog-cap.txt.
- **OC2B-035** Record resource limits per service (memory/CPU).
  Proof: os-build/logs/OC2B-limits.md.
- **OC2B-036** Verify a killed -9 service is detected within the
  watchdog interval. Proof: os-build/logs/OC2B-watchdog-kill.txt.
- **OC2B-037** Verify a hung (not dead) service is detected via the
  health check, not just the process table. Proof:
  os-build/logs/OC2B-watchdog-hang.txt.
- **OC2B-038** Record the stop story: one command stops everything
  cleanly. Proof: os-build/logs/OC2B-stop.md.
- **OC2B-039** Record the log location for every service.
  Proof: os-build/logs/OC2B-service-logs.md.
- **OC2B-040** Confirm a service never writes outside its data dir
  and log path. Proof: os-build/logs/OC2B-write-scope.txt.
- **OC2B-041** Write the first-boot behaviour: services start,
  no setup wizard blocks the desktop. Proof:
  os-build/logs/OC2B-firstboot.md.
- **OC2B-042** Write the no-network behaviour: everything degrades
  to staged/offline honestly. Proof: os-build/logs/OC2B-offline.md.
- **OC2B-043** Record the upgrade behaviour: new version picks up
  old ledgers without loss. Proof: os-build/logs/OC2B-upgrade.md.
- **OC2B-044** Verify two services never bind the same port.
  Proof: os-build/logs/OC2B-ports.txt with the bind table.
- **OC2B-045** Confirm every bound port is localhost-only.
  Proof: the ss/netstat output in OC2B-ports.txt.
- **OC2B-046** Write the service status summary command (one line
  per service: up/down/BLOCKED). Proof:
  os-build/logs/OC2B-status-cmd.txt.
- **OC2B-047** Record the exact autostart fileset for the ISO
  provision step. Proof: os-build/logs/OC2B-autostart-manifest.md.
- **OC2B-048** Hand the autostart manifest to the ISO lane in
  writing (path + install target per file). Proof: the handoff note
  in os-build/logs/OC2B-handoff-autostart.md.
- **OC2B-049** If any autostart target path is owned by another
  lane's package, record the dependency instead of writing the
  file. Proof: the dependency note or the files, either is honest.
- **OC2B-050** Commit the §2 artifacts. Proof: the commit sha
  recorded in your lane status.

## §3 Queue service live verification (OC2B-051..OC2B-075)

- **OC2B-051** Run the full queue suite on the final packaged tree.
  Proof: os-build/logs/OC2B-queue-suite.txt.
- **OC2B-052** Record pass/fail/skip counts against the §9 baseline
  (296/296). Proof: the count line in OC2B-queue-suite.txt.
- **OC2B-053** Reconcile every delta vs baseline by name.
  Proof: os-build/logs/OC2B-queue-diff.md.
- **OC2B-054** Run one end-to-end job through the packaged queue
  service (submit → process → receipt). Proof:
  os-build/logs/OC2B-queue-e2e.json.
- **OC2B-055** Verify the receipt names the model, the input hash,
  and the timestamp. Proof: the receipt quoted in OC2B-queue-e2e.json.
- **OC2B-056** Run 10 varied jobs and confirm all 10 receipt.
  Proof: os-build/logs/OC2B-queue-10.jsonl.
- **OC2B-057** Confirm a malformed job is refused with a named
  error, never a crash. Proof: os-build/logs/OC2B-queue-bad.txt.
- **OC2B-058** Measure per-job latency distribution (min/median/max).
  Proof: os-build/logs/OC2B-queue-latency.txt.
- **OC2B-059** Run the queue for 30 minutes unattended and count
  jobs/receipts/errors. Proof: os-build/logs/OC2B-queue-soak.txt.
- **OC2B-060** Confirm zero unreceipted jobs in the soak.
  Proof: the reconciliation in OC2B-queue-soak.txt.
- **OC2B-061** Verify the queue survives a service restart with
  no job loss. Proof: os-build/logs/OC2B-queue-restart.txt.
- **OC2B-062** Verify the queue survives a machine reboot with
  no job loss. Proof: os-build/logs/OC2B-queue-reboot.txt.
- **OC2B-063** Record the max queue depth tested and behaviour at
  the cap. Proof: os-build/logs/OC2B-queue-depth.txt.
- **OC2B-064** Confirm backpressure: submitters are told to wait,
  not silently dropped. Proof: os-build/logs/OC2B-queue-backpressure.txt.
- **OC2B-065** Run the queue with no model key present and confirm
  honest offline behaviour. Proof: os-build/logs/OC2B-queue-nokey.txt.
- **OC2B-066** Confirm no key material appears in any queue log.
  Proof: the scan in os-build/logs/OC2B-queue-logscan.txt.
- **OC2B-067** Record the queue's disk usage after 1000 jobs.
  Proof: os-build/logs/OC2B-queue-disk.txt.
- **OC2B-068** Write the queue operator doc: start/stop/inspect/
  drain/retry. Proof: os-build/logs/OC2B-queue-ops.md.
- **OC2B-069** Verify drain-then-stop loses nothing.
  Proof: os-build/logs/OC2B-queue-drain.txt.
- **OC2B-070** Verify a poison job (always-failing) is quarantined
  after N tries, not retried forever. Proof:
  os-build/logs/OC2B-queue-poison.txt.
- **OC2B-071** Record the quarantine review procedure.
  Proof: os-build/logs/OC2B-queue-quarantine.md.
- **OC2B-072** Confirm receipts are append-only (no edits, no
  deletes in normal operation). Proof:
  os-build/logs/OC2B-queue-appendonly.txt.
- **OC2B-073** Write the queue section verdict: READY or the named
  rows that are not. Proof: the verdict block in your lane status.
- **OC2B-074** File every queue defect found with repro steps.
  Proof: os-build/logs/OC2B-queue-defects.md (empty is a result).
- **OC2B-075** Commit the §3 artifacts. Proof: the commit sha
  recorded in your lane status.

## §4 Patrol, crew and watchdog daemons (OC2B-076..OC2B-100)

- **OC2B-076** Run one patrol cycle on the packaged tree.
  Proof: os-build/logs/OC2B-patrol-once.json.
- **OC2B-077** Verify the patrol timeline has patrol→review→judge→response
  in order. Proof: the timeline in OC2B-patrol-once.json.
- **OC2B-078** Run the patrol on its timer for 1 hour, count cycles.
  Proof: os-build/logs/OC2B-patrol-hour.txt.
- **OC2B-079** Confirm every cycle produced a receipt or a named
  skip reason. Proof: the reconciliation in OC2B-patrol-hour.txt.
- **OC2B-080** Run the crew pipeline on a staged incident.
  Proof: os-build/logs/OC2B-crew-staged.json.
- **OC2B-081** Confirm dispatch in the staged run hit ONLY the
  loopback endpoint. Proof: the dispatch URL in OC2B-crew-staged.json.
- **OC2B-082** Run the failure-honesty drill: withhold the key,
  confirm the error step names it. Proof:
  os-build/logs/OC2B-crew-nokey.txt.
- **OC2B-083** Confirm a real emergency number never appears in
  any code path. Proof: the grep in os-build/logs/OC2B-noreal.txt.
- **OC2B-084** Record the watchdog's restart policy per daemon.
  Proof: os-build/logs/OC2B-daemon-watch.md.
- **OC2B-085** Kill each daemon once and confirm restart + receipt.
  Proof: os-build/logs/OC2B-daemon-kill.txt.
- **OC2B-086** Run all daemons together for 1 hour, count restarts.
  Proof: os-build/logs/OC2B-daemons-hour.txt.
- **OC2B-087** Confirm zero unlogged restarts in the hour.
  Proof: the reconciliation in OC2B-daemons-hour.txt.
- **OC2B-088** Record CPU/memory per daemon at idle and busy.
  Proof: os-build/logs/OC2B-daemon-resources.txt.
- **OC2B-089** Confirm no daemon exceeds its budget in the hour.
  Proof: the verdict in OC2B-daemon-resources.txt.
- **OC2B-090** Verify log rotation works under sustained output.
  Proof: os-build/logs/OC2B-daemon-logrotate.txt.
- **OC2B-091** Write the daemon operator doc.
  Proof: os-build/logs/OC2B-daemon-ops.md.
- **OC2B-092** Record the alert path when a daemon stays down
  past its restart cap. Proof: os-build/logs/OC2B-daemon-alert.md.
- **OC2B-093** Confirm the alert names the daemon, the cause, and
  the owner. Proof: a sample alert in OC2B-daemon-alert.md.
- **OC2B-094** Run the 10-batch patrol scenario from §13's lineage
  and confirm all-baseline again. Proof:
  os-build/logs/OC2B-patrol-10batch.json.
- **OC2B-095** Record any deviation vs the §13 baseline.
  Proof: os-build/logs/OC2B-patrol-delta.md (none is a result).
- **OC2B-096** Re-run the STAGED incident path end to end and
  confirm sim- receipt format unchanged. Proof:
  os-build/logs/OC2B-staged-rerun.json.
- **OC2B-097** Re-run the cleared/inconclusive/yellow paths and
  confirm zero dispatch each. Proof:
  os-build/logs/OC2B-quiet-paths.json.
- **OC2B-098** Write the §4 verdict. Proof: the verdict block in
  your lane status.
- **OC2B-099** File every daemon defect found with repro steps.
  Proof: os-build/logs/OC2B-daemon-defects.md (empty is a result).
- **OC2B-100** Commit the §4 artifacts. Proof: the commit sha
  recorded in your lane status.

## §5 Model endpoints, receipts, guardrail (OC2B-101..OC2B-125)

- **OC2B-101** List every model the submission may name, with the
  receipt that proves each. Proof: os-build/logs/OC2B-models.md.
- **OC2B-102** Re-run one live chat call per named model and keep
  the receipts. Proof: os-build/logs/OC2B-models-live.jsonl.
- **OC2B-103** Confirm spend incremented on the guardrail for each.
  Proof: os-build/logs/OC2B-spend-live.txt.
- **OC2B-104** Reproduce the reasoning-token starvation finding
  (Wonder/ Spark long-context) on the current tree. Proof:
  os-build/logs/OC2B-token-starve.txt.
- **OC2B-105** Confirm the fallbacks still engage when starved.
  Proof: os-build/logs/OC2B-fallbacks.txt.
- **OC2B-106** Record the guardrail totals and the cap.
  Proof: os-build/logs/OC2B-guardrail.txt.
- **OC2B-107** Confirm no call exceeds its per-call budget.
  Proof: the audit in OC2B-guardrail.txt.
- **OC2B-108** Run with the key revoked and confirm every path
  degrades honestly. Proof: os-build/logs/OC2B-key-revoked.txt.
- **OC2B-109** Confirm revocation produces zero partial receipts.
  Proof: the check in OC2B-key-revoked.txt.
- **OC2B-110** Record the model endpoint URLs allowlisted in code.
  Proof: os-build/logs/OC2B-allowlist.txt.
- **OC2B-111** Confirm no non-allowlisted host is contacted in any
  test or live run. Proof: the egress audit in OC2B-allowlist.txt.
- **OC2B-112** Verify every receipt carries model, input hash,
  timestamp, spend. Proof: the schema check in
  os-build/logs/OC2B-receipt-schema.txt.
- **OC2B-113** Reject one malformed receipt and record why.
  Proof: os-build/logs/OC2B-receipt-reject.txt.
- **OC2B-114** Record receipt retention and rotation policy.
  Proof: os-build/logs/OC2B-receipt-retention.md.
- **OC2B-115** Confirm receipts survive reboot and upgrade.
  Proof: os-build/logs/OC2B-receipt-durable.txt.
- **OC2B-116** Write the model ops doc: add/remove/rotate models.
  Proof: os-build/logs/OC2B-models-ops.md.
- **OC2B-117** Record what happens when a model is retired
  mid-session. Proof: os-build/logs/OC2B-model-retire.txt.
- **OC2B-118** Confirm retired-model jobs fail named, never hang.
  Proof: the test in OC2B-model-retire.txt.
- **OC2B-119** Reconcile total spend across all sections.
  Proof: os-build/logs/OC2B-spend-total.txt.
- **OC2B-120** Label the total an estimate at Spark rates.
  Proof: the label line in OC2B-spend-total.txt.
- **OC2B-121** Record the spend per lane/section.
  Proof: the breakdown in OC2B-spend-total.txt.
- **OC2B-122** Confirm no spend is unattributable.
  Proof: the reconciliation in OC2B-spend-total.txt.
- **OC2B-123** Write the §5 verdict. Proof: the verdict block in
  your lane status.
- **OC2B-124** File every model-layer defect with repro steps.
  Proof: os-build/logs/OC2B-model-defects.md (empty is a result).
- **OC2B-125** Commit the §5 artifacts. Proof: the commit sha
  recorded in your lane status.

## §6 Livecams integration (OC2B-126..OC2B-150)

- **OC2B-126** Re-run the 975-list on the packaged tree.
  Proof: os-build/logs/OC2B-livecams-list.txt.
- **OC2B-127** Re-run the 7 assessed readings over 5 areas.
  Proof: os-build/logs/OC2B-livecams-7.json.
- **OC2B-128** Confirm all 7 are still baseline honestly.
  Proof: the verdicts in OC2B-livecams-7.json.
- **OC2B-129** Confirm the count-3 snapshot set reproduces.
  Proof: os-build/logs/OC2B-livecams-count3.txt.
- **OC2B-130** Re-run the name filter determinism check.
  Proof: os-build/logs/OC2B-livecams-filter.txt.
- **OC2B-131** Re-run both refusals and confirm they stay loud.
  Proof: os-build/logs/OC2B-livecams-refusals.txt.
- **OC2B-132** Re-run the 12/12 offline tests.
  Proof: os-build/logs/OC2B-livecams-offline.txt.
- **OC2B-133** Record the fetcher wart status (URLError vs
  LiveCamError) and any fix. Proof:
  os-build/logs/OC2B-livecams-wart.md.
- **OC2B-134** Run one live assess-one and keep the frame+reading.
  Proof: os-build/captures/oc2b-live-frame.jpg +
  os-build/logs/OC2B-livecams-live.json.
- **OC2B-135** Confirm the reading names a real model.
  Proof: the model field in OC2B-livecams-live.json.
- **OC2B-136** Record the no-camera fallback behaviour.
  Proof: os-build/logs/OC2B-livecams-nocam.md.
- **OC2B-137** Confirm zero fabricated frames in all runs.
  Proof: the attestation in os-build/logs/OC2B-livecams-honest.md.
- **OC2B-138** Record camera-area coverage (areas x divisions).
  Proof: os-build/logs/OC2B-livecams-coverage.md.
- **OC2B-139** Confirm the medicus wording stays clean.
  Proof: the wording check in OC2B-livecams-coverage.md.
- **OC2B-140** Write the livecam operator doc.
  Proof: os-build/logs/OC2B-livecams-ops.md.
- **OC2B-141** Record the frame retention policy.
  Proof: os-build/logs/OC2B-livecams-retention.md.
- **OC2B-142** Confirm retained frames carry timestamps.
  Proof: the check in OC2B-livecams-retention.md.
- **OC2B-143** Run the full livecam path on a second area.
  Proof: os-build/logs/OC2B-livecams-area2.json.
- **OC2B-144** Compare the two areas' verdict shapes.
  Proof: os-build/logs/OC2B-livecams-areas.md.
- **OC2B-145** Record any area-specific caveats.
  Proof: the caveats in OC2B-livecams-areas.md.
- **OC2B-146** Confirm no area is hardcoded as always-baseline.
  Proof: the code grep in os-build/logs/OC2B-livecams-nohardcode.txt.
- **OC2B-147** Write the §6 verdict. Proof: the verdict block in
  your lane status.
- **OC2B-148** File every livecam defect with repro steps.
  Proof: os-build/logs/OC2B-livecams-defects.md (empty is a result).
- **OC2B-149** Hand the autostart-relevant livecam bits to §2's
  manifest if missing. Proof: the handoff or the no-op note.
- **OC2B-150** Commit the §6 artifacts. Proof: the commit sha
  recorded in your lane status.

## §7 Goose runtime (OC2B-151..OC2B-175)

- **OC2B-151** Inventory the Goose services and their entry points.
  Proof: os-build/logs/OC2B-goose-inventory.md.
- **OC2B-152** Check whether Buffy's runner fix has landed on main.
  Proof: the branch/commit check in OC2B-goose-inventory.md.
- **OC2B-153** If the fix HAS landed: run the full gate-2 suite and
  record results. Proof: os-build/logs/OC2B-goose-gate2.txt.
- **OC2B-154** If the fix has NOT landed: re-file the blocker in
  one line and skip to OC2B-165. Proof: the BLOCKED line in your
  lane status.
- **OC2B-155** On the fixed runner: reproduce the 6/7 pass state.
  Proof: os-build/logs/OC2B-goose-run1.txt.
- **OC2B-156** Run the updater path that previously aborted.
  Proof: os-build/logs/OC2B-goose-updater.txt.
- **OC2B-157** Record the updater verdict honestly.
  Proof: the verdict in OC2B-goose-updater.txt.
- **OC2B-158** Run the core5 checks. Proof:
  os-build/logs/OC2B-goose-core5.txt.
- **OC2B-159** Run the full library root check.
  Proof: os-build/logs/OC2B-goose-root.txt.
- **OC2B-160** Re-file or close D1/D2/D3 with evidence.
  Proof: os-build/logs/OC2B-goose-defects.md.
- **OC2B-161** Run one Goose service end to end if the runner
  allows. Proof: os-build/logs/OC2B-goose-e2e.json.
- **OC2B-162** Record the per-service RUN evidence or the
  kernel-link ceiling honestly. Proof:
  os-build/logs/OC2B-goose-run-evidence.md.
- **OC2B-163** Package Goose services that run; document the rest
  as blocked. Proof: os-build/logs/OC2B-goose-pack.md.
- **OC2B-164** Write the Goose autostart entries for the ones
  that run. Proof: os-build/logs/OC2B-goose-autostart.md.
- **OC2B-165** Document the Goose operational boundary: what runs,
  what doesn't, and why. Proof: os-build/logs/OC2B-goose-boundary.md.
- **OC2B-166** Confirm no Goose test needs kernel syscall externs
  on the link path it ships. Proof:
  os-build/logs/OC2B-goose-link.txt.
- **OC2B-167** Record the Goose toolchain versions.
  Proof: os-build/logs/OC2B-goose-toolchain.txt.
- **OC2B-168** Write the Goose operator doc.
  Proof: os-build/logs/OC2B-goose-ops.md.
- **OC2B-169** Record the Goose log locations.
  Proof: os-build/logs/OC2B-goose-logs.md.
- **OC2B-170** Confirm Goose logs contain no secrets.
  Proof: the scan in os-build/logs/OC2B-goose-logscan.txt.
- **OC2B-171** Record Goose resource usage.
  Proof: os-build/logs/OC2B-goose-resources.txt.
- **OC2B-172** Write the §7 verdict (RUN or BLOCKED with owner).
  Proof: the verdict block in your lane status.
- **OC2B-173** If BLOCKED: list exactly what unblocks it and who
  owns each piece. Proof: os-build/logs/OC2B-goose-unblock.md.
- **OC2B-174** If RUN: write the regression screen for the next
  runner change. Proof: os-build/logs/OC2B-goose-regress.md.
- **OC2B-175** Commit the §7 artifacts. Proof: the commit sha
  recorded in your lane status.

## §8 Lobster glue (OC2B-176..OC2B-200)

- **OC2B-176** Inventory the Lobster scripts and what each does.
  Proof: os-build/logs/OC2B-lobster-inventory.md.
- **OC2B-177** Identify the Lobster runtime/interpreter.
  Proof: the runtime path in OC2B-lobster-inventory.md.
- **OC2B-178** Run hello.lobster and keep the output.
  Proof: os-build/logs/OC2B-lobster-hello.txt.
- **OC2B-179** Run agent-call and bus-send/bus-recv round trip.
  Proof: os-build/logs/OC2B-lobster-bus.txt.
- **OC2B-180** Run the budget script. Proof:
  os-build/logs/OC2B-lobster-budget.txt.
- **OC2B-181** Reproduce the failures/ directory cases.
  Proof: os-build/logs/OC2B-lobster-failures.txt.
- **OC2B-182** For each failing case: expected-fail or defect.
  Proof: os-build/logs/OC2B-lobster-triage.md.
- **OC2B-183** Package Lobster glue the agent runtime actually
  uses. Proof: os-build/logs/OC2B-lobster-pack.md.
- **OC2B-184** Leave the rest as documented-not-shipped.
  Proof: the list in OC2B-lobster-pack.md.
- **OC2B-185** Write the autostart entries for shipped glue.
  Proof: os-build/logs/OC2B-lobster-autostart.md.
- **OC2B-186** Confirm Lobster glue never blocks desktop boot.
  Proof: os-build/logs/OC2B-lobster-noblock.txt.
- **OC2B-187** Record Lobster log locations.
  Proof: os-build/logs/OC2B-lobster-logs.md.
- **OC2B-188** Confirm Lobster logs contain no secrets.
  Proof: the scan in os-build/logs/OC2B-lobster-logscan.txt.
- **OC2B-189** Record Lobster resource usage.
  Proof: os-build/logs/OC2B-lobster-resources.txt.
- **OC2B-190** Write the Lobster operator doc.
  Proof: os-build/logs/OC2B-lobster-ops.md.
- **OC2B-191** Record the Lobster version pin.
  Proof: os-build/logs/OC2B-lobster-version.txt.
- **OC2B-192** Confirm the pin exists in the ISO package set.
  Proof: the pin check in OC2B-lobster-version.txt.
- **OC2B-193** Write the §8 verdict. Proof: the verdict block in
  your lane status.
- **OC2B-194** File every Lobster defect with repro steps.
  Proof: os-build/logs/OC2B-lobster-defects.md (empty is a result).
- **OC2B-195** Hand autostart-relevant glue to §2's manifest if
  missing. Proof: the handoff or the no-op note.
- **OC2B-196** If the Lobster runtime is unavailable: record
  BLOCKED with the provider and move on. Proof: the BLOCKED line.
- **OC2B-197** Document the Lobster operational boundary.
  Proof: os-build/logs/OC2B-lobster-boundary.md.
- **OC2B-198** Reconcile Lobster files vs the failures/ dir.
  Proof: os-build/logs/OC2B-lobster-reconcile.md.
- **OC2B-199** Record what "done" means for Lobster in 1.0.
  Proof: the definition in your lane status.
- **OC2B-200** Commit the §8 artifacts. Proof: the commit sha
  recorded in your lane status.

## §9 Cross-check lane (OC2B-201..OC2B-225)

- **OC2B-201** Reproduce ONE OpenCode 1 proof from a clean
  checkout: the §11 film (ffprobe 180.000s + sha).
  Proof: os-build/logs/OC2B-xcheck-film.txt.
- **OC2B-202** File agree or disagree with evidence.
  Proof: the verdict in OC2B-xcheck-film.txt.
- **OC2B-203** Check CAPTURE_NOTES.md line by line against the
  film and records. Proof: os-build/logs/OC2B-xcheck-notes.md.
- **OC2B-204** File agree/disagree per line.
  Proof: the per-line verdicts in OC2B-xcheck-notes.md.
- **OC2B-205** Reproduce ONE §1 baseline assertion on a clean
  clone (gate GREEN). Proof: os-build/logs/OC2B-xcheck-gate.txt.
- **OC2B-206** File agree/disagree. Proof: OC2B-xcheck-gate.txt.
- **OC2B-207** Reproduce ONE §9 live receipt path offline.
  Proof: os-build/logs/OC2B-xcheck-model.txt.
- **OC2B-208** File agree/disagree. Proof: OC2B-xcheck-model.txt.
- **OC2B-209** Reproduce ONE §14 suite result.
  Proof: os-build/logs/OC2B-xcheck-science.txt.
- **OC2B-210** File agree/disagree. Proof: OC2B-xcheck-science.txt.
- **OC2B-211** Reproduce ONE §17 count (2071/2015/56).
  Proof: os-build/logs/OC2B-xcheck-native.txt.
- **OC2B-212** File agree/disagree. Proof: OC2B-xcheck-native.txt.
- **OC2B-213** Reproduce the MetaOS ISO boot proof (this lane's
  own future artifact — placeholder until it exists).
  Proof: os-build/logs/OC2B-xcheck-iso.md.
- **OC2B-214** File agree/disagree when the ISO exists.
  Proof: OC2B-xcheck-iso.md.
- **OC2B-215** Record the cross-check cadence (one per session).
  Proof: the log in os-build/logs/OC2B-xcheck-log.md.
- **OC2B-216** Confirm no cross-check ever mutated the proof.
  Proof: the read-only attestation in OC2B-xcheck-log.md.
- **OC2B-217** File a disagreement playbook: what happens on
  DISAGREE. Proof: os-build/logs/OC2B-disagree-playbook.md.
- **OC2B-218** Exercise the playbook once on a synthetic
  mismatch if no real one exists. Proof:
  os-build/logs/OC2B-disagree-drill.txt.
- **OC2B-219** Record cross-check coverage (which OC1 sections
  have been checked). Proof: os-build/logs/OC2B-xcheck-coverage.md.
- **OC2B-220** Prioritise unchecked high-value proofs next.
  Proof: the priority list in OC2B-xcheck-coverage.md.
- **OC2B-221** Confirm cross-checks never touch main.
  Proof: the branch attestation in OC2B-xcheck-log.md.
- **OC2B-222** Write the §9 verdict. Proof: the verdict block in
  your lane status.
- **OC2B-223** File every cross-check defect with evidence.
  Proof: os-build/logs/OC2B-xcheck-defects.md (empty is a result).
- **OC2B-224** Hand disagreements to Pax in writing.
  Proof: os-build/logs/OC2B-disagreements.md.
- **OC2B-225** Commit the §9 artifacts. Proof: the commit sha
  recorded in your lane status.

## §10 Agent status UI (OC2B-226..OC2B-250)

- **OC2B-226** Inventory the agent status surface (tray/widget).
  Proof: os-build/logs/OC2B-tray-inventory.md.
- **OC2B-227** Wire queue depth into the tray.
  Proof: os-build/logs/OC2B-tray-queue.txt.
- **OC2B-228** Wire daemon states into the tray.
  Proof: os-build/logs/OC2B-tray-daemons.txt.
- **OC2B-229** Wire guardrail spend into the tray.
  Proof: os-build/logs/OC2B-tray-spend.txt.
- **OC2B-230** Confirm the tray never shows a stale state.
  Proof: os-build/logs/OC2B-tray-fresh.txt.
- **OC2B-231** Confirm the tray never shows a model key.
  Proof: the scan in os-build/logs/OC2B-tray-nosecrets.txt.
- **OC2B-232** Record the tray refresh cadence.
  Proof: os-build/logs/OC2B-tray-cadence.md.
- **OC2B-233** Confirm the tray degrades when services are down.
  Proof: os-build/logs/OC2B-tray-degraded.txt.
- **OC2B-234** Write the tray autostart entry.
  Proof: os-build/logs/OC2B-tray-autostart.md.
- **OC2B-235** Confirm the tray starts on login with no setup.
  Proof: os-build/logs/OC2B-tray-login.txt.
- **OC2B-236** Record the tray's resource footprint.
  Proof: os-build/logs/OC2B-tray-resources.txt.
- **OC2B-237** Write the tray operator doc.
  Proof: os-build/logs/OC2B-tray-ops.md.
- **OC2B-238** Confirm clicking through opens the right log.
  Proof: os-build/logs/OC2B-tray-links.txt.
- **OC2B-239** Record the tray's error states.
  Proof: os-build/logs/OC2B-tray-errors.md.
- **OC2B-240** Confirm errors name the service and the fix.
  Proof: the samples in OC2B-tray-errors.md.
- **OC2B-241** Hand tray .desktop entries to the desktop lane
  in writing. Proof: os-build/logs/OC2B-tray-handoff.md.
- **OC2B-242** If the desktop lane owns the tray: record the
  handoff accepted. Proof: the acceptance note.
- **OC2B-243** If the desktop lane is unreachable: ship the
  tray entries yourself, documented. Proof: the entries +
  the note.
- **OC2B-244** Confirm the tray never blocks boot.
  Proof: os-build/logs/OC2B-tray-noblock.txt.
- **OC2B-245** Record the tray's offline behaviour.
  Proof: os-build/logs/OC2B-tray-offline.md.
- **OC2B-246** Write the §10 verdict. Proof: the verdict block
  in your lane status.
- **OC2B-247** File every tray defect with repro steps.
  Proof: os-build/logs/OC2B-tray-defects.md (empty is a result).
- **OC2B-248** Confirm the tray matches the theme (Meta blue,
  no foreign assets). Proof: os-build/logs/OC2B-tray-theme.txt.
- **OC2B-249** Record the tray's accessibility basics.
  Proof: os-build/logs/OC2B-tray-a11y.md.
- **OC2B-250** Commit the §10 artifacts. Proof: the commit sha
  recorded in your lane status.

## §11 Spend accounting + guardrails (OC2B-251..OC2B-275)

- **OC2B-251** Enumerate every spend source in the runtime.
  Proof: os-build/logs/OC2B-spend-sources.md.
- **OC2B-252** Confirm every source reports to the guardrail.
  Proof: os-build/logs/OC2B-spend-coverage.txt.
- **OC2B-253** Set the per-source caps. Proof:
  os-build/logs/OC2B-spend-caps.md.
- **OC2B-254** Confirm caps are enforced, not advisory.
  Proof: os-build/logs/OC2B-spend-enforced.txt.
- **OC2B-255** Record the cap-breach behaviour.
  Proof: os-build/logs/OC2B-spend-breach.md.
- **OC2B-256** Confirm breach behaviour is honest-stop, never
  silent-skip. Proof: the test in OC2B-spend-breach.md.
- **OC2B-257** Reconcile spend daily during the sprint.
  Proof: os-build/logs/OC2B-spend-daily.md.
- **OC2B-258** Confirm no spend is unattributable.
  Proof: the reconciliation in OC2B-spend-daily.md.
- **OC2B-259** Record the estimator calibration (Spark rates).
  Proof: os-build/logs/OC2B-spend-calibration.md.
- **OC2B-260** Label every total an estimate.
  Proof: the label audit in OC2B-spend-daily.md.
- **OC2B-261** Write the spend ops doc: check/raise/lower caps.
  Proof: os-build/logs/OC2B-spend-ops.md.
- **OC2B-262** Record who may raise caps (boss only).
  Proof: the rule in OC2B-spend-ops.md.
- **OC2B-263** Confirm a cap raise requires a logged decision.
  Proof: os-build/logs/OC2B-spend-raise.txt.
- **OC2B-264** Record the spend alert thresholds.
  Proof: os-build/logs/OC2B-spend-alerts.md.
- **OC2B-265** Confirm alerts fire before the cap, not after.
  Proof: the test in OC2B-spend-alerts.md.
- **OC2B-266** Record the alert delivery path.
  Proof: os-build/logs/OC2B-spend-delivery.md.
- **OC2B-267** Confirm alert delivery works with no models.
  Proof: the offline test in OC2B-spend-delivery.md.
- **OC2B-268** Write the §11 verdict. Proof: the verdict block
  in your lane status.
- **OC2B-269** File every guardrail defect with repro steps.
  Proof: os-build/logs/OC2B-guardrail-defects.md (empty is a result).
- **OC2B-270** Record the final sprint spend total.
  Proof: os-build/logs/OC2B-spend-final.txt.
- **OC2B-271** Attribute the total per section.
  Proof: the breakdown in OC2B-spend-final.txt.
- **OC2B-272** Confirm the total matches Pax's ledger within
  rounding. Proof: the reconciliation in OC2B-spend-final.txt.
- **OC2B-273** Record any spend disputes with evidence.
  Proof: os-build/logs/OC2B-spend-disputes.md (empty is a result).
- **OC2B-274** Hand the spend record to Milo's audit.
  Proof: os-build/logs/OC2B-spend-handoff.md.
- **OC2B-275** Commit the §11 artifacts. Proof: the commit sha
  recorded in your lane status.

## §12 Closeout + handoff (OC2B-276..OC2B-300)

- **OC2B-276** Re-run the full queue suite one final time.
  Proof: os-build/logs/OC2B-closeout-queue.txt.
- **OC2B-277** Re-run patrol once end to end.
  Proof: os-build/logs/OC2B-closeout-patrol.json.
- **OC2B-278** Re-run one live model call and keep the receipt.
  Proof: os-build/logs/OC2B-closeout-model.json.
- **OC2B-279** Re-run the offline suite fully.
  Proof: os-build/logs/OC2B-closeout-offline.txt.
- **OC2B-280** Inventory every proof file this list committed.
  Proof: os-build/logs/OC2B-proof-index.md.
- **OC2B-281** Verify every proof path in your status resolves.
  Proof: the check output in OC2B-proof-index.md.
- **OC2B-282** Write the handoff note to Pax: what is ready,
  what must NOT merge, merge order. Proof:
  os-build/logs/OC2B-handoff.md.
- **OC2B-283** List every UNPROVEN/BLOCKED row with owner.
  Proof: the list in OC2B-handoff.md.
- **OC2B-284** Record the honest readiness verdict: READY or
  the named rows that are not. Proof: the verdict in OC2B-handoff.md.
- **OC2B-285** Confirm no secrets in the branch.
  Proof: the scan in os-build/logs/OC2B-closeout-secrets.txt.
- **OC2B-286** Confirm no mock presented as live anywhere.
  Proof: the label audit in os-build/logs/OC2B-closeout-honest.md.
- **OC2B-287** Record the final gate state the runtime stands on.
  Proof: os-build/logs/OC2B-closeout-gate.txt.
- **OC2B-288** Confirm nothing in this lane touches main.
  Proof: the branch attestation in OC2B-handoff.md.
- **OC2B-289** Post build status to room 1 as things land.
  Proof: the post log in OC2B-handoff.md.
- **OC2B-290** Record where spare time went if any section
  finished early. Proof: the note in OC2B-handoff.md.
- **OC2B-291** Write the final status-file pass: every section
  DONE/UNPROVEN/BLOCKED with reasons. Proof: your completed
  lane status file.
- **OC2B-292** Verify the status file's every proof path resolves.
  Proof: the check output appended to OC2B-proof-index.md.
- **OC2B-293** Record the list's total live spend.
  Proof: os-build/logs/OC2B-spend-lane-total.txt.
- **OC2B-294** Record total lane wall-clock by section.
  Proof: os-build/logs/OC2B-time-table.md.
- **OC2B-295** Assemble the DEL-ONLY list for your lane.
  Proof: os-build/logs/OC2B-delonly.md.
- **OC2B-296** Write the timeline to the deadline with owners.
  Proof: os-build/logs/OC2B-timeline.md.
- **OC2B-297** Record the claim-clause map: PROVEN/UNPROVEN per
  clause with paths. Proof: os-build/logs/OC2B-clauses.md.
- **OC2B-298** For every UNPROVEN clause write the one-line
  reason. Proof: the reasons in OC2B-clauses.md.
- **OC2B-299** Final commit on your branch. Proof: the commit
  sha in your lane status.
- **OC2B-300** The last line of your status: what remains
  unproven in plain words. Proof: the final line.
