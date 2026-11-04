// Meta OS agent layer — unit failure alerts (R2-T3 watchman lane, tasks 65-66).
//
// A failed scheduled unit must name the unit and the reason, and one failure
// must ring exactly once: the alarm is filed through notify.mjs, whose alarm
// key carries a 15-minute dedupe window (WINDOW_MS). Repeating the same
// failure re-records a suppressed line in the journal but rings no second bell.
//
// Key shape:  unit:<unit>:failed   (one key per unit, so unit A's failure
// never suppresses unit B's, and a recovery followed by a new failure rings
// again once the window passes).
import { notify, WINDOW_MS } from "./notify.mjs";

export { WINDOW_MS };

export function unitAlarmKey(unit) {
  return "unit:" + unit + ":failed";
}

export function formatUnitAlarm(unit, reason) {
  if (typeof unit !== "string" || unit.trim() === "") throw new Error("unit_alert: unit is required");
  return {
    severity: "alarm",
    key: unitAlarmKey(unit),
    title: "Unit failed: " + unit,
    body: "unit " + unit + " failed: " + (reason || "no reason recorded"),
  };
}

// Files the alarm; returns the journal record ({suppressed:true} on repeats
// inside the window). The artifact is <root>/notices.jsonl.
export async function alertUnitFailure({ root, unit, reason, now = Date.now(), detail = "" } = {}) {
  if (!root) throw new Error("unit_alert: root is required");
  const alarm = formatUnitAlarm(unit, reason);
  if (detail) alarm.body += " — " + detail;
  return notify({ root, ...alarm, now });
}
