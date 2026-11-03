# Meta OS skills

**300 generated capability skills** plus the hand-written crew skills (`worker`, `relief`, `claimant`, `watchdog`, `quartermaster`, `archivist`) and the `fedora-hat` persona.

Generated from `_tools/catalog.py`; edit the catalog, then run
`python3 _tools/generate_catalog.py && python3 _tools/verify_catalog.py`.

### Hand-written crew skills (7)

[`worker`](./worker) · [`relief`](./relief) · [`claimant`](./claimant) ·
[`watchdog`](./watchdog) · [`quartermaster`](./quartermaster) ·
[`archivist`](./archivist) · [`fedora-hat`](./fedora-hat)

### Rust (20)

[`borrow-checker`](./borrow-checker) · [`lifetimes`](./lifetimes) · [`ownership`](./ownership) · [`traits`](./traits) · [`generics`](./generics) · [`error-types`](./error-types) · [`result-propagation`](./result-propagation) · [`unsafe-audit`](./unsafe-audit) · [`ffi-boundary`](./ffi-boundary) · [`async-tasks`](./async-tasks) · [`channels`](./channels) · [`mutexes`](./mutexes) · [`macros`](./macros) · [`zero-copy`](./zero-copy) · [`iterator-chains`](./iterator-chains) · [`pattern-matching`](./pattern-matching) · [`cargo-features`](./cargo-features) · [`no-std`](./no-std) · [`binary-size`](./binary-size) · [`cross-compile`](./cross-compile)

### Linux systems (20)

[`systemd-unit`](./systemd-unit) · [`systemd-timer`](./systemd-timer) · [`journald-logs`](./journald-logs) · [`cgroups`](./cgroups) · [`namespaces`](./namespaces) · [`mount-units`](./mount-units) · [`udev-rules`](./udev-rules) · [`dbus-calls`](./dbus-calls) · [`signal-handling`](./signal-handling) · [`unix-sockets`](./unix-sockets) · [`file-permissions`](./file-permissions) · [`capabilities`](./capabilities) · [`initramfs`](./initramfs) · [`boot-order`](./boot-order) · [`kernel-modules`](./kernel-modules) · [`swap-tuning`](./swap-tuning) · [`logrotate`](./logrotate) · [`cron-units`](./cron-units) · [`shell-portability`](./shell-portability) · [`process-supervision`](./process-supervision)

### Debian image (20)

[`live-build`](./live-build) · [`preseed`](./preseed) · [`apt-pinning`](./apt-pinning) · [`package-signing`](./package-signing) · [`chroot-build`](./chroot-build) · [`squashfs`](./squashfs) · [`iso-hybrid`](./iso-hybrid) · [`reproducible-image`](./reproducible-image) · [`image-size`](./image-size) · [`firstboot`](./firstboot) · [`update-channel`](./update-channel) · [`rollback-partition`](./rollback-partition) · [`secure-boot`](./secure-boot) · [`firmware-blobs`](./firmware-blobs) · [`locale-config`](./locale-config) · [`fstab-layout`](./fstab-layout) · [`service-enable`](./service-enable) · [`user-setup`](./user-setup) · [`build-manifest`](./build-manifest) · [`boot-test`](./boot-test)

### Network (20)

[`tcp-handshake`](./tcp-handshake) · [`udp-datagrams`](./udp-datagrams) · [`dns-resolution`](./dns-resolution) · [`tls-verification`](./tls-verification) · [`http-semantics`](./http-semantics) · [`websocket`](./websocket) · [`proxy-headers`](./proxy-headers) · [`firewall-rules`](./firewall-rules) · [`mtls`](./mtls) · [`retry-budget`](./retry-budget) · [`backoff-jitter`](./backoff-jitter) · [`connection-pool`](./connection-pool) · [`timeouts`](./timeouts) · [`load-balancing`](./load-balancing) · [`rate-limiting`](./rate-limiting) · [`ipv6`](./ipv6) · [`unix-socket-client`](./unix-socket-client) · [`packet-capture`](./packet-capture) · [`mtu`](./mtu) · [`http-caching`](./http-caching)

### Data (20)

