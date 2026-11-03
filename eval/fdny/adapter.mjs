// Meta FDNY eval adapter (first slice).
//
// The FDNY world pack on main is status "partial": a definition plus
// exactly one built runtime, the PAR clock
// (os/worlds/fdny/runtime/par_clock.py). Every other declared watcher
// remains definition only, and nothing here runs a real fire
// department, directs real crews, or replaces any accountability
// system. What this harness scores, from committed material only:
//
//   - os/worlds/validate_pack.py must accept os/worlds/fdny/pack.json;
//   - watchers, agents, alerts, firstboot fields, and urgency classes
//     must match the committed pack.json exactly;
//   - privacy must hold structurally: an alert crosses the bus only
//     when its privacy class is summary, and every cross-world send
//     must declare a non-empty never_carries list;
//   - cross-world declarations must be checked BOTH ways. This is
//     where the pack is honestly partial in a second sense: both
//     FDNY sends are reciprocated (hospital and ems both declare
//     receiving incoming-casualty-summary from fdny), but only 2 of
//     3 FDNY receives are: ems declares NO transport-status send to
//     fdny (it sends multi-casualty-summary to fdny instead, and
//     transport-status only to nypd). The scenario passes when the
//     measurement matches that committed reality, and the gap is
//     named in the evidence and the README, not hidden and not
//     fixed by inventing a send on the other side.
//   - the PAR clock itself is smoke-tested for real, with its own
//     --now fake clock, in a temporary directory: enter a crew,
//     tick inside the grace window (par-check-due warning, no
//     ALERT line), tick past it (crew-unaccounted critical plus
//     the frozen FND-020 ALERT line), tick again (silent: dedupe).
//     No real crew, no radio, no sensors, no bus post.
//
// The harness NEVER dispatches a unit, never orders a crew, never
// carries member or patient information: every value it reads is a
// pack declaration, and the only identifiers in play are crew ids
// in the smoke test's temporary state file. No live feed, no model
// call. This is distinct from eval/ignis (the Trio Ignis app);
// FDNY here is the fire-department world pack.

