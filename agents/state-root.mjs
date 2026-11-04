// state-root.mjs — where a hosted agent is allowed to write.
//
// The image ships the agent payload under /usr/share/metaos/agent, which is
// root-owned and read-only. Every hosted entry point used to write its ledger
// beside its own source, so in the guest the first mkdir threw EACCES, the
// worker exited 1, and the Agents page called the job "failed (exit 1)" with
// nothing saying why. In a checkout the old behaviour is correct and stays:
// write beside the code, so tests and humans find the files where they always
// were. Only when that directory is NOT writable does this fall back to the
// user's state dir, which is where the relay's own board already lives.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export function isWritable(dir) {
  try {
    fs.accessSync(dir, fs.constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

// `payloadRoot` is the tree the agent shipped in; `label` keeps each agent's
// state apart when they share a fallback (state/oc2-agent/aegis, .../nervus).
export function stateRoot(payloadRoot, label = "") {
  const explicit = process.env.METAOS_AGENT_STATE;
  if (explicit) {
    return label ? path.join(path.resolve(explicit), label) : path.resolve(explicit);
  }
  if (isWritable(payloadRoot)) return payloadRoot;
  const base = process.env.XDG_STATE_HOME || path.join(os.homedir(), ".local", "state");
  return path.join(base, "oc2-agent", label);
}
