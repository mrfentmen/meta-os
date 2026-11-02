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
