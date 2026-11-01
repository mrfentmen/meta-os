// Command view: pure formatting for the LOOP FEED panel — the
// agent crew's activity, read from GET /api/crew/status (the crew's
// own records: server/queue/crew_records.py, docs/AGENT_CREW.md).
// No DOM access: safe to import from the browser and node tests,
// like js/command-flag.js.
//
// The feed shows only what the crew actually recorded: patrol
// checks with their real outcomes (including feed errors and
// budget pauses — the loop degrades loudly, never silently),
// review verdicts, reported incidents, investigation runs, and
// dispatch receipts. Dispatch in this system is SIMULATED — the
// dispatch lines say so, every time.

const DIVISION_LABEL = { vigiles: "Vigiles", ignis: "Ignis", medicus: "Medicus" };

export function divisionLabel(productId) {
  return DIVISION_LABEL[productId] ?? productId ?? "—";
}

// Two-tier flag indication (Del's ruling, Oct 31, via Pax): small
// things get a YELLOW indication, big things are RED, baselines get
// none. YELLOW = recorded + shown for human review, no investigation,
// no dispatch. RED = the full flag chain (review, investigation,
// response). The category strings are the js/products.js taxonomy
// strings, matched exactly (lowercased); a category in neither list
// — including baselines like "normal activity" — gets no tier, never
// a guessed one. Rendering only: the crew/harness owns flagging.
const FLAG_TIERS = {
  vigiles: {
    yellow: ["energetic movement", "ambiguous gesture", "staged verbal dispute"],
    red: ["physical contact", "person down", "possible altercation"],
  },
  ignis: {
    yellow: ["visible smoke", "smoldering fire", "obscured or distant hazard",
      "electrical fire indicators", "gas fire indicators",
      "cooking oil fire indicators", "metal fire indicators",
      "battery fire indicators"],
    red: ["visible flame", "vehicle fire", "structure fire", "dark smoke", "brown smoke"],
  },
  medicus: {
    yellow: ["crowd gathered around a person", "blocked crew access",
      "person slumped in vehicle", "bystander aid in progress"],
    red: ["person on ground", "person down in roadway", "person motionless",
      "person in or near water", "person trapped or pinned",
      "blood visible at scene", "vehicle collision scene",
      "multi-person incident scene"],
  },
};

export function flagTier(division, category) {
  const tiers = FLAG_TIERS[division];
  if (!tiers || typeof category !== "string") return null;
  const cat = category.trim().toLowerCase();
  if (tiers.yellow.includes(cat)) return "yellow";
  if (tiers.red.includes(cat)) return "red";
  return null;
}

// One line for one projected crew incident (GET /api/crew/status
// incidents: server/crew-status.mjs). Surfaces what the crew
// recorded and the UI previously dropped: the BOLO block with its
// visible marks, the evidence file counts, and a purge receipt.
// Face crops appear only as a count — never an image, never an
// identity (standing rule: no face-identification work). Absent
// parts stay absent: no BOLO, no evidence, no tier segment.
export function loopIncidentText(incident) {
  if (!incident || typeof incident !== "object") return null;
  const cam = incident.camera_name ?? incident.camera_id ?? "camera";
  const div = divisionLabel(incident.division);
  let text = `Incident — ${cam} · ${div}: ${incident.category ?? ""} (${incident.status ?? "unknown"})`.trim();
  const tier = flagTier(incident.division, incident.category);
  if (tier === "yellow") {
    text += " · YELLOW — recorded for human review, no investigation, no dispatch";
  } else if (tier === "red") {
    text += " · RED — full flag chain";
  }
  const bolo = incident.bolo;
  if (bolo && typeof bolo === "object") {
    const marks = Array.isArray(bolo.visible_marks) ? bolo.visible_marks.filter((m) => typeof m === "string" && m) : [];
    const descriptions = Array.isArray(bolo.person_descriptions) ? bolo.person_descriptions.length : 0;
    text += ` · BOLO: ${marks.length ? marks.join("; ") : "no visible marks recorded"}`;
    if (descriptions) text += ` · ${descriptions} person description${descriptions === 1 ? "" : "s"}`;
    if (typeof bolo.direction_note === "string" && bolo.direction_note) {
      text += ` · direction: ${bolo.direction_note}`;
    }
  }
  if (incident.evidence_purged) {
    text += " · evidence files purged on false-positive close — no person evidence kept";
  } else if (incident.evidence && typeof incident.evidence === "object") {
    text += ` · evidence: ${incident.evidence.files ?? 0} files (${incident.evidence.frames ?? 0} frames, ${incident.evidence.face_crops ?? 0} face crops)`;
  }
  return text;
}

