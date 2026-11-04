# One-commit switch plan: Rust `relay` for `relay/relay.mjs` (Lane D proposal — NOT executed)

Status: PROPOSAL for lead approval. The image still runs Node `relay/relay.mjs`.
Nothing below was switched, and no ISO/provision script was touched (D14 gate).

## Preconditions (all must be true before the switch commit)

1. R1 fixed: POST `/rooms/<room>/messages` returns `{"index","id"}` with the
   documented `msg-<sha256(room,index,line)[0:16]>` shape (`relay/relay.mjs:134`).
2. R2 fixed: `parse_object_strings` (`crates/relay/src/http.rs`) skips
   whitespace after `,` (one-line fix), so Python-`json.dumps`/pretty JSON
   posts get 201 like Node.
3. R3–R5 fixed or formally accepted: invalid-`since` 400, `limit` honored,
   out-of-range-`limit` 400 — matching `relay/relay.mjs:328-358`.
4. Re-run: `cargo build --release -p relay`, `cargo test --release -p relay`,
   black-box `crates/verify-logs/relay-blackbox.log` shows 0 mismatches, and
   `node --test relay/relay.test.mjs relay/relay.round13.test.mjs` is green
   (note: R13-419 is red vs Node itself today — stale clamp expectation —
   so that suite must be fixed or waived first, independent of Rust).
5. File-store parity run: boot both with the same `RELAY_STORE_FILE`, post,
   restart, confirm reload equality (torn-record tolerance included).

## Switch commit (single commit, carrier-only)

- Change the relay launch in `os-build/face/provision.sh` (or the supervising
  unit that starts `node relay/relay.mjs`) to start `/opt/metaos/bin/relay`
  with the same `RELAY_PORT` / `RELAY_STORE_FILE` environment.
- Ship the binary from `target/release/relay` (source-built in CI, not a blob).
- No UI change: `relay/viewer.html`, `board/board.html` keep the same URLs.

## Rollback (one command, no rebuild)

- Revert the launch line to `node relay/relay.mjs`; restart the service.
- The store file format (`{"room":...,"line":...}` JSONL) is shared, so rooms
  survive a rollback; in-memory-only mode loses history either way.

## Verification after switch

- `curl $RELAY/health` → `{"ok":true,...}`; POST+GET watermark round-trip;
  `node --test relay/relay.test.mjs` still green (it tests the Node module,
  unaffected).
- Rollback trigger: any 400/500 divergence in the first 24h → revert per above.
