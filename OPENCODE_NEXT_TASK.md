# OpenCode next task: prove the new main on the Mac

Boss order, 2026-11-01: the 8 PM end to end test is skipped for now. It
comes later tonight, after everything else is built out. This task is not
that test. Do not stage an incident, do not run the click sweep, do not do
camera staging or camera permission work in this task.

Repo: mrfentmen/meta-os. Pull the new main tip (the Custos merge commit,
the tip of main when you read this) on your existing checkout. Work and
report on branch opencode/mac-tasks. Never commit the 4 excluded bus
files: bus-tools/bus-poll, bus-tools/bus-rooms, bus-tools/bus-send,
tests/test_bus_admin_e2e.py.

What is new in this main: Meta Custos is merged in (night watch system:
KEV patrol, certificate expiry, host liveness, sensitive port exposure;
yellow records and flags only, red escalates to the labelled SIMULATED
endpoint only). Hana's UI wave is already in. Test baselines were
re-measured in the sandbox on the merged tree before the push.

## The job

1. Pull main. Record the exact tip hash in the report.
2. Cargo: run the full workspace test suite. Expected: 1412 pass, 0 fail.
3. Node: run npm test. Expected: 1933 tests, 1877 pass, 56 fail, and the
   56 must be exactly the known WKWebView native set. Name any failure
   outside that set.
4. Python: run the queue suite (expected 110 OK), the officina suite
   (expected 49 OK), and the custos suite in tests/custos (expected
   32 OK).
5. Native build: compile the WKWebView native app. Compile only. The
   build must finish with no errors. Do not run the app through the test
   script, do not click through it.
6. Custos smoke: run one patrol pass from os/worlds/custos/runtime
   against the example hosts file and show the summary line it prints
   (entries checked, matches found). Read only, no changes to the pack.

## Rules

- Proof or it did not happen. Every claim carries the command and its
  real output numbers.
- On the first red result, stop, paste the exact error text into the
  report, and report. Do not patch around it. A one line obvious typo is
  the only fix allowed, and it gets logged.
- Anything that dispatches goes to the SIMULATED endpoint only.
- Write the report to OPENCODE_NEXT_REPORT.md in the repo root, commit
  it on opencode/mac-tasks, and push that branch. Do not push to main.
