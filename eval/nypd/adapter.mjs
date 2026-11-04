// Meta NYPD eval adapter (first slice).
//
// The NYPD world pack on main is status "spec": a definition only
// (os/worlds/nypd/PACK.md + pack.json), no runtime code at all. This
// pack defines no working police system, dispatches no unit, and
// holds no case record, and nothing here changes that. What this
// harness scores, from committed material only:
//
//   - os/worlds/validate_pack.py must accept os/worlds/nypd/pack.json;
//   - watchers, agents, alerts, firstboot fields, and urgency classes
//     must match the committed pack.json exactly;
//   - privacy must hold structurally: an alert crosses the bus only
//     when its privacy class is summary, and every cross-world send
//     must declare a non-empty never_carries list;
//   - privacy classes must match the committed lists: the local_only
//     class (case records, named-officer assignments, the roster
//     with officer names, transcripts and scribe notes, anything
//     identifying a victim, suspect, or witness) never moves, and
//     only road closures, perimeters/hazards, and incident id/type
//     ride the bus_summary class;
//   - cross-world declarations must be checked BOTH ways. This is
//     where the pack is honestly spec-only in a second sense: NONE
//     of NYPD's 3 declared receives is reciprocated by its source
//     pack (fdny sends incoming-casualty-summary only to hospital
//     and ems, never to nypd; ems sends no transport-status to
//     anyone; hospital sends capacity-status only to ems and fdny),
//     and 1 of its 3 sends is unreciprocated (fdny declares no
//     road-closure-summary receive from nypd, while ems does).
//     The scenario passes when the measurement matches that
//     committed reality, and the gaps are named in the evidence and
//     the README, not hidden and not fixed by inventing a send or a
//     receive on the other side.
//   - the doc must agree: PACK.md names the same agents, alerts,
//     and sends, and carries the "SPEC, NOT BUILT" honesty label.
//
// The harness NEVER dispatches a unit, never orders anyone, never
// carries case information or personal identifiers: every value it
// reads is a pack declaration. No live feed, no model call. This is
// distinct from eval/vigiles (the Trio Vigiles app); NYPD here is
// the police-department world pack.

