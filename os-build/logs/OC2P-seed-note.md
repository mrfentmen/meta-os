# OC2P seed determinism note (no VM — /tmp ISOs only, deleted after)

Experiment 2026-11-03: `sh agent-layer/make-seed.sh <out> oc2-determinism`
run twice, same instance-id, 2s apart. Both built (921600 bytes each).

- run A: `53d253b7749c7443997c8efa6814ad3141f22685a8ba9b1d9ac3c3c836ba84b7`
- run B: `8e22f6ab4624983527f7befbb81352087ab01eedc7b7e94fd715c60b98632d5f`

Result: NOT byte-deterministic. `hdiutil makehybrid` embeds volume/timestamp
data, so identical inputs give different bytes. The recipe (user-data,
meta-data, keypair steps in `make-seed.sh`) is deterministic and re-runnable;
the artifact is not byte-pinned.

Rule for the lane: never assert a seed sha across runs. Re-proofs start
"from script" (recipe), and any consumer verifies by mounting + reading
`user-data`/`meta-data` content, not by comparing ISO hashes. Both test ISOs
deleted from /tmp after hashing.
