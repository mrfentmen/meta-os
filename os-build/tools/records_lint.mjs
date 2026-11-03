#!/usr/bin/env node
// CB-078 — report-only header lint for os-build/records/*.md.
// Required: a title, a date, and a scope/source line. No record is edited.
import fs from "node:fs";
import path from "node:path";

export function lintText(text) {
  const errors = [];
  const lines = text.split(/\r?\n/);
  const first = lines.find((line) => line.trim() !== "");
  if (!first || !first.startsWith("# ")) errors.push("title: first non-empty line must start '# '");
  const head = lines.slice(0, 10).join("\n");
  if (!/2026-\d{2}-\d{2}/.test(head) && !/^Date:/m.test(head)) errors.push("date: expected 2026-..-.. or Date: in the first 10 lines");
  if (!/^Scope:/m.test(head) && !/^Source:/m.test(head) && !/^## (Scope|Source|What)/m.test(head)) {
    errors.push("scope: expected Scope:, Source: or a Scope/Source/What heading");
  }
  return errors;
}

export function lintDir(dir) {
  const rows = [];
  for (const name of fs.readdirSync(dir).filter((n) => n.endsWith(".md")).sort()) {
    const file = path.join(dir, name);
    rows.push({ file: name, errors: lintText(fs.readFileSync(file, "utf8")) });
  }
  return rows;
}

export function main(argv) {
  const dir = argv[0] || "os-build/records";
  const rows = lintDir(dir);
  const bad = rows.filter((r) => r.errors.length);
  console.log("records: " + rows.length + ", complete: " + (rows.length - bad.length) + ", incomplete: " + bad.length);
  for (const row of bad) console.log("  " + row.file + " — " + row.errors.join("; "));
  console.log("report only: no record was edited");
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
