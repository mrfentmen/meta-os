// CB2-392/393 — the bridge's wire shape for the messages it does send.
//
// The bridge has no chat of its own: it answers a start or a stop with a result
// addressed to the agent that asked. That reply is the message, so it has a
// destination, a kind, and a body, and a reply with no destination is refused
// rather than written into the ledger as a note to nobody.
import test from "node:test";
import assert from "node:assert/strict";
import { toWire, WIRE_FIELDS } from "../agents/bridge.mjs";

test("CB2-392 a bridge result converts to the wire shape with every field kept", () => {
  const message = {
    to: "watchman",
    kind: "started",
    body: { run: "run-1", agent: "watchman" },
    ts: 1793600000000,
  };
  const wire = toWire(message);

  assert.deepEqual(Object.keys(wire).sort(), [...WIRE_FIELDS].sort());
  assert.equal(wire.to, "watchman");
  assert.equal(wire.kind, "started");
  assert.deepEqual(wire.body, { run: "run-1", agent: "watchman" });
  assert.equal(wire.ts, 1793600000000);
  assert.equal(wire.v, 1, "the wire carries its version");

  // A missing timestamp is filled with the clock, not left undefined.
  const now = toWire({ to: "x", kind: "refused", body: { reason: "stop-filed" } });
  assert.equal(typeof now.ts, "number");
  assert.ok(now.ts > 0);

  // The input is not mutated by shaping it.
  assert.deepEqual(message, { to: "watchman", kind: "started", body: { run: "run-1", agent: "watchman" }, ts: 1793600000000 });
});

test("CB2-393 a message with no destination is refused by name", () => {
  for (const bad of [
    null,
    {},
    { kind: "started", body: {} },
    { to: "", kind: "started" },
    { to: "   ", kind: "started" },
    { to: 42, kind: "started" },
  ]) {
    assert.throws(() => toWire(bad), /bridge: message has no destination/, JSON.stringify(bad));
  }

  // A destination but no kind is also refused: a nameless message cannot be routed.
  assert.throws(() => toWire({ to: "watchman" }), /bridge: message has no kind/);
  assert.throws(() => toWire({ to: "watchman", kind: "  " }), /bridge: message has no kind/);

  // The body is optional and defaults to an empty object, never undefined.
  assert.deepEqual(toWire({ to: "a", kind: "refused" }).body, {});
});
