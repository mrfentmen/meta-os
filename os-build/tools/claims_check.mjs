#!/usr/bin/env node
// CB-094 — check the six demo beats' markers in one log.
import fs from "node:fs";

export const BEATS = [
  { name: "1 boot", markers: ["META OS 0.1 (K6)", "META OS KERNEL - alive (K1)"] },
  { name: "2 ring 3", markers: ["HELLO FROM USERSPACE", "user hello: entry 0x600000000000"] },
  { name: "3 three programs", markers: ["sleeper: before sleep", "crasher: about to read zero"] },
  { name: "4 fault isolation", markers: ["INT user page-fault", "sleeper: after sleep"] },
  { name: "5 shell state", markers: ["STATUS tasks=7", "user bad syscall 99 refused"] },
  { name: "6 imperium receipt", markers: ["receipt_id=sim-6623d237a90b3d9d", "simulated=true"] },
];

export function checkClaims(text) {
  const beats = BEATS.map((beat) => {
    const missing = beat.markers.filter((marker) => !text.includes(marker));
    return { name: beat.name, pass: missing.length === 0, missing };
  });
  return { beats, allPass: beats.every((b) => b.pass) };
}

export function main(argv) {
  if (!argv[0]) { console.error("usage: claims_check.mjs <log>"); process.exitCode = 2; return; }
  const result = checkClaims(fs.readFileSync(argv[0], "utf8"));
  for (const beat of result.beats) {
    console.log((beat.pass ? "PASS " : "MISSING ") + beat.name +
      (beat.missing.length ? " — " + beat.missing.join(", ") : ""));
  }
  if (!result.allPass) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
