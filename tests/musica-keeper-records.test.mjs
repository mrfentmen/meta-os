// CB2-469/470 — keeper records, derived from a real session take log.
//
// The log is the studio's own: os/worlds/musica/sessions/hn038-ambient. The
// window is computed from it, never typed in, so a change in the log shows up
// here as a change in the record.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { keeperLine, keeperWindow, validateKeeperEntry } from "../os/worlds/musica/keeper_log.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const LOG = path.join(ROOT, "os", "worlds", "musica", "sessions", "hn038-ambient", "take_log.jsonl");
const takes = fs.readFileSync(LOG, "utf8").trim().split("\n").map((line) => JSON.parse(line));

test("CB2-469 a keeper window carries start, end and the kept count from the real log", () => {
  assert.equal(takes.length, 4, "the real session has four takes");
  const window = keeperWindow(takes);

  assert.equal(window.session, "hn038-ambient");
  assert.equal(window.start, "2026-11-01T11:33:08.662066Z", "the first take's timestamp");
  assert.equal(window.end, "2026-11-01T11:33:10.272536Z", "the last take's timestamp");
  assert.equal(window.kept, 4, "every take kept");
  assert.equal(window.rejected, 0);
  assert.equal(window.takes, 4);
  assert.equal(window.complete, true);
  assert.deepEqual(window.missing, []);

  // The record survives a round trip through the line format it is written in.
  const line = keeperLine(window);
  assert.deepEqual(JSON.parse(line), window);
  assert.equal(line.includes("\n"), false, "one record, one line");
  assert.deepEqual(validateKeeperEntry(window), []);
});

test("CB2-470 a keeper entry with no end is flagged incomplete, not treated as finished", () => {
  const window = keeperWindow(takes);
  const noEnd = { ...window, end: null };
  const errors = validateKeeperEntry(noEnd);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /end: missing/);

  // A take without a timestamp makes the window incomplete and names the gap.
  const broken = takes.map((t, i) => (i === takes.length - 1 ? { ...t, timestamp: null } : t));
  const partial = keeperWindow(broken);
  assert.equal(partial.complete, false);
  assert.deepEqual(partial.missing, ["timestamp"]);
  assert.equal(partial.end, "2026-11-01T11:33:09.748256Z", "the last usable timestamp, not a guess");

  // A take with no verdict is missing that field too.
  const noVerdict = takes.map((t, i) => (i === 0 ? { ...t, verdict: null } : t));
  const unjudged = keeperWindow(noVerdict);
  assert.deepEqual(unjudged.missing, ["verdict"]);
  assert.equal(unjudged.kept, 3);

  // Other refusals: a reversed window, more keepers than takes, bad types.
  assert.match(validateKeeperEntry({ ...window, end: "2026-10-31T00:00:00Z" }).join(" "), /end: is before start/);
  assert.match(validateKeeperEntry({ ...window, kept: 9 }).join(" "), /more keepers than takes/);
  assert.match(validateKeeperEntry({ ...window, takes: "4" }).join(" "), /takes: must be a non-negative integer/);
  assert.deepEqual(validateKeeperEntry(null), ["keeper entry: must be an object"]);

  // An empty log is refused outright: there is no window without takes.
  assert.throws(() => keeperWindow([]), /at least one take is required/);
  assert.throws(() => keeperWindow(null), /at least one take is required/);
});
