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
