// Session restore for HN-023. Pure: the caller supplies storage,
// the camera list, and the crew incidents, so node tests run
// without a browser. Rule: a reload restores the incident view
// from RECORDS, not from memory state. The saved selection is
// only a pointer (camera + last category/priority + time); on
// load it is validated against the freshly loaded camera list
// AND the freshly fetched crew incidents, and the crew record
// wins — the inspector then renders from that record, never
// from the stale saved category. Unknown camera: restore nothing.

export const RESTORE_KEY = "meta-trio-restore-v1";

export function saveSelection(storage, selection) {
  try {
    if (!selection || typeof selection.cameraId !== "string" || !selection.cameraId) return false;
    storage.setItem(RESTORE_KEY, JSON.stringify({
      cameraId: selection.cameraId,
      category: typeof selection.category === "string" ? selection.category : null,
      priority: typeof selection.priority === "string" ? selection.priority : null,
      at: typeof selection.at === "number" ? selection.at : Date.now(),
    }));
    return true;
  } catch {
    return false;
  }
}

export function loadSelection(storage) {
  try {
    const raw = storage.getItem(RESTORE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    if (typeof parsed.cameraId !== "string" || !parsed.cameraId) return null;
    if (parsed.category !== null && typeof parsed.category !== "string") return null;
    if (parsed.priority !== null && typeof parsed.priority !== "string") return null;
    if (parsed.at !== undefined && typeof parsed.at !== "number") return null;
    return parsed;
  } catch {
    return null;
  }
}

// incidents: crew payload records ({ camera_id, ... }), endpoint
// order newest first — the first match for the camera is the
// record the restored view renders from. Returns null when the
// camera is not in the loaded list (stale pointer, restore
// nothing) — never a guessed camera.
export function resolveSelection(selection, cameraIds, incidents) {
  if (!selection || !Array.isArray(cameraIds) || !cameraIds.includes(selection.cameraId)) return null;
  const list = Array.isArray(incidents) ? incidents : [];
  const incident = list.find((rec) => rec && typeof rec === "object" && rec.camera_id === selection.cameraId) ?? null;
  return { cameraId: selection.cameraId, incident };
}
