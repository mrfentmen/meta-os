// Meta OS agent layer — writes that fail loudly (R11-292).
//
// `fs.writeFileSync` does not tell you how many bytes landed. On a full disk the process gets
// ENOSPC and throws, which is fine; the dangerous case is a short write that returns without an
// error and leaves a record that parses as less than it should be. These wrappers check the
// byte count, throw, and remove the partial file so the next reader sees "missing", never
// "shorter than expected".
import fs from "node:fs";
import path from "node:path";

export class DiskFullError extends Error {}

export function writeFileLoud(file, data, { fsImpl = fs } = {}) {
  const buf = Buffer.isBuffer(data) ? data : Buffer.from(String(data));
  fsImpl.mkdirSync(path.dirname(file), { recursive: true });
  const fd = fsImpl.openSync(file, "w");
  let written;
  try {
    written = fsImpl.writeSync(fd, buf, 0, buf.length, 0);
  } catch (err) {
    try { fsImpl.closeSync(fd); } catch { /* already closed */ }
    try { fsImpl.unlinkSync(file); } catch { /* nothing to remove */ }
    if (err && (err.code === "ENOSPC" || err.code === "EDQUOT")) {
      throw new DiskFullError("disk full writing " + file + " (" + err.code + ")");
    }
    throw err;
  }
  fsImpl.closeSync(fd);
  if (written !== buf.length) {
    try { fsImpl.unlinkSync(file); } catch { /* nothing to remove */ }
    throw new DiskFullError("short write to " + file + ": " + written + " of " + buf.length + " bytes");
  }
  return written;
}

// CB-396: writing the same bytes twice is not an event. The no-change path returns
// changed:false and never opens the file, so its mtime stays put and a watcher does not
// report a change that did not happen. Byte comparison, not a string compare: encoding
// differences must not read as a change either.
export function writeIfChanged(file, data, { fsImpl = fs } = {}) {
  const buf = Buffer.isBuffer(data) ? data : Buffer.from(String(data));
  let current = null;
  try { current = fsImpl.readFileSync(file); } catch { /* no readable file yet */ }
  if (current !== null && current.equals(buf)) return { changed: false, bytes: buf.length };
  writeFileLoud(file, buf, { fsImpl });
  return { changed: true, bytes: buf.length };
}

// CB-397: a write outside the allowed root is refused before the path is opened.
// The check is path.relative, not a string prefix -- "/root-evil/x" must not pass for
// "/root", and a resolved "../" escape must not either.
export function writeWithinRoot(allowedRoot, file, data, { fsImpl = fs } = {}) {
  const root = path.resolve(allowedRoot);
  const target = path.resolve(file);
  const rel = path.relative(root, target);
  if (rel === "" || rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error("write refused: " + target + " is outside " + root);
  }
  return writeFileLoud(target, data, { fsImpl });
}

// Append is the record path; a short append must not look like a written record.
export function appendLoud(file, text, { fsImpl = fs } = {}) {
  const buf = Buffer.from(String(text));
  fsImpl.mkdirSync(path.dirname(file), { recursive: true });
  const fd = fsImpl.openSync(file, "a");
  let written;
  try {
    written = fsImpl.writeSync(fd, buf, 0, buf.length, null);
  } catch (err) {
    try { fsImpl.closeSync(fd); } catch { /* already closed */ }
    if (err && (err.code === "ENOSPC" || err.code === "EDQUOT")) {
      throw new DiskFullError("disk full appending " + file + " (" + err.code + ")");
    }
    throw err;
  }
  fsImpl.closeSync(fd);
  if (written !== buf.length) throw new DiskFullError("short append to " + file + ": " + written + " of " + buf.length);
  return written;
}
