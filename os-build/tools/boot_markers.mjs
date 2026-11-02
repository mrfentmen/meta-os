#!/usr/bin/env node
// CB-074 — report which claim markers a serial log carries.
import fs from "node:fs";

export const MARKERS = [
  "META OS 0.1 (K6)",
  "META OS KERNEL - alive (K1)",
  "HELLO FROM USERSPACE",
  "user exit code 0",
  "sleeper: before sleep",
  "crasher: about to read zero",
  "readkey: enter seen",
  "readkey got 30",
  "Mrfentmen@metaos",
  "OS: Meta OS 0.1 (K6) x86_64",
  "STATUS tasks",
  "user bad syscall 99 refused",
];

export function scan(text) {
  return MARKERS.map((marker) => ({ marker, present: text.includes(marker) }));
}

export function report(text) {
  const rows = scan(text);
  const missing = rows.filter((r) => !r.present);
  return {
    rows,
    present: rows.length - missing.length,
    missing: missing.map((r) => r.marker),
  };
}

export function main(argv) {
  const file = argv[0];
  if (!file) {
    console.error("usage: boot_markers.mjs <serial-log>");
    process.exitCode = 2;
    return;
  }
  const result = report(fs.readFileSync(file, "utf8"));
  console.log("boot markers: " + result.present + "/" + result.rows.length + " present");
  for (const row of result.rows) console.log((row.present ? "  PRESENT " : "  MISSING ") + row.marker);
  if (result.missing.length) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
