// Meta OS agent layer — workspace snapshots and instant rollbacks.
//
// Before an agent attempts a complex or destructive operation (install
// script, heavy refactor), it snapshots the workspace; if the operation
// corrupts files, it rolls back to the snapshot instead of failing
// permanently. Snapshots cover: the file tree (content-hashed), the
// process environment, and dependency fingerprints (package manifests,
// not the installed modules themselves).
//
// What this is NOT: live process memory cannot be snapshotted from
// userland — the manifest says so explicitly. Snapshot stores are local
// scratch: never commit a store (it may contain env values).
//
//   node agents/snapshots.mjs snapshot <dir> --store <sdir> [--label x]
//   node agents/snapshots.mjs list --store <sdir>
//   node agents/snapshots.mjs verify <id> --store <sdir>
//   node agents/snapshots.mjs rollback <id> --store <sdir> [--apply] [--target <dir>]
//
// Rollback is a dry-run diff unless --apply is passed. --target defaults
// to the directory the snapshot was taken from; rollback refuses any
// write outside that directory (containment via realpath).

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const DEFAULT_EXCLUDES = new Set(["node_modules", ".git"]);
const MANIFEST_NAME = "manifest.json";
const TREE_NAME = "tree";

function fail(code, message, detail = {}) {
  const err = new Error(message);
  err.name = "SnapshotError";
  err.code = code;
  Object.assign(err, detail);
  throw err;
}

function realDir(p, what) {
  let st;
  try {
    st = fs.statSync(p);
  } catch {
    fail("NOT_FOUND", `${what} not found: ${p}`);
  }
  if (!st.isDirectory()) fail("NOT_DIR", `${what} is not a directory: ${p}`);
  return fs.realpathSync(p);
}

function sha256File(file) {
  const h = crypto.createHash("sha256");
  h.update(fs.readFileSync(file));
  return h.digest("hex");
}

