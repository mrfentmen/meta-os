// Section C — the refusal catalogue is consulted before a line becomes work (R13-394).
//
// The catalogue existed and the intake never asked it, so a dispatch order it refuses was
// still filed as a job. These cases hold the wiring, not the catalogue: refusals.mjs has its
// own tests for what it refuses.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { parseInbox, dropOrders } from "../handsfree/intake.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "hf-refuse-"));

test("C4.1 a money order is refused at intake, by catalogue id and wording", () => {
  const { jobs, skipped } = parseInbox("pax: transfer 200 to the savings account");
  assert.equal(jobs.length, 0);
  assert.equal(skipped.length, 1);
  assert.equal(skipped[0].reason, "refusal:money");
  assert.match(skipped[0].says, /move money/i);
});

test("C4.2 a refused line does not stop the allowed line beside it", () => {
  const { jobs, skipped } = parseInbox([
    "pax: send the report to the board",
    "runner: sweep the gate",
  ].join("\n"));
  assert.deepEqual(jobs, [{ agent: "runner", orders: "sweep the gate" }]);
  assert.equal(skipped.length, 1);
  assert.equal(skipped[0].reason, "refusal:send");
  assert.equal(skipped[0].line, 1);
});

test("C4.3 a refused order files no job, is recorded, and stays in the inbox", () => {
  const dir = tmp();
  const inbox = path.join(dir, "inbox.txt");
  const jobsDir = path.join(dir, "jobs");
  // "invoice" would hit the money pattern first, and money is the blunter refusal.
  fs.writeFileSync(inbox, "pax: email the board\n");
  const r = dropOrders(inbox, jobsDir);
  assert.equal(r.jobs.length, 0);
  assert.equal(fs.readdirSync(jobsDir).length, 0);
  const rec = JSON.parse(fs.readFileSync(inbox + ".refusals.jsonl", "utf8").trim());
  assert.equal(rec.reason, "refusal:send");
  assert.match(rec.says, /send anything/i);
  assert.match(fs.readFileSync(inbox, "utf8"), /email the board/);
});
