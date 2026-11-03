// Federation, first moment (BUILD WAVE W4, TONIGHT PLANS 2026-11-02):
// one cross-division moment, simulated and labelled everywhere.
//
// When an Ignis flag creates an incident in the one system queue
// (js/command-flag.js), a Medicus incoming-scene notice is derived
// from that incident — same camera, same incident id, same time.
// The notice is NOT a Medicus assessment: it carries no Medicus
// category, no priority, no severity, no triage, no treatment
// language, and it dispatches nothing. It says only that an
// Ignis-flagged scene exists at this camera, so a Medicus operator
// looking at the same camera sees the same scene. Every surface
// that shows it carries the word SIMULATED, and the notice closes
// when its source incident clears or is superseded.
//
// The server trio queue (server/queue.mjs, queue_service.py) is a
// different queue — assessment jobs, not incidents — so this moment
// is deliberately built on the client IncidentQueue, the queue that
// already holds the flag. No new queue, no new endpoint, no real
// service contacted. Pure module: no DOM, safe to import from
// browser and node tests alike.

import { isFlaggedCategory } from "./command-flag.js";

export const FEDERATION_SOURCE_PRODUCT = "ignis";
export const FEDERATION_TARGET_PRODUCT = "medicus";

// The notice text, fixed so no caller can soften the label or add
// a claim the notice does not make. The camera name is supplied by
// the rendering surface, which knows the loaded camera list; the
// notice itself carries only ids, so it can never name a camera it
// was not derived from.
export const FEDERATION_NOTICE_LABEL = "SIMULATED";

export function federationNoticeText(category) {
  return (
    `Incoming scene notice for Medicus (SIMULATED): an Ignis flag is open ` +
    `at this camera — ${category}. Same camera, same time as the Ignis ` +
    `incident. This is a notice only: no Medicus assessment, no dispatch.`
  );
}

// Build the notice for one incident, or null when the incident is
// not an open, flagged Ignis incident. Baseline results, closed or
// superseded incidents, and other divisions never produce one.
export function buildFederationNotice(incident) {
  if (!incident || typeof incident !== "object") return null;
  if (incident.productId !== FEDERATION_SOURCE_PRODUCT) return null;
  if (!incident.open || incident.cleared) return null;
  if (typeof incident.id !== "string" || incident.id.length === 0) return null;
  if (typeof incident.cameraId !== "string" || incident.cameraId.length === 0) return null;
  if (typeof incident.timestamp !== "string" || incident.timestamp.length === 0) return null;
  if (!isFlaggedCategory(FEDERATION_SOURCE_PRODUCT, incident.category)) return null;
  return {
    id: `federation-${incident.id}`,
    kind: "federation-notice",
    simulated: true,
    label: FEDERATION_NOTICE_LABEL,
    sourceProductId: FEDERATION_SOURCE_PRODUCT,
    targetProductId: FEDERATION_TARGET_PRODUCT,
    sourceIncidentId: incident.id,
    cameraId: incident.cameraId,
    category: incident.category,
    timestamp: incident.timestamp,
    text: federationNoticeText(incident.category),
    seen: false,
    open: true,
    cleared: false,
    clearedReason: null,
  };
}

// The notice store: one open notice per (camera, target division),
// derived from the newest open Ignis incident on that camera.
// A second Ignis incident on the same camera supersedes the first
// notice exactly as the IncidentQueue supersedes the first incident.
export class FederationNotices {
  constructor() {
    this._items = [];
    this._seq = 0;
  }

  // All notices this session, newest first (open and closed).
  list() {
    return [...this._items].sort((a, b) => b.seq - a.seq);
  }

  // The open notice for a camera under the target division, or null.
  openForCamera(cameraId, targetProductId = FEDERATION_TARGET_PRODUCT) {
    const open = this._items.filter(
      (notice) => notice.cameraId === cameraId && notice.open && notice.targetProductId === targetProductId,
    );
    return open.sort((a, b) => b.seq - a.seq)[0] ?? null;
  }

  // The open notice derived from one source incident, or null.
  openForSource(sourceIncidentId) {
    return (
      this._items.find((notice) => notice.sourceIncidentId === sourceIncidentId && notice.open) ?? null
    );
  }

  // Derive (or refresh) the notice for an incident. Returns
  // { notice, created } — created is false when the same source
  // incident already has an open notice (its timestamp is refreshed
  // to stay linked to the incident) or when the incident produces
  // no notice at all (notice null).
  add(incident) {
    const built = buildFederationNotice(incident);
    if (!built) return { notice: null, created: false };
    const existing = this.openForSource(incident.id);
    if (existing) {
      existing.timestamp = incident.timestamp;
      existing.category = incident.category;
      existing.text = federationNoticeText(incident.category);
      return { notice: existing, created: false };
    }
    for (const notice of this._items) {
      if (notice.open && notice.cameraId === incident.cameraId && notice.targetProductId === FEDERATION_TARGET_PRODUCT) {
        notice.open = false;
        notice.cleared = true;
        notice.clearedReason = "superseded";
      }
    }
    this._seq += 1;
    const notice = { ...built, seq: this._seq };
    this._items.push(notice);
    return { notice, created: true };
  }

  // Close the notice derived from one source incident (called when
  // that incident clears). Returns the closed notice or null.
  clearForSource(sourceIncidentId) {
    const notice = this.openForSource(sourceIncidentId);
    if (!notice) return null;
    notice.open = false;
    notice.cleared = true;
    notice.clearedReason = "source cleared";
    return notice;
  }

  // Mark one notice seen (operator selected it). Returns it, or
  // null for an unknown id.
  markSeen(id) {
    const notice = this._items.find((item) => item.id === id);
    if (!notice) return null;
    notice.seen = true;
    return notice;
  }
}
