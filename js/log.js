// Evaluation session log (BRIEF.md section 7, v2 contract).
// Every analysis request the UI makes is recorded exactly once: the request
// timestamp, the product it was assessed under, the measured round-trip
// latency, the outcome status, and either the validated response or the
// real error. Entries hold assessments and errors only — never frames or
// image data — and nothing is uploaded; the operator exports the log as
// JSON for the evaluation lane. When a storage adapter is supplied (the
// app passes the browser's localStorage), entries survive a page reload:
// they are restored on construction, saved on every record, and removed
// on clear. A missing, corrupt, or unwritable store never breaks logging:
// the log keeps working in memory. Shape matches the native app's
// SessionLog export (per-entry product plus a top-level product for the
// product active at export time).

export const LOG_STATUSES = ["ok", "network_error", "http_error", "invalid_response"];

export class SessionLog {
  constructor({ nowFn = () => new Date(), storage = null, storageKey = "meta-trio-session-log-v1" } = {}) {
    this._nowFn = nowFn;
    this._storage = storage;
    this._storageKey = storageKey;
    this._entries = [];
    this._seq = 0;
    this._restore();
  }

  // Reloads previously saved entries, keeping only well-formed ones, so a
  // stale or hand-edited store cannot inject an entry the log would never
  // have recorded itself.
  _restore() {
    if (!this._storage) return;
    let raw;
    try {
      raw = this._storage.getItem(this._storageKey);
    } catch {
      return;
    }
    if (typeof raw !== "string" || raw === "") return;
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return;
    }
    if (!Array.isArray(parsed)) return;
    for (const entry of parsed) {
      if (!entry || typeof entry !== "object" || !Number.isInteger(entry.seq) || !LOG_STATUSES.includes(entry.status)) {
        continue;
      }
      this._entries.push(entry);
      if (entry.seq > this._seq) this._seq = entry.seq;
    }
  }

  _save() {
    if (!this._storage) return;
    try {
      this._storage.setItem(this._storageKey, JSON.stringify(this._entries));
    } catch {
      // Private browsing, quota, or a disabled store: in-memory logging
      // continues, and the next reload simply starts from an empty log.
    }
  }

  _removeSaved() {
    if (!this._storage) return;
    try {
      this._storage.removeItem(this._storageKey);
    } catch {
      // Same as _save: clearing the in-memory log still succeeds.
    }
  }

  get count() {
    return this._entries.length;
  }

  // Session stats for the detail view (Del direction 2026-10-29: session
  // stats per product, Rowan's detail/stats lane). Counts only what the
  // log actually recorded: successful assessments bucketed by their own
  // product, and failures as one total (a failed request still counts
  // as a session event, but it produced no assessment to bucket). An
  // ok entry with an unknown or missing product is counted in `ok`
  // but in no product bucket, so the buckets never invent a product;
  // the app always records a real product, so in practice the buckets
  // sum to `ok`. Pure read over the entries: no sampling, no model.
  stats() {
    const byProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    let ok = 0;
    let failed = 0;
    for (const entry of this._entries) {
      if (entry.status === "ok") {
        ok += 1;
        if (Object.hasOwn(byProduct, entry.product)) {
          byProduct[entry.product] += 1;
        }
      } else {
        failed += 1;
      }
    }
    return { total: this._entries.length, ok, failed, byProduct };
  }

  record({ requestTimestamp, product = null, latencyMs = null, status, response = null, error = null, scenarioLabel = null }) {
    if (!LOG_STATUSES.includes(status)) {
      throw new RangeError(`unknown log status: ${status}`);
    }
    this._seq += 1;
    const entry = {
      seq: this._seq,
      recorded_at: this._nowFn().toISOString(),
      request_timestamp: requestTimestamp,
      product,
      latency_ms: latencyMs,
      status,
      scenario_label: scenarioLabel,
      response,
      error,
    };
    this._entries.push(entry);
    this._save();
    return entry;
  }

  entries() {
    return this._entries.slice();
  }

  clear() {
    this._entries = [];
    this._seq = 0;
    this._removeSaved();
  }

  // Shape consumed by the Agent 3 evaluation lane.
  toExport({ endpoint = null, samplingIntervalSeconds = null, product = null } = {}) {
    return {
      app: "meta-sentinel-frontend",
      exported_at: this._nowFn().toISOString(),
      product,
      endpoint,
      sampling_interval_seconds: samplingIntervalSeconds,
      entry_count: this._entries.length,
      entries: this.entries(),
    };
  }
}
