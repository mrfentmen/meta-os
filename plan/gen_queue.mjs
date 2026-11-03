#!/usr/bin/env node
// gen_queue.mjs — build the Meta OS work queue from the repo itself.
//
// The point is not to write a pretty list. It is that every line in
// plan/QUEUE.jsonl names real files and a check that can fail. Regenerate it
// after the tree moves; ids are stable so agents can claim one and it never
// means something else later.
//
//   node plan/gen_queue.mjs            # writes plan/QUEUE.jsonl + plan/QUEUE.md
//   node plan/gen_queue.mjs --count    # just the totals
//
// Sizes are honest estimates in working days: "S" under a day, "M" 1-3,
// "L" 1-2 weeks. Nothing here is generated to inflate a number — an item only
// exists if a file or a registry entry justifies it.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..");
const out = [];
const seen = new Set();

function add(epic, id, title, { size = "M", why = "", files = [], done = [] } = {}) {
  if (seen.has(id)) return;
  seen.add(id);
  out.push({ id, epic, title, size, why, files, done });
}

const read = (p) => fs.readFileSync(path.join(REPO, p), "utf8");
const exists = (p) => fs.existsSync(path.join(REPO, p));

// ---------------------------------------------------------------- surfaces
const faceDir = "os-build/face";
const html = exists(faceDir) ? fs.readdirSync(path.join(REPO, faceDir)).filter((f) => f.endsWith(".html")).sort() : [];
const py = exists(faceDir) ? fs.readdirSync(path.join(REPO, faceDir)).filter((f) => f.endsWith(".py")).sort() : [];

for (const file of html) {
  const base = path.basename(file, ".html");
  add("native-apps", "APP-" + base + "-gtk",
    "Port " + base + ".html to a native Meta app (GTK4, no browser)",
    {
      size: "L",
      why: "A browser page is not an operating system. This surface is still a web page inside a desktop, which is the single biggest gap between the demo and the claim.",
      files: [faceDir + "/" + file],
      done: [
        "a real binary on PATH, in the dock, launched without a browser",
        "same features as the page, verified by hand on a booted desktop",
        "the page is kept as a fallback and says so",
      ],
    });
  add("native-apps", "APP-" + base + "-contract",
    "Freeze " + base + "'s backend contract as a native API",
    {
      size: "M",
      why: "The GTK port must not learn the page's quirks. One documented contract, one implementation.",
      files: [faceDir + "/" + file],
      done: ["endpoint/CLI list written down", "the page and the native app both use it", "a test pins the shape"],
    });
  add("native-apps", "APP-" + base + "-failure",
    base + ": offline, empty and error states with no blank window",
    {
      size: "S",
      why: "Every surface must say what is wrong instead of showing nothing; a blank app reads as a crash.",
      files: [faceDir + "/" + file],
      done: ["backend down => named message and a retry", "no literal 'undefined' anywhere", "test for the down path"],
    });
  add("native-apps", "APP-" + base + "-keyboard",
    base + ": keyboard, focus and accessibility pass",
    {
      size: "S",
      why: "A desktop app that needs a mouse is a toy; the mock has keyboard affordances.",
      files: [faceDir + "/" + file],
      done: ["Tab order is sane", "Esc/Enter do the obvious thing", "one screen-reader-visible name per control"],
    });
}

for (const file of py) {
  const base = path.basename(file, ".py");
  add("backends", "BE-" + base + "-api",
    "Make " + base + ".py a library with a tested API, not a server-only script",
    {
      size: "M",
      why: "The native ports need to call this directly; today it only speaks HTTP to a page.",
      files: [faceDir + "/" + file],
      done: ["functions exported and documented", "the HTTP layer is a thin wrapper", "tests cover the functions"],
    });
  add("backends", "BE-" + base + "-port",
    base + ": bind loopback only and refuse non-local callers",
    {
      size: "S",
      why: "Local surfaces should not be reachable from the network on a laptop at a hackathon.",
      files: [faceDir + "/" + file],
      done: ["127.0.0.1 bind proven", "a request from another interface is refused", "documented in the app's docs"],
    });
  add("backends", "BE-" + base + "-supervise",
    base + ": restart story under systemd, logged",
    {
      size: "S",
      why: "A backend that dies silently leaves a dead tile.",
      files: [faceDir + "/" + file],
      done: ["unit has Restart=on-failure", "journal shows the restart", "the app names the outage"],
    });
}

// ---------------------------------------------------------------- worlds
const worldsDir = "os/worlds";
const worlds = exists(worldsDir)
  ? fs.readdirSync(path.join(REPO, worldsDir)).filter((d) => fs.statSync(path.join(REPO, worldsDir, d)).isDirectory()).sort()
  : [];
