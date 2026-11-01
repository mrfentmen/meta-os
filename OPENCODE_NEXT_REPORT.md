# Prove the new main (Custos merge) on the Mac

Task: OPENCODE_NEXT_TASK.md at main tip 787058c (this checkout merged as
e81c3e4). Compile and suites only — no staging, no click sweep, no camera.

Baselines from the task (sandbox, merged tree): cargo 1412/0; node 1933 run,
1877 pass, 56 fail (exact known WKWebView set); queue python 110 OK; officina
49 OK; custos 32 OK.

## Results (tip 787058c merged as e81c3e4)

1. Pulled main: tip 787058c (Custos merge), merged into opencode/mac-tasks as e81c3e4.
2. Cargo: 1412 pass, 0 fail (`cargo test --workspace`, EXIT:0). Matches.
3. Node: 1933 run, 1877 pass, 56 fail — all 56 in tests/native-*, zero
   outside the known set. Matches exactly.
4. Python: queue suite does NOT collect on this Mac (same
   dynamic_credentials import failure as the 100-task run: 4 collection
   errors, 0 run — sandbox 110 OK stands unreproduced here); officina 49/49
   OK; custos tests/custos 32/32 OK.
5. Native build: `swift build` clean, "Build complete! (40.01s)", EXIT:0.
   Compile only, app not launched, per the task.
6. Custos smoke: `patrol.py run --config hosts.example.json` (read only,
   records to stdout, state in /tmp): summary line —
   hosts_checked 3, kev_entries_seen 1766, 5 KEV matches (red, escalated to
   endpoint SIMULATED only), 1 yellow (github.com port 22 exposure), 6
   baseline-normal, 0 down; one noted error (CT fetch for letsencrypt.org:
   HTTP 502). No repo files touched.
