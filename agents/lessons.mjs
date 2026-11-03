// The Graft — the boss's rule (2026-10-26): "one agent learns, the
// whole crew levels up." A FEATURE of the agent layer, not a product.
// Lessons are append-only, shared by every agent, and the newest
// ones ride into every brief at spawn — an agent opens its eyes
// already knowing what the crew learned without it.
import fs from "node:fs";

export function lessonsFile(root) { return root + "/lessons.jsonl"; }

export function teach(root, agent, text) {
  // CB-390: a lesson with no text teaches nothing, and an empty line is what every
  // other agent would read as a lesson the crew never learned. Refuse it here, by name,
  // before the file is opened -- nothing is written and the caller sees why.
  if (typeof text !== "string" || text.trim() === "") {
    throw new Error("lesson refused: empty text");
  }
  if (typeof agent !== "string" || agent.trim() === "") {
    throw new Error("lesson refused: empty agent");
  }
  const line = JSON.stringify({ ts: new Date().toISOString(), agent, text }) + "\n";
  const file = lessonsFile(root);
  // If the last writer died mid-append, the file does not end in a newline and appending would
  // fuse the new lesson into the torn one. One separator byte keeps the new record whole.
  try {
    const st = fs.statSync(file);
    if (st.size) {
      const fd = fs.openSync(file, "r");
      const b = Buffer.alloc(1);
      fs.readSync(fd, b, 0, 1, st.size - 1);
      fs.closeSync(fd);
      if (b[0] !== 0x0a) fs.appendFileSync(file, "\n");
    }
  } catch { /* no file yet */ }
  fs.appendFileSync(file, line);
  return line;
}

export function lessons(root, limit = 20) {
  // A single corrupted line must not erase the crew's shared memory. The old reader parsed the
  // whole file in one map(), so one bad byte made every lesson disappear -- an agent then opened
  // its eyes knowing nothing and could not tell why (R11-290). Torn lines are skipped and
  // counted by lessonsHealth(); valid lessons keep riding into the brief.
  try {
    const all = [];
    for (const line of fs.readFileSync(lessonsFile(root), "utf8").split("\n")) {
      if (!line) continue;
      try { all.push(JSON.parse(line)); } catch { /* quarantined: skipped, not repaired */ }
    }
    return all.slice(-limit);
  } catch { return []; }
}

export function lessonsHealth(root) {
  try {
    let good = 0, torn = 0;
    for (const line of fs.readFileSync(lessonsFile(root), "utf8").split("\n")) {
      if (!line) continue;
      try { JSON.parse(line); good += 1; } catch { torn += 1; }
    }
    return { good, torn };
  } catch { return { good: 0, torn: 0 }; }
}
