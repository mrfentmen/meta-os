// R13-476..490 — the federation drill harness.
//
// There is no federation module in this repo. None. This file is a SIMULATOR: it models the eleven
// named world agents as pure data, dispatches a routine event to each, and hands four events from
// one world to another. Every record it writes carries `simulated: true` and the literal label
// SIMULATED, because a record that could be mistaken for a live routing is worse than no record.
//
// What the drills prove: the harness runs, the handoffs link both ends, and the label survives into
// every line. What they do NOT prove: that any real world agent exists, that anything was dispatched,
// or that any of this is safe to run against a real service. NEURON_SURGERY_SPEC's rule is the same
// rule here — a stub says STUB or it is a lie.
//
//   node federation/sim.mjs
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const OUT = path.join(ROOT, "os-build", "round13", "federation");

export const LABEL = "SIMULATED";

export const WORLDS = {
  nypd: { kind: "police", answers: "unit assigned, scene logged (simulated)" },
  fdny: { kind: "fire", answers: "engine queued, exposure noted (simulated)" },
  ems: { kind: "medical", answers: "medic assigned, ETA logged (simulated)" },
  hospital: { kind: "care", answers: "bed reserved, triage noted (simulated)" },
  dsny: { kind: "sanitation", answers: "route amended, debris noted (simulated)" },
  dep: { kind: "water", answers: "crew queued, main checked (simulated)" },
  doe: { kind: "schools", answers: "transport flagged, school notified (simulated)" },
  mta: { kind: "transit", answers: "service notice drafted (simulated)" },
  musica: { kind: "studio", answers: "session paused, take logged (simulated)" },
  officina: { kind: "fabrication", answers: "bench queued, part logged (simulated)" },
  "science-lab": { kind: "research", answers: "run queued, sample logged (simulated)" },
};

export function createSim({ ledgerFile }) {
  fs.mkdirSync(path.dirname(ledgerFile), { recursive: true });
  const records = [];
  let seq = 0;

  function write(rec) {
    const full = { label: LABEL, simulated: true, seq: seq++, at: new Date().toISOString(), ...rec };
    records.push(full);
    fs.appendFileSync(ledgerFile, JSON.stringify(full) + "\n");
    return full;
  }

  // A routine event: one world receives it and answers. No other world is involved.
  function routine(world, event) {
    const w = WORLDS[world];
    if (!w) throw new Error("unknown world: " + world);
    return write({ drill: "routine", world, kind: w.kind, event, response: w.answers, correlated: null });
  }

  // A handoff: two records, both carrying the same correlation id, so the pair can be joined
  // without trusting either record's position in the file.
  function handoff(from, to, event, note) {
    const a = WORLDS[from], b = WORLDS[to];
    if (!a || !b) throw new Error("unknown world in handoff: " + from + " -> " + to);
    const correlation = "corr-" + seq + "-" + from + "-" + to;
    const first = write({ drill: "handoff", world: from, to, kind: a.kind, event, response: a.answers,
      correlated: correlation, direction: "sent", note });
    const second = write({ drill: "handoff", world: to, from, kind: b.kind, event, response: b.answers,
      correlated: correlation, direction: "received", linked: first.seq, note });
    return { correlation, first, second };
  }

  return { routine, handoff, records, ledgerFile };
}

