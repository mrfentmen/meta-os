// Node built-in test runner, no dependencies:
//   node --test tests/native-log-restore.test.mjs
//
// Web <-> native session-log restore parity. The web frontend's log
// restore (js/log.js _restore) keeps every well-formed saved entry
// and drops only the malformed ones, so one bad entry cannot wipe the
// log. The native restore used to decode the whole saved array in one
// shot, so a single malformed entry made the entire decode fail and a
// relaunch start from an empty log, silently discarding every good
// entry. This test reads SessionLog.swift (it cannot run Swift in this
// sandbox) to assert the restore decodes one entry at a time and
// skips the ones that fail, instead of decoding the array whole.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const swift = readFileSync(
  new URL("../native/Sources/MetaTrio/Models/SessionLog.swift", import.meta.url),
  "utf8",
);

const restore = swift.slice(
  swift.indexOf("private static func loadSavedEntries()"),
  swift.indexOf("/// Best effort, like the web log's storage writes"),
);

test("native: restore parses the saved file as a raw JSON array, not as a decoded entry array", () => {
  assert.match(restore, /JSONSerialization\.jsonObject\(with: data\) as\? \[Any\]/);
  assert.doesNotMatch(restore, /JSONDecoder\(\)\.decode\(\[SessionLogEntry\]\.self/);
});

test("native: restore decodes each entry on its own and skips the ones that fail", () => {
  assert.match(restore, /for rawEntry in rawEntries/);
  assert.match(
    restore,
    /let entry = try\? decoder\.decode\(SessionLogEntry\.self, from: entryData\)/,
  );
  assert.match(restore, /continue/);
  assert.match(restore, /kept\.append\(entry\)/);
});

test("native: restore still returns an empty log for a missing or non-array file", () => {
  assert.match(restore, /guard let url = persistenceURL/);
  assert.match(restore, /else \{\n\s+return \[\]\n\s+\}/);
});