import { readFileSync, readdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";

export const NYPD_PACK_REL = "os/worlds/nypd/pack.json";
export const NYPD_DOC_REL = "os/worlds/nypd/PACK.md";
export const VALIDATOR_REL = "os/worlds/validate_pack.py";
export const WORLDS = ["fdny", "ems", "hospital", "mta", "dsny", "doe", "dep"];

function readJson(root, rel) {
  return JSON.parse(readFileSync(join(root, rel), "utf8"));
}

function readText(root, rel) {
  return readFileSync(join(root, rel), "utf8");
}

export function loadNypdData(root) {
  const pack = readJson(root, NYPD_PACK_REL);
  const doc = readText(root, NYPD_DOC_REL);
  const others = {};
  for (const w of WORLDS) {
    try {
      others[w] = readJson(root, `os/worlds/${w}/pack.json`);
    } catch {
      others[w] = null;
    }
  }
  const dirFiles = readdirSync(join(root, "os/worlds/nypd")).sort();
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
      stdout = execFileSync("python3", [join(root, VALIDATOR_REL), join(root, NYPD_PACK_REL)], { encoding: "utf8" });
    } catch (err) {
      return fail(`validate_pack.py exited ${err.status}: ${(err.stdout || "") + (err.stderr || "")}`.trim());
    }
    // The validator CLI prints "<path>: OK" per valid manifest (or
    // nothing when given no arguments); either is a clean pass.
    if (stdout.trim() !== "" && !stdout.trim().endsWith(": OK")) {
      return fail(`validator printed unexpected output: ${stdout.trim()}`);
    }
    return ok(`validate_pack.py accepts os/worlds/nypd/pack.json (exit 0, ${expected.errors.length} errors)`);
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
    return ok(`3 watchers, 4 agents, every serves entry resolves; liaison-messenger serves 2, the others 1 each`);
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
    return ok(`crossing == summary: no alert crosses; ${local.join(", ")} all stay local`);
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
    return ok(`all ${sends.length} sends declare a non-empty never_carries list including case details, suspect or victim names, any personal identifiers, and record contents`);
  },
  "reciprocity"(data, expected) {
    const recv = data.pack.cross_world.receives.map((r) => {
      const src = data.others[r.from];
      const match = src && src.cross_world.sends.some((s) => s.to === "nypd" && s.kind === r.kind);
      return { from: r.from, kind: r.kind, match: Boolean(match) };
    });
    const sent = data.pack.cross_world.sends.map((s) => {
      const dst = data.others[s.to];
      const match = dst && dst.cross_world.receives.some((r) => r.from === "nypd" && r.kind === s.kind);
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
    return ok(`receives ${recvMatched}/${recv.length} reciprocated; sends ${sentMatched}/${sent.length} reciprocated; GAPS named, not hidden: no source pack declares any of ${unrecipRecv.join(", ")}, and ${unrecipSent.join(", ")} is declared as sent by nypd but no such receive is declared by its destination pack`);
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
    return ok(`${fields.length} firstboot fields, all labelled; required: ${expected.required.join(", ")}; optional: tour_schedule only`);
  },
  "status-spec"(data, expected) {
    if (data.pack.status !== expected.status) return fail(`status ${data.pack.status}, expected ${expected.status}`);
    if (data.pack.version !== expected.version) return fail(`version ${data.pack.version}, expected ${expected.version}`);
    if (JSON.stringify(data.dirFiles) !== JSON.stringify(expected.files)) {
      return fail(`os/worlds/nypd holds ${data.dirFiles.join(",")}, expected ${expected.files.join(",")}`);
    }
    if ("runtime" in data.pack) {
      return fail(`pack declares a runtime key, expected definition only`);
    }
    return ok(`status "spec", version ${expected.version}; os/worlds/nypd holds PACK.md and pack.json only — definition, no runtime`);
  },
  "privacy-classes"(data, expected) {
    const classes = data.pack.privacy_classes;
    if (!classes) return fail(`pack declares no privacy_classes`);
    if (JSON.stringify(classes.local_only) !== JSON.stringify(expected.localOnly)) {
      return fail(`local_only ${JSON.stringify(classes.local_only)}, expected ${JSON.stringify(expected.localOnly)}`);
    }
    if (JSON.stringify(classes.bus_summary) !== JSON.stringify(expected.busSummary)) {
      return fail(`bus_summary ${JSON.stringify(classes.bus_summary)}, expected ${JSON.stringify(expected.busSummary)}`);
    }
    return ok(`privacy classes match: ${classes.local_only.length} local_only items that never move, ${classes.bus_summary.length} bus_summary items that may ride`);
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
    if (!data.doc.includes(expected.honesty)) return fail(`PACK.md does not carry the honesty label ${expected.honesty}`);
    return ok(`PACK.md names all 4 agent nicks, all 4 alert kinds, both send kinds, and carries the ${expected.honesty} honesty label`);
  },
};

export function assessReal(scenario, data, root) {
  const check = CHECKS[scenario.check];
  if (!check) return fail(`unknown check: ${scenario.check}`);
  return check(data, scenario.expected, root);
}

export function runNypdEval(scenarios, assess, { root }) {
  const data = loadNypdData(root);
  return scenarios.map((scenario) => {
    const result = assess(scenario, data, root);
    return { scenario, pass: result.pass, evidence: result.evidence };
  });
}

export function formatNypdReport(records, source) {
  const passed = records.filter((r) => r.pass).length;
  const lines = [
    `Meta NYPD eval — ${source}`,
    `Result: ${passed}/${records.length} scenarios passed.`,
    "",
  ];
  for (const r of records) {
    lines.push(`| ${r.scenario.id} (${r.scenario.title}) | ${r.pass ? "PASS" : "fail"} — ${r.evidence} |`);
  }
  return lines.join("\n");
}