const DRILLS = [
  ["R13-476", "nypd", "routine", "routine event: noise complaint on a residential block"],
  ["R13-477", "fdny", "routine", "routine event: smoke reported from a basement vent"],
  ["R13-478", "ems", "routine", "routine event: fall on a stairway, one casualty"],
  ["R13-479", "hospital", "routine", "routine event: incoming patient, triage requested"],
  ["R13-480", "dsny", "routine", "routine event: missed collection on a route"],
  ["R13-481", "dep", "routine", "routine event: hydrant pressure below normal"],
  ["R13-482", "doe", "routine", "routine event: school transport delay"],
  ["R13-483", "mta", "routine", "routine event: signal fault on one line"],
  ["R13-484", "musica", "routine", "routine event: session take flagged for review"],
  ["R13-485", "officina", "routine", "routine event: bench part out of tolerance"],
  ["R13-486", "science-lab", "routine", "routine event: run finished with a null result"],
  ["R13-487", "fdny>hospital", "handoff", "incoming patients warning", "fdny warns the hospital of incoming patients"],
  ["R13-488", "nypd>fdny", "handoff", "fire-risk event handed over", "a fire-risk event originates in the nypd world"],
  ["R13-489", "dsny>dep", "handoff", "storm-debris event handed over", "storm debris blocks a drain"],
  ["R13-490", "mta>doe", "handoff", "transit disruption handed over", "school transport depends on the line"],
];

export function runDrills(ledgerFile) {
  const sim = createSim({ ledgerFile });
  const rows = [];
  for (const [task, target, mode, event, note] of DRILLS) {
    if (mode === "routine") {
      const rec = sim.routine(target, event);
      rows.push({ task, mode, target, event, correlation: null, records: [rec.seq], response: rec.response });
    } else {
      const [from, to] = target.split(">");
      const r = sim.handoff(from, to, event, note);
      rows.push({ task, mode, target: from + " -> " + to, event, correlation: r.correlation,
        records: [r.first.seq, r.second.seq], response: r.second.response });
    }
  }
  const allLabelled = sim.records.every((r) => r.label === LABEL && r.simulated === true);
  const handoffs = rows.filter((r) => r.mode === "handoff");
  const linked = handoffs.every((h) => {
    const pair = sim.records.filter((r) => r.correlated === h.correlation);
    return pair.length === 2 && pair[0].correlated === pair[1].correlated;
  });
  return { sim, rows, allLabelled, linked, counts: { drills: rows.length, records: sim.records.length, handoffs: handoffs.length } };
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  fs.mkdirSync(OUT, { recursive: true });
  const ledgerFile = path.join(OUT, "ledger.jsonl");
  fs.rmSync(ledgerFile, { force: true });
  const result = runDrills(ledgerFile);

  fs.writeFileSync(path.join(OUT, "F_DRILLS.json"), JSON.stringify({
    tool: "federation/sim.mjs",
    label: LABEL,
    ran_at: new Date().toISOString(),
    counts: result.counts,
    all_records_labelled_simulated: result.allLabelled,
    handoff_pairs_linked: result.linked,
    rows: result.rows,
    records: result.sim.records,
    what_this_proves: "the drill harness runs, the handoffs link, and the SIMULATED label survives into every record",
    what_this_does_not_prove: "that any world agent exists, that anything was dispatched, or that any routing is exercised",
  }, null, 2) + "\n");

  const table = ["| task | drill | target | records | correlation |", "|---|---|---|---|---|"];
  for (const r of result.rows) {
    table.push("| " + r.task + " | " + r.mode + " | " + r.target + " | " + r.records.join(", ")
      + " | " + (r.correlation || "—") + " |");
  }
  fs.writeFileSync(path.join(OUT, "SECTION_T.md"),
    "# Section T — federation drills (R13-476..490)\n\n"
    + "Run: `node federation/sim.mjs`. Machine record: `F_DRILLS.json`; append-only ledger: `ledger.jsonl`.\n\n"
    + "Counts: " + JSON.stringify(result.counts) + " · all records labelled SIMULATED: " + result.allLabelled
    + " · handoff pairs linked: " + result.linked + "\n\n"
    + "**There is no federation module in this repo.** `federation/sim.mjs` is a simulator over eleven "
    + "named worlds; every record it writes carries `label: \"SIMULATED\"` and `simulated: true`. The "
    + "drills prove the harness and the labelling, not a single real dispatch.\n\n"
    + table.join("\n") + "\n");

  console.log("federation SIMULATED: " + JSON.stringify(result.counts)
    + " labelled=" + result.allLabelled + " linked=" + result.linked);
}
