// Meta OS agent layer — notifications (spec §10: speak only on change).
//
// Three sinks, ordered by how much they can hurt:
//   journal  always; an append-only JSONL line under the layer's root
//   desktop  only when a session can show it (notify-send plus a display)
//   webhook  only when METAOS_NOTIFY_WEBHOOK is set; opt-in, timeout-bounded
//
// A repeated alarm with the same key inside the window is recorded as
// suppressed instead of ringing again. A checker that repeats itself teaches
// people to ignore it; this one is quiet until something changes.
//
//   node agents/notify.mjs --root DIR --severity alarm --key k --title "..."
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { spawnSync } from "node:child_process";

export const WINDOW_MS = 15 * 60 * 1000;
export const DEFAULT_CHANNELS = ["journal", "desktop"];
export const SEVERITIES = ["note", "alarm"];

export function noticeFile(root) {
  return path.join(root, "notices.jsonl");
}

export function noticeStateFile(root) {
  return path.join(root, "notices-state.json");
}

function loadState(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return {};
  }
}

// Only alarms are deduplicated: two quiet notes about two different runs are
// both worth keeping, and a note is cheap.
export function shouldSuppress(state, key, severity, now = Date.now(), windowMs = WINDOW_MS) {
  if (severity !== "alarm" || !key) return false;
  const last = state[key];
  return Boolean(last && now - last < windowMs);
}

async function postJson(target, record, timeoutMs = 3000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(target, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(record),
      signal: controller.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

function deliverDesktop(record, deps) {
  const hasDisplay = process.env.DISPLAY || process.env.WAYLAND_DISPLAY;
  if (!hasDisplay) return null;
  const bin = deps.notifySend || "notify-send";
  const args = [
    "--urgency", record.severity === "alarm" ? "critical" : "normal",
    record.title, record.body || "",
  ];
  const run = deps.spawnSync || spawnSync;
  try {
    const result = run(bin, args, { encoding: "utf8" });
    return result && result.status === 0 ? "desktop" : null;
  } catch {
    return null;
  }
}

export async function notify({
  root,
  severity = "note",
  key = null,
  title,
  body = "",
  channels = DEFAULT_CHANNELS,
  now = Date.now(),
  deps = {},
}) {
  if (!SEVERITIES.includes(severity)) {
    throw new Error("notify: severity must be note or alarm");
  }
  if (!title) throw new Error("notify: title is required");

  fs.mkdirSync(root, { recursive: true });
  const statePath = noticeStateFile(root);
  const state = loadState(statePath);
  const suppressed = shouldSuppress(state, key, severity, now);

  const record = {
    ts: new Date(now).toISOString(), severity, key, title, body,
    suppressed, delivered: [],
  };

  if (!suppressed) {
    for (const channel of channels) {
      if (channel === "journal") {
        record.delivered.push("journal");
      } else if (channel === "desktop") {
        const delivered = deliverDesktop(record, deps);
        if (delivered) record.delivered.push(delivered);
      } else if (channel === "webhook") {
        const target = process.env.METAOS_NOTIFY_WEBHOOK;
        if (!target) continue;
        const ok = await (deps.postJson || postJson)(target, record);
        if (ok) record.delivered.push("webhook");
      } else {
        throw new Error("notify: unknown channel " + channel);
      }
    }
    if (key) {
      state[key] = now;
      fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
    }
  }

  fs.appendFileSync(noticeFile(root), JSON.stringify(record) + "\n");
  return record;
}

export function createNotifier(root) {
  return (notice) => notify({ root, ...notice }).catch(() => null);
}

/* ---- CLI ---- */
const HERE = path.dirname(url.fileURLToPath(import.meta.url));
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const arg = (name, fallback = null) => {
    const i = process.argv.indexOf(name);
    return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
  };
  const notice = {
    root: arg("--root", process.cwd()),
    severity: arg("--severity", "note"),
    key: arg("--key"),
    title: arg("--title"),
    body: arg("--body", ""),
  };
  if (!notice.title) {
    console.error("usage: notify.mjs --root DIR --title TEXT [--severity note|alarm] [--key K] [--body TEXT]");
    process.exit(1);
  }
  notify(notice)
    .then((record) => {
      console.log(JSON.stringify(record, null, 2));
      process.exit(record.suppressed ? 0 : 0);
    })
    .catch((error) => {
      console.error("notify: " + ((error && error.message) || error));
      process.exit(1);
    });
}
