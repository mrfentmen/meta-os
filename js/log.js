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
  // sum to `ok`. Failures are likewise bucketed by their recorded
  // status (DETAIL-2): a failed request still counts as a session
  // event, and the cause breakdown says whether the session is losing
  // requests to the network, to HTTP errors, or to invalid responses.
  // DETAIL-3 adds the request timestamp of the most recent successful
  // assessment (lastOkAt, null when the log holds no ok entry): a
  // session that went quiet after its last success reads differently
  // from one that never succeeded, and failures never move it, so it
  // always names a real recorded success. It uses the entry's request
  // timestamp — the assessment's own timestamp, the same value the
  // history renders — not the log-write time, and an ok entry with no
  // usable request timestamp leaves the previous value in place.
  // DETAIL-4 adds the mean measured round-trip latency of successful
  // assessments (avgOkLatencyMs, null when no ok entry carries a
  // usable latency): failures never contribute, and an ok entry with
  // no finite latency_ms is skipped rather than counted as zero, so
  // the mean is always over real recorded measurements. The panel
  // renders it rounded to whole milliseconds.
  // DETAIL-5 splits DETAIL-3's last success per product
  // (lastOkAtByProduct, null per product with no ok entry): a session
  // where Ignis went quiet but Vigiles just succeeded reads
  // differently from one where all three went quiet together. Same
  // rules as DETAIL-3, per bucket: failures never move a bucket, an
  // ok entry with an unknown or missing product moves no bucket, and
  // an ok entry with no usable request timestamp leaves its bucket's
  // previous value in place.
  // DETAIL-6 bounds DETAIL-4's mean with the fastest and slowest
  // successful latencies (minOkLatencyMs / maxOkLatencyMs, both null
  // when no ok entry carries a usable latency): a mean alone cannot
  // tell a tight session from one with one very slow success, and
  // the range says which. Same measurement rules as DETAIL-4:
  // failures never contribute, and an ok entry with no finite
  // latency_ms is skipped rather than counted as zero, so both ends
  // are always real recorded measurements. The panel renders them
  // rounded to whole milliseconds.
  // Pure read over the entries: no sampling, no model.
  stats() {
    const byProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    const failedByStatus = { network_error: 0, http_error: 0, invalid_response: 0 };
    const lastOkAtByProduct = { vigiles: null, ignis: null, sanitas: null };
    let ok = 0;
    let failed = 0;
    let lastOkAt = null;
    let latencySum = 0;
    let latencyCount = 0;
    let minOkLatencyMs = null;
    let maxOkLatencyMs = null;
    for (const entry of this._entries) {
      if (entry.status === "ok") {
        ok += 1;
        if (Object.hasOwn(byProduct, entry.product)) {
          byProduct[entry.product] += 1;
        }
        if (typeof entry.request_timestamp === "string" && entry.request_timestamp !== "") {
          lastOkAt = entry.request_timestamp;
          if (Object.hasOwn(lastOkAtByProduct, entry.product)) {
            lastOkAtByProduct[entry.product] = entry.request_timestamp;
          }
        }
        if (Number.isFinite(entry.latency_ms)) {
          latencySum += entry.latency_ms;
          latencyCount += 1;
          if (minOkLatencyMs === null || entry.latency_ms < minOkLatencyMs) {
            minOkLatencyMs = entry.latency_ms;
          }
          if (maxOkLatencyMs === null || entry.latency_ms > maxOkLatencyMs) {
            maxOkLatencyMs = entry.latency_ms;
          }
        }
      } else {
        failed += 1;
        if (Object.hasOwn(failedByStatus, entry.status)) {
          failedByStatus[entry.status] += 1;
        }
      }
    }
    return {
      total: this._entries.length,
      ok,
      failed,
      byProduct,
      failedByStatus,
      lastOkAt,
      lastOkAtByProduct,
      avgOkLatencyMs: latencyCount === 0 ? null : latencySum / latencyCount,
      minOkLatencyMs,
      maxOkLatencyMs,
    };
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