import { readFileSync, readdirSync, existsSync, mkdtempSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";

export const FDNY_PACK_REL = "os/worlds/fdny/pack.json";
export const FDNY_DOC_REL = "os/worlds/fdny/PACK.md";
export const VALIDATOR_REL = "os/worlds/validate_pack.py";
export const PAR_CLOCK_REL = "os/worlds/fdny/runtime/par_clock.py";
export const WORLDS = ["hospital", "ems", "nypd", "mta", "dsny", "doe", "dep"];

function readJson(root, rel) {
  return JSON.parse(readFileSync(join(root, rel), "utf8"));
}

function readText(root, rel) {
  return readFileSync(join(root, rel), "utf8");
}

export function loadFdnyData(root) {
  const pack = readJson(root, FDNY_PACK_REL);
  const doc = readText(root, FDNY_DOC_REL);
  const others = {};
  for (const w of WORLDS) {
    try {
      others[w] = readJson(root, `os/worlds/${w}/pack.json`);
    } catch {
      others[w] = null;
    }
  }
  const dirFiles = readdirSync(join(root, "os/worlds/fdny")).sort();
  return { pack, doc, others, dirFiles };
}

function fail(evidence) {
  return { pass: false, evidence };
}

function ok(evidence) {
  return { pass: true, evidence };
}

const CHECKS = {
  "validator-clean"(data, expected, root) {
    let stdout = "";
    try {
      stdout = execFileSync("python3", [join(root, VALIDATOR_REL), join(root, FDNY_PACK_REL)], { encoding: "utf8" });
    } catch (err) {
      return fail(`validate_pack.py exited ${err.status}: ${(err.stdout || "") + (err.stderr || "")}`.trim());
    }
    // The validator CLI prints "<path>: OK" per valid manifest (or
    // nothing when given no arguments); either is a clean pass.
    if (stdout.trim() !== "" && !stdout.trim().endsWith(": OK")) {
      return fail(`validator printed unexpected output: ${stdout.trim()}`);
    }
    return ok(`validate_pack.py accepts os/worlds/fdny/pack.json (exit 0, ${expected.errors.length} errors)`);
  },
  "watchers-agents"(data, expected) {
    const watcherIds = data.pack.watchers.map((w) => w.id);
    if (JSON.stringify(watcherIds) !== JSON.stringify(expected.watchers)) {
      return fail(`watchers ${watcherIds.join(",")}, expected ${expected.watchers.join(",")}`);
    }
    const nicks = data.pack.agents.map((a) => a.nick);
    if (JSON.stringify(nicks) !== JSON.stringify(expected.agents)) {
      return fail(`agents ${nicks.join(",")}, expected ${expected.agents.join(",")}`);
    }
    for (const agent of data.pack.agents) {
      const bad = agent.serves.filter((s) => !watcherIds.includes(s));
      if (bad.length > 0) return fail(`${agent.nick} serves unknown watcher(s): ${bad.join(",")}`);
    }
    const serves = Object.fromEntries(data.pack.agents.map((a) => [a.nick, a.serves]));
    for (const [nick, want] of Object.entries(expected.serves)) {
      if (JSON.stringify(serves[nick]) !== JSON.stringify(want)) {
        return fail(`${nick} serves ${JSON.stringify(serves[nick])}, expected ${JSON.stringify(want)}`);
      }
    }
    return ok(`4 watchers, 4 agents, every serves entry resolves; accountability-watcher and handoff-messenger serve 2 each, the others 1 each`);
  },
  "alerts-shape"(data, expected) {
    const kinds = data.pack.alerts.map((a) => a.kind);
    if (JSON.stringify(kinds) !== JSON.stringify(expected.kinds)) {
      return fail(`alert kinds ${kinds.join(",")}, expected ${expected.kinds.join(",")}`);
    }
    for (const alert of data.pack.alerts) {
      if (!expected.severities.includes(alert.severity)) return fail(`${alert.kind} severity ${alert.severity} outside the shared set`);
      if (!expected.privacy.includes(alert.privacy)) return fail(`${alert.kind} privacy ${alert.privacy} outside the shared set`);
      if (!expected.urgency.includes(alert.urgency)) return fail(`${alert.kind} urgency ${alert.urgency} outside the shared set`);
      if (!/^[a-z0-9][a-z0-9-]*$/.test(alert.kind)) return fail(`${alert.kind} is not a single lowercase token`);
    }
    const ranks = data.pack.urgency.map((u) => u.rank).sort();
    if (JSON.stringify(ranks) !== JSON.stringify(expected.ranks)) {
      return fail(`urgency ranks ${ranks.join(",")}, expected ${expected.ranks.join(",")}`);
    }
    return ok(`4 alerts, kinds/severity/privacy/urgency all inside the shared sets, urgency ranks 1-4 exactly once each`);
  },
  "privacy-crossing"(data, expected) {
    for (const alert of data.pack.alerts) {
      const crosses = alert.crosses_bus;
      const isSummary = alert.privacy === "summary";
      if (crosses !== isSummary) {
        return fail(`${alert.kind}: crosses_bus=${crosses} but privacy=${alert.privacy}; crossing requires summary`);
      }
    }
    const crossing = data.pack.alerts.filter((a) => a.crosses_bus).map((a) => a.kind);
    const local = data.pack.alerts.filter((a) => !a.crosses_bus).map((a) => a.kind);
    if (JSON.stringify(crossing) !== JSON.stringify(expected.crossing) || JSON.stringify(local) !== JSON.stringify(expected.local)) {
      return fail(`crossing ${crossing.join(",")}, local ${local.join(",")}`);
    }
    return ok(`crossing == summary: ${crossing.join(", ")} crosses; ${local.join(", ")} stay local`);
  },
  "sends-never-carries"(data, expected) {
    const sends = data.pack.cross_world.sends;
    if (sends.length !== expected.count) return fail(`${sends.length} sends, expected ${expected.count}`);
    for (const send of sends) {
      if (!Array.isArray(send.never_carries) || send.never_carries.length === 0) {
        return fail(`send to ${send.to} (${send.kind}) declares no never_carries list`);
      }
      for (const must of expected.mustNeverCarry) {
        if (!send.never_carries.includes(must)) return fail(`send to ${send.to} (${send.kind}) never_carries misses "${must}"`);
      }
    }
    return ok(`all ${sends.length} sends declare a non-empty never_carries list including patient names, patient identifiers, member names, and medical details of any individual`);
  },
  "reciprocity"(data, expected) {
    const recv = data.pack.cross_world.receives.map((r) => {
      const src = data.others[r.from];
      const match = src && src.cross_world.sends.some((s) => s.to === "fdny" && s.kind === r.kind);
      return { from: r.from, kind: r.kind, match: Boolean(match) };
    });
    const sent = data.pack.cross_world.sends.map((s) => {
      const dst = data.others[s.to];
      const match = dst && dst.cross_world.receives.some((r) => r.from === "fdny" && r.kind === s.kind);
      return { to: s.to, kind: s.kind, match: Boolean(match) };
    });
    const recvMatched = recv.filter((r) => r.match).length;
    const sentMatched = sent.filter((s) => s.match).length;
    const unrecipRecv = recv.filter((r) => !r.match).map((r) => `${r.from}:${r.kind}`);
    const unrecipSent = sent.filter((s) => !s.match).map((s) => `${s.to}:${s.kind}`);
    const expectedUnrecipRecv = (expected.unreciprocatedReceives || []).map((r) => `${r.from}:${r.kind}`);
    const expectedUnrecipSent = (expected.unreciprocatedSends || []).map((s) => `${s.to}:${s.kind}`);
    if (recvMatched !== expected.receivesMatched || recv.length !== expected.receivesTotal ||
        sentMatched !== expected.sendsMatched || sent.length !== expected.sendsTotal ||
        JSON.stringify(unrecipRecv) !== JSON.stringify(expectedUnrecipRecv) ||
        JSON.stringify(unrecipSent) !== JSON.stringify(expectedUnrecipSent)) {
      return fail(`receives ${recvMatched}/${recv.length}, sends ${sentMatched}/${sent.length}, unreciprocated receives ${unrecipRecv.join(",")}, unreciprocated sends ${unrecipSent.join(",")}`);
    }
    return ok(`receives ${recvMatched}/${recv.length} reciprocated; sends ${sentMatched}/${sent.length} reciprocated; GAP named, not hidden: ${unrecipRecv.join(", ")} is declared as received by fdny but no such send is declared by its source pack`);
  },
  "firstboot"(data, expected) {
    const fields = data.pack.firstboot.map((f) => f.field);
    if (JSON.stringify(fields) !== JSON.stringify(expected.fields)) {
      return fail(`firstboot fields ${fields.join(",")}, expected ${expected.fields.join(",")}`);
    }
    for (const f of data.pack.firstboot) {
      if (!f.label || !f.label.trim()) return fail(`firstboot ${f.field} has no label`);
      if (f.required !== expected.required.includes(f.field)) {
        return fail(`firstboot ${f.field} required=${f.required}, expected ${expected.required.includes(f.field)}`);
      }
    }
    return ok(`${fields.length} firstboot fields, all labelled; required: ${expected.required.join(", ")}; optional: battalion only`);
  },
  "status-partial"(data, expected) {
    if (data.pack.status !== expected.status) return fail(`status ${data.pack.status}, expected ${expected.status}`);
    if (data.pack.version !== expected.version) return fail(`version ${data.pack.version}, expected ${expected.version}`);
    if (JSON.stringify(data.dirFiles) !== JSON.stringify(expected.files)) {
      return fail(`os/worlds/fdny holds ${data.dirFiles.join(",")}, expected ${expected.files.join(",")}`);
    }
    if (!data.pack.runtime || data.pack.runtime.status !== expected.runtimeStatus) {
      return fail(`runtime status ${data.pack.runtime && data.pack.runtime.status}, expected ${expected.runtimeStatus}`);
    }
    return ok(`status "partial", version ${expected.version}; os/worlds/fdny holds PACK.md, pack.json, and runtime/ — one built runtime, the rest definition only`);
  },
  "runtime-files"(data, expected, root) {
    const parts = (data.pack.runtime && data.pack.runtime.parts) || [];
    if (parts.length !== expected.count) return fail(`${parts.length} runtime parts declared, expected ${expected.count}`);
    for (const part of parts) {
      const resolved = join(root, "os", part.path);
      if (!existsSync(resolved)) return fail(`declared runtime part ${part.path} does not exist at ${resolved}`);
    }
    return ok(`${parts.length} declared runtime part exists on disk: ${parts.map((p) => p.path).join(", ")} (resolved under os/)`);
  },
  "par-clock-smoke"(data, expected, root) {
    const clock = join(root, PAR_CLOCK_REL);
    const dir = mkdtempSync(join(tmpdir(), "fdny-par-"));
    const stateFile = join(dir, "state.json");
    const run = (args) => execFileSync("python3", [clock, "--file", stateFile, ...args], { encoding: "utf8" });
    try {
      run(["enter", "--crew", "crew-1", "--entered-at", "1000", "--location", "division 2 stairwell"]);
      // Due at 1000 + 600 = 1600; grace runs to 1720. At 1700 the
      // check is due but not yet over: one warning event, no ALERT.
      const dueOut = run(["tick", "--now", "1700"]);
      const dueLines = dueOut.trim() ? dueOut.trim().split("\n") : [];
      if (dueLines.length !== 1) return fail(`tick at 1700 printed ${dueLines.length} lines, expected exactly the par-check-due event`);
      const dueEvent = JSON.parse(dueLines[0]);
      if (dueEvent.kind !== "par-check-due" || dueEvent.severity !== "warning" || dueEvent.crew !== "crew-1") {
        return fail(`tick at 1700 event was ${dueLines[0]}, expected a par-check-due warning for crew-1`);
      }
      // At 1800, past the grace window: the due event is already
      // ledgered, so only crew-unaccounted fires, with its ALERT line.
      const overOut = run(["tick", "--now", "1800"]);
      const overLines = overOut.trim() ? overOut.trim().split("\n") : [];
      if (overLines.length !== 2) return fail(`tick at 1800 printed ${overLines.length} lines, expected the event plus its ALERT line`);
      const overEvent = JSON.parse(overLines[0]);
      if (overEvent.kind !== "crew-unaccounted" || overEvent.severity !== "critical") {
        return fail(`tick at 1800 event was ${overLines[0]}, expected a crew-unaccounted critical event`);
      }
      if (!/^ALERT:\S+ critical crew-unaccounted$/.test(overLines[1])) {
        return fail(`tick at 1800 ALERT line was ${overLines[1]}, expected the frozen FND-020 form`);
      }
      // Same clock, unchanged state: dedupe keeps it silent.
      const againOut = run(["tick", "--now", "1800"]);
      if (againOut.trim() !== "") return fail(`repeat tick at 1800 printed ${againOut.trim()}, expected silence (dedupe)`);
      return ok(`PAR clock smoke: enter at 1000, par-check-due warning at 1700 (no ALERT), crew-unaccounted critical + FND-020 ALERT line at 1800, silent repeat tick (dedupe); state lived only in a temp dir`);
    } catch (err) {
      return fail(`par_clock.py smoke failed: ${(err.stdout || "") + (err.stderr || "") || err.message}`.trim());
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  },
  "doc-agrees"(data, expected) {
    for (const nick of expected.agentNicks) {
      if (!data.doc.includes(nick)) return fail(`PACK.md does not name agent ${nick}`);
    }
    for (const kind of expected.alertKinds) {
      if (!data.doc.includes(kind)) return fail(`PACK.md does not name alert ${kind}`);
    }
    for (const kind of expected.sendKinds) {
      if (!data.doc.includes(kind)) return fail(`PACK.md does not name send ${kind}`);
    }
    return ok(`PACK.md names all 4 agent nicks, all 4 alert kinds, and the incoming-casualty-summary send kind`);
  },
};

export function assessReal(scenario, data, root) {
  const check = CHECKS[scenario.check];
  if (!check) return fail(`unknown check: ${scenario.check}`);
  return check(data, scenario.expected, root);
}

export function runFdnyEval(scenarios, assess, { root }) {
  const data = loadFdnyData(root);
  return scenarios.map((scenario) => {
    const result = assess(scenario, data, root);
    return { scenario, pass: result.pass, evidence: result.evidence };
  });
}

export function formatFdnyReport(records, source) {
  const passed = records.filter((r) => r.pass).length;
  const lines = [
    `Meta FDNY eval — ${source}`,
    `Result: ${passed}/${records.length} scenarios passed.`,
    "",
  ];
  for (const r of records) {
    lines.push(`| ${r.scenario.id} (${r.scenario.title}) | ${r.pass ? "PASS" : "fail"} — ${r.evidence} |`);
  }
  return lines.join("\n");
}