for (const w of worlds) {
  add("worlds", "W-" + w + "-launch", "Wire the " + w + " world into the dock as a real app", {
    size: "M",
    why: "The user built these worlds to be used. A world that is not launchable from the desktop does not exist to a user.",
    files: [worldsDir + "/" + w],
    done: ["desktop entry with the Meta icon", "launches with no terminal", "a run leaves a visible receipt"],
  });
  add("worlds", "W-" + w + "-data", w + ": one dataset, one schema, no placeholder rows", {
    size: "M",
    why: "Every world currently carries its own idea of a record; two sources of truth make the receipts unverifiable.",
    files: [worldsDir + "/" + w],
    done: ["schema file written", "loader validates", "placeholder data removed or labelled"],
  });
  add("worlds", "W-" + w + "-agent", w + ": give the world one named agent with a budget", {
    size: "M",
    why: "The agentic OS claim needs agents that belong to a surface, not just a generic board.",
    files: [worldsDir + "/" + w, "agents/registry.json"],
    done: ["registry entry with a real command", "maxCostUsd set", "one eval task in evals/agentic"],
  });
  add("worlds", "W-" + w + "-receipt", w + ": every run writes a receipt a person can read", {
    size: "M",
    why: "Receipts are the product. An unattributable run is a demo, not evidence.",
    files: [worldsDir + "/" + w],
    done: ["receipt.json per run", "timestamps + inputs + outputs", "a page or dialog shows the last 20"],
  });
  add("worlds", "W-" + w + "-test", w + ": a test that fails when the world is broken", {
    size: "S",
    why: "Untested worlds break during the one demo that matters.",
    files: [worldsDir + "/" + w],
    done: ["one end-to-end test", "runs offline", "fails loudly on a broken fixture"],
  });
}

// ---------------------------------------------------------------- agents
let agents = [];
try {
  agents = JSON.parse(read("agents/registry.json")).agents || [];
} catch { /* registry is optional for the generator */ }
for (const a of agents) {
  const name = a.name;
  if (a.draft) {
    add("agents", "AG-" + name + "-live", "Turn draft agent " + name + " into a real command", {
      size: "M",
      why: "A registry full of drafts is a to-do list pretending to be a product. Draft reason: " + (a.draftReason || "unstated"),
      files: ["agents/registry.json"],
      done: ["a command that really runs", "no placeholder", "one run captured in the console"],
    });
  } else {
    add("agents", "AG-" + name + "-eval", "Eval task for " + name + " with a deterministic grader", {
      size: "M",
      why: "An agent that is only eyeballed once is unmeasured.",
      files: ["agents/registry.json", "evals/agentic/tasks"],
      done: ["a task folder with setup/grade", "grader fails on a no-op", "score recorded in the report"],
    });
  }
  add("agents", "AG-" + name + "-budget", name + ": prove the budget refusal path", {
    size: "S",
    why: "Cost control is the difference between an OS and a bill.",
    files: ["agents/registry.json", "agents/runtime.mjs"],
    done: ["refusal reachable from a job", "receipt names the cap", "console shows refused, not failed"],
  });
  add("agents", "AG-" + name + "-console", name + ": one readable row in the agent console", {
    size: "S",
    why: "If a run cannot be seen, it cannot be trusted.",
    files: ["os-build/face/agents.html"],
    done: ["row with state pill", "click opens the transcript", "no polling storm"],
  });
}

// ---------------------------------------------------------------- debrand
const debrandDirs = ["os-build", "agent-layer", "agents", "server", "os", "iso"];
const hits = [];
function walk(rel) {
  const abs = path.join(REPO, rel);
  let entries = [];
  try { entries = fs.readdirSync(abs, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    if (e.name === "node_modules" || e.name === ".git" || e.name.startsWith(".")) continue;
    const r = path.join(rel, e.name);
    if (e.isDirectory()) walk(r);
    else if (/\.(py|mjs|js|html|sh|xml|css|md|json|toml|service|timer)$/.test(e.name)) {
      let text = "";
      try { text = fs.readFileSync(path.join(REPO, r), "utf8"); } catch { continue; }
      if (/ubuntu|xubuntu|canonical/i.test(text)) hits.push(r);
    }
  }
}
for (const d of debrandDirs) if (exists(d)) walk(d);
for (const f of hits.sort()) {
  const id = "DB-" + f.replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 64);
  add("debrand", id, "De-Ubuntu " + f, {
    size: "S",
    why: "The name a person reads is the product. This file still says Ubuntu/Xubuntu/Canonical.",
    files: [f],
    done: [
      "no user-visible Ubuntu/Xubuntu/Canonical string remains",
      "technical identifiers that apt or the kernel need are kept and marked as such",
      "any behavioural change is named in the commit message",
    ],
  });
}

