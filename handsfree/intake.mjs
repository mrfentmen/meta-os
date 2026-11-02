// Hands-Free C1 — a text inbox becomes watchman job files.
//
// The inbox is lines a person can type: one line, one order, the agent's name before a colon.
// Blank lines and #comments are ignored. A line with no colon is NOT guessed at -- it stays in
// the inbox and is reported, because an order nobody can parse is an order nobody should run.
import fs from "node:fs";
import path from "node:path";

export function parseInbox(text) {
  const jobs = [];
  const skipped = [];
  text.split(/\r?\n/).forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith("#")) return;
    const at = line.indexOf(":");
    if (at <= 0) {
      skipped.push({ line: i + 1, text: line, reason: "no agent before a colon" });
      return;
    }
    const agent = line.slice(0, at).trim();
    const orders = line.slice(at + 1).trim();
    if (!agent || !orders) {
      skipped.push({ line: i + 1, text: line, reason: "empty agent or empty order" });
      return;
    }
    jobs.push({ agent, orders });
  });
  return { jobs, skipped };
}

// Write each order as <id>.job.json, atomically, and mark the lines that were taken. Lines the
// parser refused stay in the inbox: silently deleting them would turn a typo into a lost order.
export function dropOrders(inboxFile, jobsDir, { now = Date.now(), source = "handsfree" } = {}) {
  const text = fs.readFileSync(inboxFile, "utf8");
  const { jobs, skipped } = parseInbox(text);
  fs.mkdirSync(jobsDir, { recursive: true });
  const stamp = new Date(now).toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  const written = [];

  jobs.forEach((j, i) => {
    let id = j.agent + "-" + stamp + "-" + i;
    let bump = 0;
    while (fs.existsSync(path.join(jobsDir, id + ".job.json"))) {
      bump += 1;
      id = j.agent + "-" + stamp + "-" + i + "-" + bump;
    }
    const rec = { id, agent: j.agent, orders: j.orders, filedAt: new Date(now).toISOString(), source };
    const tmp = path.join(jobsDir, id + ".job.json.tmp");
    fs.writeFileSync(tmp, JSON.stringify(rec, null, 2));
    fs.renameSync(tmp, path.join(jobsDir, id + ".job.json"));
    written.push({ id, agent: j.agent });
  });

  if (written.length) {
    fs.appendFileSync(inboxFile + ".done", written.map((w) => JSON.stringify({ ...w, at: new Date(now).toISOString() })).join("\n") + "\n");
  }
  fs.writeFileSync(inboxFile, skipped.length ? skipped.map((s) => s.text).join("\n") + "\n" : "");
  return { jobs: written, skipped };
}
