// Meta Nervus — validate the instrument tray against the gateway's backend list (C2).
//
// A named tool that does not exist is a finding, not a footnote. Exit 1 when the tray names a
// prefix the gateway does not serve, or when two tray entries claim the same prefix.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { validateTray } from "./contracts.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const root = path.basename(HERE) === "nervus" ? path.dirname(HERE) : HERE;
const trayFile = process.argv[2] || path.join(root, "nervus", "tray.json");
const backendsFile = process.argv[3] || path.join(root, "mcp-gateway", "backends.json");

const tray = JSON.parse(fs.readFileSync(trayFile, "utf8"));
const backends = JSON.parse(fs.readFileSync(backendsFile, "utf8"));
const r = validateTray(tray, backends);

console.log("nervus tray: " + r.count + " tool(s), " + (backends.backends || []).length + " gateway backend(s)");
if (r.ok) {
  console.log("  every named prefix exists in mcp-gateway/backends.json; no duplicates");
  process.exit(0);
}
for (const m of r.missing) console.log("  MISSING " + m.tool + " (prefix " + m.prefix + "): " + m.reason);
for (const d of r.duplicates) console.log("  DUPLICATE prefix " + d);
process.exit(1);