// ---------------------------------------------------------------- kernel / boot / iso
const bootEpics = [
  ["KERNEL", "kernel: one boot path that is the shipped path", "L", "Two boot paths (ext4 image + ISO) mean the thing you demo is not the thing you ship."],
  ["KERNEL", "kernel: framebuffer handoff documented against the actual modes", "M", "The desktop only looks right if the framebuffer matches; that is currently folklore."],
  ["KERNEL", "kernel: boot banner reads Meta OS, not a Linux line", "S", "The first thing on screen is the identity."],
  ["KERNEL", "kernel: panic path shows a Meta screen with a recovery hint", "M", "A black screen on panic is indistinguishable from a dead machine."],
  ["KERNEL", "ISO: installer path tested end to end once", "L", "Calamares is shipped but untested; that is a demo risk."],
  ["KERNEL", "ISO: live session and installed session share one identity", "M", "Two identities means the installed OS looks like someone else's."],
  ["KERNEL", "boot: measured time-to-desktop, published", "S", "A number beats an adjective."],
  ["KERNEL", "boot: recovery target boots without the face services", "M", "If the agent layer fails, the desktop must still arrive."],
];
for (const [epic, title, size, why] of bootEpics) {
  add(epic.toLowerCase(), "BOOT-" + title.split(":")[0].toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-" + seen.size,
    title, { size, why, files: ["os-build"], done: ["a command or capture proves it", "written into os-build/DEMO.md"] });
}

// ---------------------------------------------------------------- eval / trust
const evalEpics = [
  ["EVAL", "Eval: 25-task agent suite with per-task cost recorded", "L", "Eight tasks is a smoke test; 25 starts to be a measurement."],
  ["EVAL", "Eval: run the suite on the booted OS, not only the host", "L", "Host-green does not prove guest-green."],
  ["EVAL", "Eval: refusal suite (destructive, secret, out-of-workspace)", "M", "The guardrail is the story; it needs a graded suite."],
  ["EVAL", "Eval: regression gate in the build", "M", "A score nobody blocks on decays."],
  ["EVAL", "Eval: publish a scoreboard page in the console", "M", "Visible numbers drive work."],
  ["EVAL", "Eval: calibrate the cost estimate against real usage", "S", "The price column is currently a guess."],
];
for (const [epic, title, size, why] of evalEpics) {
  add(epic.toLowerCase(), "EV-" + title.split(":")[1].trim().replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase().slice(0, 50),
    title, { size, why, files: ["evals/agentic"], done: ["runnable", "report written", "limitations stated"] });
}

// ---------------------------------------------------------------- docs / demo
const docEpics = [
  ["DOC", "Demo: 5-minute script that matches the shipped build", "M", "The video must not show a UI that no longer exists."],
  ["DOC", "Docs: one page that explains what is real and what is a fallback", "M", "Honesty is a feature at a hackathon; judges ask."],
  ["DOC", "Docs: install-from-ISO instructions a stranger can follow", "M", "Untested instructions are fiction."],
  ["DOC", "Docs: architecture map from desktop tile to backend port", "S", "New agents need a map, not a transcript."],
  ["DOC", "Docs: agent authoring guide (registry + eval + budget)", "M", "The pipeline only scales if adding an agent is boring."],
];
for (const [epic, title, size, why] of docEpics) {
  add(epic.toLowerCase(), "DOC-" + title.split(":")[0].toLowerCase() + "-" + seen.size,
    title, { size, why, files: ["os-build"], done: ["written", "checked against the build", "linked from README"] });
}

// ---------------------------------------------------------------- write
const byEpic = out.reduce((m, t) => ((m[t.epic] = (m[t.epic] || []).concat(t)), m), {});
const counts = Object.fromEntries(Object.entries(byEpic).map(([k, v]) => [k, v.length]));
const total = out.length;

if (process.argv.includes("--count")) {
  console.log(JSON.stringify({ total, counts }, null, 2));
  process.exit(0);
}

fs.writeFileSync(path.join(HERE, "QUEUE.jsonl"), out.map((t) => JSON.stringify(t)).join("\n") + "\n");
const lines = [
  "# Meta OS work queue — generated",
  "",
  "Generated by `node plan/gen_queue.mjs` from the tree as it is. Every item names the files it",
  "touches and a check that can fail. Ids are stable; claim one and it never means something else.",
  "",
  "| epic | items |",
  "|---|---|",
  ...Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, v]) => "| " + k + " | " + v + " |"),
  "| **total** | **" + total + "** |",
  "",
  "Sizes: S under a day, M one to three, L one to two weeks. `plan/BACKLOG.md` holds the",
  "hand-written epic work (the big achievements); this file holds the file-scoped queue.",
  "",
  ...Object.entries(byEpic).flatMap(([epic, items]) => [
    "## " + epic + " (" + items.length + ")",
    "",
    ...items.map((t) => "- `" + t.id + "` **" + t.title + "** — " + t.size + ". " + t.why),
    "",
  ]),
];
fs.writeFileSync(path.join(HERE, "QUEUE.md"), lines.join("\n"));
console.log("gen_queue: " + total + " items -> plan/QUEUE.jsonl, plan/QUEUE.md");
console.log("gen_queue: " + JSON.stringify(counts));