// Incident lines from a status payload: newest first (the endpoint
// already orders them), capped. Unknown/malformed records drop out.
export function loopIncidentItems(payload, limit = 20) {
  const incidents = Array.isArray(payload?.incidents) ? payload.incidents : [];
  const items = [];
  for (const incident of incidents) {
    const text = loopIncidentText(incident);
    if (text === null) continue;
    items.push({
      at: incident.created_at ?? null,
      type: "incident",
      tier: flagTier(incident.division, incident.category),
      text,
    });
    if (items.length >= limit) break;
  }
  return items;
}

// One feed line for one crew event, or null for an event type the
// feed does not render (unknown types are skipped, never guessed).
export function loopEventText(event) {
  if (!event || typeof event !== "object") return null;
  const cam = event.camera_name ?? event.camera_id ?? "camera";
  const div = divisionLabel(event.division);
  switch (event.type) {
    case "patrol-check":
      if (event.outcome === "baseline") {
        return `Patrol — ${cam} · ${div}: ${event.category ?? "baseline"} (no flag)`;
      }
      if (event.outcome === "flagged") {
        return `Patrol — ${cam} · ${div}: FLAGGED ${event.category ?? ""}`.trim();
      }
      if (event.outcome === "feed-error") {
        return `Patrol — ${cam}: feed error (${event.error ?? "snapshot failed"})`;
      }
      if (event.outcome === "job-error" || event.outcome === "assessment-failed") {
        return `Patrol — ${cam} · ${div}: assessment failed (${event.error ?? "no result"})`;
      }
      return `Patrol — ${cam} · ${div}: ${event.outcome ?? "checked"}`;
    case "flag":
      return `Flag raised — ${cam} · ${div}: ${event.category ?? ""} (${event.priority ?? "low"} priority)`;
    case "review":
      if (event.verdict === "confirmed") {
        return `Review — ${cam}: second reading CONFIRMED the flag (${event.category ?? ""})`;
      }
      if (event.verdict === "cleared") {
        return `Review — ${cam}: flag CLEARED as a look-alike (${event.category ?? "baseline"})`;
      }
      return `Review — ${cam}: inconclusive — flag stays for human review`;
    case "incident":
      return `Incident REPORTED — ${cam} · ${div}: ${event.category ?? ""} (${event.priority ?? "low"} priority)`;
    case "orchestrator":
      return `Orchestrator — ${cam} · ${div}: ${event.decision ?? "decision"} (${event.actions ?? 0} actions) — ${event.reason ?? ""}`.trim();
    case "investigation":
      return `Investigation — ${cam}: ${event.calls ?? 0} extra checks, ${event.flags_found ?? 0} further flags`;
    case "dispatch":
      if (event.error) {
        return `Dispatch (SIMULATED) — ${cam}: endpoint error (${event.error})`;
      }
      return `Dispatch (SIMULATED) — ${cam}: package logged, receipt ${event.receipt_id ?? "—"} — no real service contacted`;
    case "patrol-status":
      if (event.state === "paused-budget") {
        return "Patrol PAUSED — test budget reserve reached; the crew files no jobs until the guardrail state changes";
      }
      return `Patrol status — ${event.state ?? "unknown"}`;
    default:
      return null;
  }
}

// Feed items from a status payload: newest first (the endpoint
// already orders them), capped, unknown event types dropped.
export function loopFeedItems(payload, limit = 12) {
  const events = Array.isArray(payload?.events) ? payload.events : [];
  const items = [];
  for (const event of events) {
    const text = loopEventText(event);
    if (text === null) continue;
    items.push({ at: event.at ?? null, type: event.type, text });
    if (items.length >= limit) break;
  }
  return items;
}

// The one-line crew status above the feed. Honest states only: no
// payload yet, endpoint silent, crew never ran, patrol paused, or
// patrol running with its real counts and camera-list source.
export function loopStatusText(payload) {
  if (payload === null || payload === undefined) return "Loop feed — waiting for the crew status endpoint…";
  if (payload.unreachable) {
    return "Loop feed UNAVAILABLE — the crew status endpoint did not answer. The crew may not be running on this stack.";
  }
  if (!payload.available) {
    return "Loop feed — no crew records yet. The patrol worker has not run on this stack.";
  }
  const patrol = payload.patrol;
  if (!patrol) return "Loop feed — crew records exist; no patrol heartbeat yet.";
  const counts = patrol.counts ?? {};
  const source =
    patrol.camera_source === "fallback-subset"
      ? "offline camera list"
      : patrol.camera_source === "nyctmc-live"
        ? "live NYCTMC list"
        : (patrol.camera_source ?? "unknown source");
  if (patrol.state === "paused-budget") {
    return `Patrol PAUSED (budget) — ${counts.checks ?? 0} checks, ${counts.reported ?? 0} reported · ${source}`;
  }
  return `Patrol ${patrol.state ?? "unknown"} — ${counts.checks ?? 0} checks · ${counts.baseline ?? 0} baseline · ${counts.reported ?? 0} reported · ${counts.feed_errors ?? 0} feed errors · ${source}`;
}