[`jsonl-append`](./jsonl-append) · [`schema-validation`](./schema-validation) · [`migrations`](./migrations) · [`sqlite-queries`](./sqlite-queries) · [`redis-keys`](./redis-keys) · [`cache-invalidation`](./cache-invalidation) · [`queue-semantics`](./queue-semantics) · [`idempotency`](./idempotency) · [`dedupe`](./dedupe) · [`retention`](./retention) · [`backup`](./backup) · [`restore-drill`](./restore-drill) · [`checksums`](./checksums) · [`indexing`](./indexing) · [`pagination`](./pagination) · [`transactions`](./transactions) · [`null-handling`](./null-handling) · [`timestamps`](./timestamps) · [`encoding`](./encoding) · [`compression`](./compression)

### Security (20)

[`threat-model`](./threat-model) · [`secret-handling`](./secret-handling) · [`authn`](./authn) · [`authz`](./authz) · [`token-lifecycle`](./token-lifecycle) · [`csrf`](./csrf) · [`injection`](./injection) · [`path-traversal`](./path-traversal) · [`sandboxing`](./sandboxing) · [`least-privilege`](./least-privilege) · [`audit-log`](./audit-log) · [`key-rotation`](./key-rotation) · [`supply-chain`](./supply-chain) · [`disclosure`](./disclosure) · [`redaction`](./redaction) · [`password-storage`](./password-storage) · [`session-fixation`](./session-fixation) · [`tls-pinning`](./tls-pinning) · [`command-injection`](./command-injection) · [`dependency-audit`](./dependency-audit)

### Testing (20)

[`unit-tests`](./unit-tests) · [`property-tests`](./property-tests) · [`fuzz-targets`](./fuzz-targets) · [`golden-files`](./golden-files) · [`snapshots`](./snapshots) · [`integration-tests`](./integration-tests) · [`e2e`](./e2e) · [`fixtures`](./fixtures) · [`flaky-tests`](./flaky-tests) · [`coverage`](./coverage) · [`mutation`](./mutation) · [`contract-tests`](./contract-tests) · [`regression-suite`](./regression-suite) · [`load-tests`](./load-tests) · [`soak-tests`](./soak-tests) · [`test-data`](./test-data) · [`assertions`](./assertions) · [`skip-policy`](./skip-policy) · [`parallel-tests`](./parallel-tests) · [`gate-runner`](./gate-runner)

### Debugging (20)

[`repro-steps`](./repro-steps) · [`bisect`](./bisect) · [`strace`](./strace) · [`core-dump`](./core-dump) · [`log-triage`](./log-triage) · [`metrics-triage`](./metrics-triage) · [`distributed-trace`](./distributed-trace) · [`heap-profile`](./heap-profile) · [`deadlock`](./deadlock) · [`race-condition`](./race-condition) · [`memory-leak`](./memory-leak) · [`off-by-one`](./off-by-one) · [`encoding-bug`](./encoding-bug) · [`timeout-bug`](./timeout-bug) · [`rollback`](./rollback) · [`environment-drift`](./environment-drift) · [`minimal-repro`](./minimal-repro) · [`hypothesis-log`](./hypothesis-log) · [`crash-loop`](./crash-loop) · [`postmortem-trace`](./postmortem-trace)

### Performance (20)

[`profiling`](./profiling) · [`benchmarking`](./benchmarking) · [`latency-percentiles`](./latency-percentiles) · [`throughput`](./throughput) · [`memory-footprint`](./memory-footprint) · [`allocation`](./allocation) · [`cache-misses`](./cache-misses) · [`io-throughput`](./io-throughput) · [`gc-tuning`](./gc-tuning) · [`connection-pools`](./connection-pools) · [`batching`](./batching) · [`parallelism`](./parallelism) · [`tail-latency`](./tail-latency) · [`resource-budget`](./resource-budget) · [`regression-gate`](./regression-gate) · [`cpu-pinning`](./cpu-pinning) · [`page-cache`](./page-cache) · [`cold-start`](./cold-start) · [`contention`](./contention) · [`capacity-model`](./capacity-model)

### Documentation (20)

[`readme`](./readme) · [`runbook`](./runbook) · [`adr`](./adr) · [`changelog`](./changelog) · [`api-reference`](./api-reference) · [`tutorial`](./tutorial) · [`reference-doc`](./reference-doc) · [`troubleshooting`](./troubleshooting) · [`diagrams`](./diagrams) · [`code-comments`](./code-comments) · [`docstrings`](./docstrings) · [`style-guide`](./style-guide) · [`link-check`](./link-check) · [`versioning-docs`](./versioning-docs) · [`deprecation-notes`](./deprecation-notes) · [`onboarding`](./onboarding) · [`faq`](./faq) · [`examples`](./examples) · [`screenshots`](./screenshots) · [`docs-review`](./docs-review)

