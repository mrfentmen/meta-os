# Prove the new main on the Mac (second run)

Task: OPENCODE_NEXT_TASK.md at main tip 6d8d54ee (this checkout merged as
ab763ac0). Compile and suites only — no staging, no click sweep, no camera
staging or camera permission work in this task.

Baselines from the task (sandbox, Custos-merge tree): cargo 1412/0;
node 1933 run, 1877 pass, 56 fail (exact known WKWebView set);
queue python 110 OK; officina 49 OK; custos tests/custos 32 OK.

Merge note: origin/main merged clean except two add/add design files
(design/meta-scientia-molecules.html, design/meta-musica-notes.html).
Both conflicts are theme/staff-geometry values; resolved with --theirs
(main side) per boss orders (bright-lab 41bc6a57; staff boss-fix).
Merged tree is otherwise byte-identical to origin/main 6d8d54ee
(verified: `git diff origin/main` shows only os-build/logs/MERGED-boot.txt,
a log from the prior run).

## Results (tip 6d8d54ee merged as ab763ac0)

1. Pulled main: tip 6d8d54ee, merged into opencode/mac-tasks as ab763ac0.
2. Cargo: RED. `cargo test --workspace` fails to compile the
   os-supervisor lib-test target (2 errors, no tests ran):
   `error[E0271]: expected {closure@watchdog.rs:4098:24} to return (), but it returns !`
   (`let mut boom = |_ts: i64| panic!("store down")`)
   `error[E0271]: expected {closure@watchdog.rs:4972:24} to return (), but it returns !`
   (`let mut boom = |_alert: &Alert| panic!("emit down")`)
   Full log: /tmp/prove-main-cargo.log. No patch applied (not a typo;
   test-closuredivergence, supervisor-lane owns it).
3. Node: 2002 run, 1947 pass, 55 fail (runner ℹ summary). Baseline was
   1933/1877/56 — the suite grew by ~69 tests since (relay,
   surfaces-dispatch-card, new native size tests).
   31 failing files are all tests/native-*. Outside that file set:
   tests/ui.test.mjs, 6 subtests (rerun in isolation: 108 pass, 6 fail):
   - camera: web Start says it is waiting for camera permission...
   - latest: web panel waits for the first assessment...
   - panels: still-image and video panels show an in-panel sending note...
   - camera: web shows an analysis-active banner while sampling...
   - latest: native panel carries the observable-evidence note...
   - config: web sampling interval clamps to 1-60 like the native Stepper...
   All six are web-vs-native parity assertions against native Swift
   sources that changed under Hana's wave (e.g. ContentView no longer
   contains `Stepper(value: $model.intervalSeconds, in: 1...60)`).
   Named here as outside the tests/native-* file set; whether the 55
   fail-name set equals the known WKWebView set is for the set owner
   to confirm — the file-location criterion no longer holds exactly.
4. Python: queue suite 128 tests, OK (the old dynamic_credentials
   collection failure is GONE on this tree; count grew 110 -> 128);
   officina 49/49 OK; custos tests/custos 125/125 OK (grew from 32).
   No Spark keys in env, no live calls (scripted assessors only).
5. Native build: RED via `swift build` in native/ —
   `LogoLoopView.swift:64:24: error: external macro implementation type
   'SwiftUIMacros.StateMacro' could not be found for macro 'State()';
   plugin for module 'SwiftUIMacros' not found`, build stops at
   [165/170], `error: Build failed`. Toolchain note, not product code:
   only CommandLineTools is installed; `xcodebuild` refuses to run:
   `xcode-select: error: tool 'xcodebuild' requires Xcode, but active
   developer directory '/Library/Developer/CommandLineTools' is a
   command line tools instance`. Compile only attempted; app never
   launched, per the task.
6. Custos smoke: `patrol.py run --config hosts.example.json`
   (read only, state in /tmp): summary line —
   `patrol complete: 3 hosts, 5 escalations, 0 errors`
   (hosts_checked 3, kev_entries_seen 1766, 5 KEV escalations to
   SIMULATED endpoints only, 1 anomalous exposure, 11 baseline
   normal, 0 down, 0 errors). One noted line (not an error): CT fetch
   for letsencrypt.org returned HTTP 502 in-transit; recorded, run
   still 0 errors. No repo files touched (state file in /tmp).
