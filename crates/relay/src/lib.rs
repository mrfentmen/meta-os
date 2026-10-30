//! Crate `relay` — Meta Nuntius relay (batch B08, owner: Hana).
//!
//! Port of `relay/relay.mjs` (Node, stdlib only) and its README.
//! The source is the spec: port behavior, do not redesign. Same
//! inputs, outputs, edge cases, error shapes — oddities ported and
//! noted. The Python/Node originals stay the live fallback until
//! this batch is PORTED (both gates + parity).
//!
//! ## What it is
//!
//! Meta Nuntius (Latin: "messenger") is the message relay for the
//! Meta Trio / Meta OS layer: the queue service, the resident agent,
//! and the product consoles exchange plain-text lines and structured
//! NOTIFY lines through it, with no external service involved. It is
//! a clean-room reimplementation of the line protocol the crew
//! already uses — it shares no code with the crew's operational
//! muse-relay bus and does not replace it.
//!
//! ## Wire format
//!
//! Message line (one per room entry):
//! ```text
//! <nick>: <text> [ts:<epoch-seconds>]
//! ```
//!
//! NOTIFY line (appended by the `/notify` endpoint, as nick `relay`):
//! ```text
//! relay: NOTIFY:<id> <severity> [<topic>] <text> [ts:<epoch-seconds>]
//! ```
//!
//! - `id` = `ntf-` + the first 16 hex chars of the SHA-256 of
//!   `room + "\n" + topic + "\n" + severity + "\n" + text` — the
//!   same payload in the same room always yields the same id.
//! - `severity` is one of `info`, `warning`, `critical`.
//! - Every line is stamped at send time with the trailing
//!   ` [ts:<epoch-seconds>]` marker.
//!
//! ## Polling
//!
//! Polling is watermark-based: POST returns the new line's 0-based
//! index in its room; GET `?since=<n>` returns the lines after index
//! `n` (`since=-1`, or no `since`, returns the whole room).
//!
//! ## Endpoints
//!
//! | Method & path | Body / params | Returns |
//! | --- | --- | --- |
//! | `POST /rooms/<room>/messages` | `{nick, text}` | `201 {index}` — the line's 0-based position in the room |
//! | `POST /rooms/<room>/notify` | `{severity, topic, text}` | `201 {index, id}` |
//! | `GET /rooms/<room>/messages?since=<n>` | `since` = last index seen | `{room, total, messages}` — the lines after index `n` |
//! | `GET /health` | — | `{ok: true, rooms: <count>, store: "memory" \| "file"}` |
//! | `GET /` | — | the viewer (`viewer.html`) |
//!
//! ## Validation caps (refusals are `400` JSON errors)
//!
//! - Room name: `[a-z0-9-]{1,32}`.
//! - Nick: single line, 1–40 chars, no control characters.
//! - Text: single line, 1–2000 chars.
//! - Topic: single line, 1–64 chars.
//! - Request body: at most 16384 bytes of JSON.
//!
//! Unknown routes answer `404` JSON; unexpected failures answer
//! `500` JSON.
//!
//! ## Storage
//!
//! Storage is in-memory by default. If `RELAY_STORE_FILE` is set,
//! every appended line is also written to that file as one JSON
//! record per line (`{"room": ..., "line": ...}`) and the file is
//! reloaded on boot, so rooms survive a restart. A torn final record
//! is skipped, never fatal.
//!
//! ## Run
//!
//! The binary resolves `RELAY_PORT` (default 8787) and
//! `RELAY_STORE_FILE` (unset = in-memory only), binds, and serves
//! forever. Open `http://127.0.0.1:8787/` for the viewer: room
//! switcher, watermark polling, and a Notifications strip that
//! surfaces NOTIFY lines newest-first.
//!
//! ## Modules
//!
//! - `validation`, `notify`, `sha256`, `store`, `json`: the pure core
//!   (validation caps, notify ids, in-memory / JSONL room store).
//! - `http`: the server layer (routes, bodies, viewer, std TCP serve),
//!   plus the parity tests whose name roots mirror
//!   `relay/relay.test.mjs`.
//!
//! No external crates: SHA-256 and the small JSON handling are
//! implemented here, mirroring the original's stdlib-only stance.

pub mod http;
pub mod json;
pub mod notify;
pub mod sha256;
pub mod store;
pub mod validation;
