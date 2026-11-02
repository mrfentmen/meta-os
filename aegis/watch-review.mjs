// Aegis watch-target review ledger (R12-007).
//
// The review is a fill-in record, not a program that decides ownership. For every target in
// aegis/watch-targets.json it emits one row with the two questions a reviewer must answer —
// "still ours" and "still live" — left blank, and the notes column empty. A second review reuses
// the same file shape, so two reviews can be compared line by line.
//
//   node aegis/watch-review.mjs [targets.json] [out.md]
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const targetsFile = process.argv[2] || path.join(root, "aegis", "watch-targets.json");
const outFile = process.argv[3] || path.join(root, "os-build", "aegis", "WATCH_REVIEW.md");
const doc = JSON.parse(fs.readFileSync(targetsFile, "utf8"));
const date = new Date().toISOString().slice(0, 10);

const lines = [];
lines.push("# Aegis watch-target review — " + date);
lines.push("");
lines.push("Generated from `" + path.relative(root, targetsFile) + "` by `aegis/watch-review.mjs`.");
lines.push("**This is a fill-in ledger, not a verdict.** `still ours` is blank on purpose: only a");
lines.push("reviewer can answer it. `liveness` is the checked result from `aegis/check-liveness.mjs` and");
lines.push("is dated in the checked column; ownership is not inferred from liveness.");
lines.push("");
lines.push("| target | type | ref | liveness | still ours | still live | notes | checked |");
lines.push("|---|---|---|---|---|---|---|---|");
for (const t of doc.targets || []) {
  lines.push("| `" + t.id + "` | " + t.type + " | " + t.ref + " | " + t.liveness + " |  |  |  | " + (t.livenessCheckedAt ? String(t.livenessCheckedAt).slice(0, 10) : "") + " |");
}
lines.push("");
lines.push("## Ownership questions for the reviewer");
lines.push("");
lines.push("- A repo is \"still ours\" when the account named in its URL still controls it; a fork is not.");
lines.push("- A page is \"still ours\" when its deployment target and DNS are still controlled by us.");
lines.push("- \"Still live\" is a separate fact: an HTTP status or a repo metadata answer, with the date.");
lines.push("- A dead target is removed with a note, never silently deleted from the list.");
lines.push("");
fs.writeFileSync(outFile, lines.join("\n"));
console.log("watch review: " + (doc.targets || []).length + " targets -> " + path.relative(root, outFile));
