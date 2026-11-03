// CB2-467/468 — Musica library data.
//
// gate-packet/library.json is written by runtime/library.py: one holding per
// brief, with the prompt that produced it and the takes it kept. The test
// round-trips the real file and runs the rights validator over fixtures,
// because the published holdings predate the licence field — that gap is
// named in os-build/BOND_500B_STATUS.md rather than papered over.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { validateLibrary } from "../os/worlds/musica/catalogue_validate.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const LIBRARY = path.join(ROOT, "os/worlds/musica/gate-packet/library.json");

const raw = fs.readFileSync(LIBRARY, "utf8");
const library = JSON.parse(raw);

test("CB2-467 the real library round-trips with every holding intact", () => {
  assert.ok(Array.isArray(library.prompts), "library.prompts is an array");
  assert.ok(library.prompts.length >= 3, "read the real holdings: " + library.prompts.length);
  const reloaded = JSON.parse(JSON.stringify(library));
  assert.deepEqual(reloaded, library, "serialise then reload is byte-identical");

  for (const holding of reloaded.prompts) {
    assert.equal(typeof holding.brief_id, "string", "brief_id");
    assert.equal(typeof holding.prompt, "string", "prompt text");
    assert.equal(typeof holding.takes, "number", "takes count");
    assert.equal(typeof holding.keepers, "number", "keepers count");
    assert.ok(Array.isArray(holding.keeper_take_ids), "keeper id list");
    assert.equal(
      holding.keeper_take_ids.length,
      holding.keepers,
      holding.brief_id + ": keeper list length matches the keeper count",
    );
    assert.equal(
      holding.keeper_rate,
      Number((holding.keepers / holding.takes).toFixed(4)),
      holding.brief_id + ": keeper rate is keepers over takes",
    );
  }
});

test("CB2-468 a holding missing its rights field is flagged, not accepted", () => {
  const fixture = {
    prompts: [{
      brief_id: "chipsynth",
      prompt: "# Chipsynth brief",
      takes: 12,
      keepers: 11,
      keeper_rate: 0.9167,
      keeper_take_ids: ["take-001"],
    }],
  };
  const errors = validateLibrary(fixture);
  assert.deepEqual(errors, [
    "library.prompts[0].licence: rights missing — every holding needs its licence line",
  ]);
});

test("CB2-468b a holding with its licence and matching counts passes", () => {
  const fixture = {
    prompts: [{
      brief_id: "chipsynth",
      prompt: "# Chipsynth brief",
      takes: 12,
      keepers: 1,
      keeper_rate: 0.0833,
      keeper_take_ids: ["take-001"],
      licence: "own — generated in-studio by Meta Musica",
    }],
  };
  assert.deepEqual(validateLibrary(fixture), []);
});
