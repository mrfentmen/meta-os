// Meta Nervus — the model inspector (R11-262).
//
// Reads a LOCAL model directory and reports what is actually on disk: architecture from the
// config, layer count from the config, and the exact size of every weight file. It does not load
// tensors, allocate a model, or infer anything the files do not say. When the config is missing or
// unreadable it refuses with a code, because "0 layers" for a missing config is a lie shaped like
// a measurement.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export class InspectError extends Error {}

const WEIGHTS = /\.(safetensors|bin|pt|gguf|onnx)$/i;

export function inspectModel(dir) {
  const base = path.resolve(dir);
  let st;
  try { st = fs.statSync(base); } catch { throw new InspectError("inspect: model directory does not exist: " + base); }
  if (!st.isDirectory()) throw new InspectError("inspect: not a directory: " + base);

  const configFile = path.join(base, "config.json");
  if (!fs.existsSync(configFile)) throw new InspectError("inspect: no config.json in " + base);
  let config;
  try { config = JSON.parse(fs.readFileSync(configFile, "utf8")); }
  catch (err) { throw new InspectError("inspect: config.json is not JSON: " + String(err.message || err)); }

  const files = [];
  for (const e of fs.readdirSync(base, { withFileTypes: true })) {
    if (!e.isFile() || !WEIGHTS.test(e.name)) continue;
    files.push({ name: e.name, bytes: fs.statSync(path.join(base, e.name)).size });
  }
  files.sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));

  const layers = config.num_hidden_layers ?? config.n_layer ?? config.num_layers ?? null;
  if (layers != null && (!Number.isInteger(layers) || layers < 1)) {
    throw new InspectError("inspect: config names an invalid layer count: " + layers);
  }

  // The hash identifies THIS directory's weights: file names and sizes, plus the config text.
  // It is not a model checksum, and the field is labelled `inspection_hash` in the record so
  // nobody can cite it as one.
  const h = crypto.createHash("sha256");
  h.update(JSON.stringify({ config, files }));
  const inspection_hash = h.digest("hex").slice(0, 16);

  return {
    dir: base,
    architecture: (config.architectures && config.architectures[0]) || config.model_type || "unknown",
    layer_count: layers,
    hidden_size: config.hidden_size ?? null,
    files,
    total_bytes: files.reduce((n, f) => n + f.bytes, 0),
    inspection_hash,
    note: "read from config.json and the file sizes on disk; no tensor was loaded and no weight was interpreted",
  };
}
