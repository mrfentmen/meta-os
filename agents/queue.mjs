// Meta OS agent layer — the queue package contract (R11-285).
//
// A package is not a file path with a hope attached. It names who it is for, what work it asks
// for, and the picture the work is about; a package missing any of those is refused with the
// missing part named, before anything is spawned. The alternative — accepting it and failing
// inside the agent — turns a bad order into a mysterious worker death.
import fs from "node:fs";
import path from "node:path";
import { writeFileLoud } from "./safe-write.mjs";

export const PACKAGE_REFUSALS = {
  "missing-id": "the package has no id, so no record could point at it",
  "missing-agent": "the package names no agent, so nobody would pick it up",
  "missing-picture": "the package carries no picture and the work is visual",
  "picture-unreadable": "the named picture does not exist on this host",
};

export class PackageError extends Error {}

export function validatePackage(pkg, { root = ".", requirePicture = true } = {}) {
  const errors = [];
  if (!pkg || typeof pkg !== "object") {
    return { ok: false, errors: [{ reason: "not-an-object", detail: "a package must be an object" }] };
  }
  if (typeof pkg.id !== "string" || !pkg.id.trim()) errors.push({ reason: "missing-id", detail: PACKAGE_REFUSALS["missing-id"] });
  if (typeof pkg.agent !== "string" || !pkg.agent.trim()) errors.push({ reason: "missing-agent", detail: PACKAGE_REFUSALS["missing-agent"] });
  if (requirePicture) {
    if (typeof pkg.picture !== "string" || !pkg.picture.trim()) {
      errors.push({ reason: "missing-picture", detail: PACKAGE_REFUSALS["missing-picture"] });
    } else if (!/^data:/.test(pkg.picture) && !/^https?:/.test(pkg.picture)) {
      const abs = path.isAbsolute(pkg.picture) ? pkg.picture : path.resolve(root, pkg.picture);
      if (!fs.existsSync(abs)) {
        errors.push({ reason: "picture-unreadable", detail: PACKAGE_REFUSALS["picture-unreadable"] + ": " + pkg.picture });
      }
    }
  }
  return { ok: errors.length === 0, errors };
}

// Accepted packages land atomically, like job files: a half-written package must never be
// readable as a complete one.
export function acceptPackage(pkg, { queueDir, root = ".", now = () => new Date() } = {}) {
  const check = validatePackage(pkg, { root });
  if (!check.ok) return { ok: false, errors: check.errors };
  const rec = { ...pkg, acceptedAt: now().toISOString(), picture: pkg.picture };
  writeFileLoud(path.join(queueDir, pkg.id + ".package.json"), JSON.stringify(rec, null, 2));
  return { ok: true, path: path.join(queueDir, pkg.id + ".package.json") };
}
