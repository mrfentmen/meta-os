#!/usr/bin/env node
// Meta OS agent layer — contract check CLI.
//
// The contract is language-neutral JSON. A Node agent writes it; a Python MOS worker, a shell
// gate, or a human can check it without importing the loop. Exit 0 means the contract is valid
// AND finished; every other outcome is exit 1 with a machine-readable reason.
//
//   node agents/contract-check.mjs runs/<run>/contract.json
import path from "node:path";
import url from "node:url";
import { canFinish, contractDigest, loadContract, summarizeContract } from "./contract.mjs";

function emit(payload, code) {
  console.log(JSON.stringify(payload));
  process.exit(code);
}

const self = url.fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(self)) {
  const file = process.argv[2];
  if (!file) {
    console.error("usage: contract-check.mjs <contract.json>");
    process.exit(2);
  }
  try {
    const contract = loadContract(path.resolve(file));
    const verdict = canFinish(contract);
    emit(
      {
        ok: verdict.ok,
        code: verdict.code,
        reason: verdict.reason,
        status: contract.status,
        goal: contract.goal,
        summary: summarizeContract(contract),
        digest: contractDigest(contract),
      },
      verdict.ok ? 0 : 1,
    );
  } catch (error) {
    emit(
      {
        ok: false,
        code: (error && error.code) || "contract-error",
        reason: String((error && error.message) || error),
      },
      1,
    );
  }
}