function walkFiles(root, excludes) {
  const out = [];
  const stack = [""];
  while (stack.length) {
    const rel = stack.pop();
    const abs = path.join(root, rel);
    let entries;
    try {
      entries = fs.readdirSync(abs, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const e of entries) {
      const childRel = rel ? `${rel}/${e.name}` : e.name;
        if (excludes.has(e.name)) continue;
      const childAbs = path.join(root, childRel);
      if (e.isSymbolicLink()) continue;
      if (e.isDirectory()) stack.push(childRel);
      else if (e.isFile()) out.push({ rel: childRel, abs: childAbs });
    }
  }
  out.sort((a, b) => (a.rel < b.rel ? -1 : 1));
  return out;
}

function snapshotId() {
  const t = new Date().toISOString().replace(/[:.]/g, "-");
  const rand = crypto.randomBytes(3).toString("hex");
  return `${t}-${rand}`;
}

function depFingerprints(root) {
  const fps = {};
  for (const name of ["package.json", "package-lock.json", "Cargo.lock", "go.mod"]) {
    const f = path.join(root, name);
    if (fs.existsSync(f)) fps[name] = sha256File(f);
  }
  return fps;
}

export function createSnapshot(targetDir, storeDir, options = {}) {
  const root = realDir(targetDir, "target");
  const store = realDir(storeDir, "store");
  const excludes = new Set([...DEFAULT_EXCLUDES, ...(options.exclude || [])]);
  const id = snapshotId();
  const dest = path.join(store, id);
  if (fs.existsSync(dest)) fail("COLLISION", `snapshot id collision: ${id}`);
  const treeDest = path.join(dest, TREE_NAME);
  fs.mkdirSync(treeDest, { recursive: true });

  const files = [];
  for (const { rel, abs } of walkFiles(root, excludes)) {
    // Never snapshot the store into itself when nested under the target.
    if (abs === store || abs.startsWith(store + path.sep)) continue;
    const dst = path.join(treeDest, rel);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(abs, dst);
    const st = fs.statSync(abs);
    files.push({ path: rel, sha256: sha256File(abs), size: st.size, mtimeMs: st.mtimeMs });
  }

  const manifest = {
    version: 1,
    id,
    label: options.label || "",
    createdAt: new Date().toISOString(),
    target: root,
    excludes: [...excludes],
    coverage: "files+env+dep-fingerprints (NOT live process memory)",
    env: { ...process.env },
    deps: depFingerprints(root),
    files,
  };
  fs.writeFileSync(path.join(dest, MANIFEST_NAME), JSON.stringify(manifest, null, 2));
  return { id, files: files.length, dir: dest };
}

export function listSnapshots(storeDir) {
  const store = realDir(storeDir, "store");
  return fs
    .readdirSync(store)
    .filter((n) => {
      try {
        return fs.statSync(path.join(store, n)).isDirectory();
      } catch {
        return false;
      }
    })
    .map((n) => {
      try {
        const m = JSON.parse(fs.readFileSync(path.join(store, n, MANIFEST_NAME), "utf8"));
        return { id: n, label: m.label || "", createdAt: m.createdAt || "", files: (m.files || []).length, target: m.target || "" };
      } catch {
        return { id: n, broken: true };
      }
    })
    .sort((a, b) => (a.id < b.id ? -1 : 1));
}

function loadManifest(store, id) {
  const dir = path.join(store, id);
  let m;
  try {
    m = JSON.parse(fs.readFileSync(path.join(dir, MANIFEST_NAME), "utf8"));
  } catch {
    fail("NO_SNAPSHOT", `no readable snapshot ${id}`);
  }
  if (!Array.isArray(m.files)) fail("CORRUPT", `snapshot ${id} manifest has no file list`);
  return { dir, manifest: m };
}

export function verifySnapshot(storeDir, id) {
  const store = realDir(storeDir, "store");
  const { manifest } = loadManifest(store, id);
  const tree = path.join(store, id, TREE_NAME);
  const bad = [];
  for (const f of manifest.files) {
    const p = path.join(tree, f.path);
    if (!fs.existsSync(p)) {
      bad.push({ path: f.path, problem: "missing-from-store" });
      continue;
    }
    if (sha256File(p) !== f.sha256) bad.push({ path: f.path, problem: "hash-mismatch" });
  }
  return { id, files: manifest.files.length, bad };
}

function containedIn(root, p) {
  const rel = path.relative(root, p);
  return rel !== "" && !rel.startsWith("..") && !path.isAbsolute(rel);
}

export function rollbackDiff(storeDir, id, targetDir = null) {
  const store = realDir(storeDir, "store");
  const { manifest } = loadManifest(store, id);
  const root = targetDir ? realDir(targetDir, "target") : realDir(manifest.target, "snapshot target");
  if (targetDir && realDir(manifest.target, "snapshot target") !== root) {
    fail("TARGET_MISMATCH", `snapshot was taken from ${manifest.target}, not ${root} (pass the original or move it back first)`);
  }
  const tree = path.join(store, id, TREE_NAME);
  const actions = [];
  const current = new Map(walkFiles(root, new Set(manifest.excludes)).map((f) => [f.rel, f.abs]));
  const wanted = new Map(manifest.files.map((f) => [f.path, f]));
  for (const [rel, abs] of current) {
    if (!containedIn(root, abs)) fail("ESCAPE", `refusing to touch path outside target: ${abs}`);
    const w = wanted.get(rel);
    if (!w) {
      actions.push({ op: "delete", path: rel });
      continue;
    }
    if (sha256File(abs) !== w.sha256) actions.push({ op: "restore", path: rel });
  }
  for (const rel of wanted.keys()) {
    if (!current.has(rel)) actions.push({ op: "restore", path: rel });
  }
  return { id, target: root, actions };
}

export function rollbackSnapshot(storeDir, id, options = {}) {
  const { id: sid, target, actions } = rollbackDiff(storeDir, id, options.target || null);
  if (!options.apply) return { id: sid, target, applied: false, actions };
  const store = realDir(storeDir, "store");
  const tree = path.join(store, sid, TREE_NAME);
  for (const a of actions) {
    const dst = path.join(target, a.path);
    if (!containedIn(target, dst)) fail("ESCAPE", `refusing to write outside target: ${dst}`);
    if (a.op === "delete") fs.rmSync(dst, { force: true });
    else {
      fs.mkdirSync(path.dirname(dst), { recursive: true });
      fs.copyFileSync(path.join(tree, a.path), dst);
    }
  }
  return { id: sid, target, applied: true, actions };
}

function parseArgs(argv) {
  const out = { cmd: argv[2] || "", pos: [], flags: {} };
  for (let i = 3; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--apply") out.flags.apply = true;
    else if (a === "--store") out.flags.store = argv[++i];
    else if (a === "--target") out.flags.target = argv[++i];
    else if (a === "--label") out.flags.label = argv[++i];
    else if (!a.startsWith("--")) out.pos.push(a);
  }
  return out;
}

if (process.argv[1] && path.resolve(process.argv[1]) === new URL(import.meta.url).pathname) {
  const { cmd, pos, flags } = parseArgs(process.argv);
  if (!flags.store && cmd !== "help") {
    console.error("usage: snapshots.mjs <snapshot|list|verify|rollback> [--store <dir>] ...");
    process.exit(2);
  }
  try {
    if (cmd === "snapshot") {
      if (!pos[0]) throw new Error("snapshot needs <dir>");
      const r = createSnapshot(pos[0], flags.store, { label: flags.label });
      console.log(`snapshot ${r.id} (${r.files} files)`);
    } else if (cmd === "list") {
      for (const s of listSnapshots(flags.store)) {
        console.log(`${s.id}${s.label ? ` [${s.label}]` : ""} ${s.files ?? "?"} files ${s.target ?? ""}${s.broken ? " BROKEN" : ""}`);
      }
    } else if (cmd === "verify") {
      if (!pos[0]) throw new Error("verify needs <id>");
      const r = verifySnapshot(flags.store, pos[0]);
      console.log(r.bad.length ? `CORRUPT: ${r.bad.length}/${r.files} bad` : `OK: ${r.files}/${r.files} intact`);
      for (const b of r.bad) console.log(`  ${b.problem}: ${b.path}`);
      if (r.bad.length) process.exit(1);
    } else if (cmd === "rollback") {
      if (!pos[0]) throw new Error("rollback needs <id>");
      const r = rollbackSnapshot(flags.store, pos[0], { apply: !!flags.apply, target: flags.target });
      console.log(`${r.applied ? "ROLLED BACK" : "DRY RUN"} ${r.actions.length} actions on ${r.target}`);
      for (const a of r.actions) console.log(`  ${a.op}: ${a.path}`);
    } else {
      console.error("usage: snapshots.mjs <snapshot|list|verify|rollback> [--store <dir>] ...");
      process.exit(2);
    }
  } catch (e) {
    console.error(`${e.name || "Error"}[${e.code || "?"}]: ${e.message}`);
    process.exit(1);
  }
}