### Release (20)

[`semver`](./semver) · [`tags`](./tags) · [`changelog-entry`](./changelog-entry) · [`artifacts`](./artifacts) · [`release-checksums`](./release-checksums) · [`signing`](./signing) · [`rollback-plan`](./rollback-plan) · [`canary`](./canary) · [`feature-flags`](./feature-flags) · [`release-migrations`](./release-migrations) · [`deprecation`](./deprecation) · [`compatibility`](./compatibility) · [`version-pinning`](./version-pinning) · [`release-notes`](./release-notes) · [`post-release-check`](./post-release-check) · [`hotfix`](./hotfix) · [`backport`](./backport) · [`release-branch`](./release-branch) · [`build-provenance`](./build-provenance) · [`artifact-retention`](./artifact-retention)

### Operations (20)

[`incident-response`](./incident-response) · [`oncall-handoff`](./oncall-handoff) · [`slo-definition`](./slo-definition) · [`alerting`](./alerting) · [`dashboards`](./dashboards) · [`healthchecks`](./healthchecks) · [`restart-policy`](./restart-policy) · [`capacity-planning`](./capacity-planning) · [`backup-drill`](./backup-drill) · [`runbook-drill`](./runbook-drill) · [`postmortem`](./postmortem) · [`change-window`](./change-window) · [`status-page`](./status-page) · [`escalation`](./escalation) · [`kill-switch`](./kill-switch) · [`log-retention`](./log-retention) · [`cost-watch`](./cost-watch) · [`dependency-outage`](./dependency-outage) · [`failover`](./failover) · [`recovery-test`](./recovery-test)

### Agent (20)

[`task-decomposition`](./task-decomposition) · [`tool-selection`](./tool-selection) · [`context-budget`](./context-budget) · [`handoff-notes`](./handoff-notes) · [`refusal`](./refusal) · [`ambiguity`](./ambiguity) · [`verification`](./verification) · [`memory`](./memory) · [`delegation`](./delegation) · [`self-review`](./self-review) · [`cost-control`](./cost-control) · [`permissions`](./permissions) · [`agent-escalation`](./agent-escalation) · [`stop-conditions`](./stop-conditions) · [`planning`](./planning) · [`progress-reporting`](./progress-reporting) · [`retry-policy`](./retry-policy) · [`uncertainty`](./uncertainty) · [`conflict-resolution`](./conflict-resolution) · [`audit-trail`](./audit-trail)

### Science (20)

[`hypothesis`](./hypothesis) · [`controls`](./controls) · [`measurement`](./measurement) · [`science-uncertainty`](./science-uncertainty) · [`reproducibility`](./reproducibility) · [`sampling`](./sampling) · [`bias`](./bias) · [`instrumentation`](./instrumentation) · [`calibration`](./calibration) · [`datasets`](./datasets) · [`notebooks`](./notebooks) · [`peer-review`](./peer-review) · [`ethics`](./ethics) · [`reporting`](./reporting) · [`effect-size`](./effect-size) · [`significance`](./significance) · [`outliers`](./outliers) · [`longitudinal`](./longitudinal) · [`field-notes`](./field-notes) · [`replication`](./replication)

### Product (20)

[`prd`](./prd) · [`acceptance-criteria`](./acceptance-criteria) · [`scope`](./scope) · [`user-stories`](./user-stories) · [`metrics`](./metrics) · [`experiments`](./experiments) · [`feedback`](./feedback) · [`roadmap`](./roadmap) · [`prioritization`](./prioritization) · [`tradeoffs`](./tradeoffs) · [`pricing`](./pricing) · [`product-onboarding`](./product-onboarding) · [`support`](./support) · [`privacy`](./privacy) · [`accessibility`](./accessibility) · [`edge-cases`](./edge-cases) · [`error-messages`](./error-messages) · [`empty-states`](./empty-states) · [`success-metrics`](./success-metrics) · [`launch-checklist`](./launch-checklist)
