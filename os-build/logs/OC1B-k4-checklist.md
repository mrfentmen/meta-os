# OC1B-126 — K4 checklist: review's pinned gate lines (extracted 2026-11-02)
# Source: os-build/K4_IPC_DESIGN.md §7 on origin/rowan/kernel-k4-build @
# 4a37f998 (Pax required change 4: literals pinned in advance by the build
# step). {s} = sender id, {d} = destination id, {n} = payload length.

1. [ ] Send success:        `user ipc send from {s} to {d} len {n}`
2. [ ] Receive success:      `user ipc recv from {s} len {n}` (total copied = 8+{n})
3. [ ] Full box refusal:     `user ipc send refused: full box {d}` (returns u64::MAX)
4. [ ] Dead destination:     `user ipc send refused: dead destination {d}`
5. [ ] Unmapped buffer:      `user ipc send refused: unmapped buffer`
6. [ ] Undersized buffer:    `user ipc recv refused: small buffer {n}` (capacity < 72)
7. [ ] Empty receive:         `user ipc recv refused: empty box` (sentinel, no block)

Additional pinned refusal lines (same §7, checked if observed):
- `user ipc send refused: bad length {n}` (zero or over 64)
- `user ipc recv refused: unmapped buffer`

Return-code rule: every refusal returns u64::MAX and changes no mailbox
state. Success send returns 0; success recv returns 8+payload_len (9..=72).
Sender id bytes [0..8) little-endian u64, kernel-filled from current_id().
