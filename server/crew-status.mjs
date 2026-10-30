// Read-only crew status for the Command view's loop feed.
//
// The Meta Imperium agent crew (server/queue/patrol.py + crew.py,
// docs/AGENT_CREW.md) writes its records as files in the crew data
// directory (TRIO_CREW_DATA_DIR, default server/queue/crew-data):
// a patrol heartbeat (crew-status.json), an append-only event feed
// (events.jsonl), incident records (incidents.json), and the
// SIMULATED dispatch log (dispatches.jsonl). This module only READS
// those files and projects them into the JSON the loop feed polls.
// It writes nothing, starts nothing, and fabricates nothing: when
// the crew has not run (no directory, no files), the answer says so
// (available: false) instead of inventing an idle state.

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const CREW_DATA_DIR = process.env.TRIO_CREW_DATA_DIR
  ? path.resolve(process.env.TRIO_CREW_DATA_DIR)
  : path.resolve(path.dirname(fileURLToPath(import.meta.url)), "queue", "crew-data");

const MAX_EVENTS = 40;
const MAX_INCIDENTS = 20;

async function readJson(file, fallback) {
  try {
    const parsed = JSON.parse(await readFile(file, "utf8"));
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

async function readJsonlTail(file, limit) {
  let text;
  try {
    text = await readFile(file, "utf8");
  } catch {
    return [];
  }
  const out = [];
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      out.push(JSON.parse(trimmed));
    } catch {
      // a torn final line is skipped, never fatal — mirrors crew_records.py
    }
  }
  return out.slice(-limit);
}

function projectIncident(record) {
  return {
    id: record.id,
    status: record.status,
    created_at: record.created_at,
    camera_id: record.camera?.id ?? null,
    camera_name: record.camera?.name ?? null,
    area: record.camera?.area ?? null,
    division: record.division,
    category: record.category,
    priority: record.priority,
    steps: Array.isArray(record.timeline) ? record.timeline.length : 0,
    receipt_id:
      [...(record.timeline ?? [])].reverse().find((s) => s.step === "dispatch")?.receipt_id ?? null,
  };
}

export async function readCrewStatus(dataDir = CREW_DATA_DIR) {
  const patrol = await readJson(path.join(dataDir, "crew-status.json"), null);
  const events = await readJsonlTail(path.join(dataDir, "events.jsonl"), MAX_EVENTS);
  const incidentsById = await readJson(path.join(dataDir, "incidents.json"), {});
  const dispatches = await readJsonlTail(path.join(dataDir, "dispatches.jsonl"), 500);
  const incidents = Object.values(incidentsById ?? {})
    .sort((a, b) => String(b.created_at ?? "").localeCompare(String(a.created_at ?? "")))
    .slice(0, MAX_INCIDENTS)
    .map(projectIncident);
  const available = patrol !== null || events.length > 0 || incidents.length > 0;
  return {
    available,
    reason: available
      ? null
      : "no crew records yet — the patrol worker has not written to the crew data directory",
    simulated_dispatch: true,
    patrol,
    events: events.reverse(), // newest first for the feed
    incidents,
    dispatches: {
      count: dispatches.length,
      last: dispatches.length
        ? { receipt_id: dispatches[dispatches.length - 1].receipt_id ?? null,
            received_at: dispatches[dispatches.length - 1].received_at ?? null }
        : null,
    },
  };
}
