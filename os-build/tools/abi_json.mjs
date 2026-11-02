#!/usr/bin/env node
// CB-095 — read the ABI doc's table as data and emit calls 0-5 plus
// reserved 6-15. kernel/src/user.rs is read as text only; never edited.
import fs from "node:fs";

export function parseAbi(markdown) {
  const calls = [];
  let reserved = [];
  for (const raw of markdown.split(/\r?\n/)) {
    if (!raw.startsWith("|")) continue;
    const cells = raw.split("|").slice(1, -1).map((s) => s.trim());
    if (cells.length < 5) continue;
    if (/^\d+$/.test(cells[0]) && Number(cells[0]) <= 5) {
      calls.push({
        number: Number(cells[0]), name: cells[1],
        args: cells[2], returns: cells[3], notes: cells[4],
      });
    }
    if (cells[0] === "6-15") {
      reserved = Array.from({ length: 10 }, (_, i) => ({
        number: i + 6, name: cells[1], args: cells[2], returns: cells[3], notes: cells[4],
      }));
    }
  }
  return { calls, reserved };
}

export function checkDispatch(abi, source) {
  // The inline match arms are the dispatch: 0 =>, 1 =>, ... 5 =>.
  return abi.calls
    .filter((call) => !new RegExp("\\b" + call.number + "\\s*=>").test(source))
    .map((call) => call.name);
}

export function main(argv) {
  const doc = argv[0] || "os-build/USERSPACE_ABI.md";
  const sourceFile = argv[1] || "kernel/src/user.rs";
  const abi = parseAbi(fs.readFileSync(doc, "utf8"));
  const source = fs.existsSync(sourceFile) ? fs.readFileSync(sourceFile, "utf8") : "";
  const missing = checkDispatch(abi, source);
  console.log(JSON.stringify({ ...abi, dispatch_source: sourceFile, dispatch_missing: missing }, null, 2));
  if (abi.calls.length !== 6 || abi.reserved.length !== 10 || missing.length) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
