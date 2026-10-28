// In-memory evaluation session log (BRIEF.md section 7). Every analysis
// request the UI makes is recorded exactly once: the request timestamp, the
// measured round-trip latency, the outcome status, and either the validated
// response or the real error. Nothing is persisted and nothing is uploaded;
// the operator exports the log as JSON for the evaluation lane.

export const LOG_STATUSES = ["ok", "network_error", "http_error", "invalid_response"];

export class SessionLog {
  constructor({ nowFn = () => new Date() } = {}) {
    this._nowFn = nowFn;
    this._entries = [];
    this._seq = 0;
  }

  get count() {
    return this._entries.length;
  }

  record({ requestTimestamp, latencyMs, status, response = null, error = null, scenarioLabel = null }) {
    if (!LOG_STATUSES.includes(status)) {
      throw new RangeError(`unknown log status: ${status}`);
    }
    this._seq += 1;
    const entry = {
      seq: this._seq,
      recorded_at: this._nowFn().toISOString(),
      request_timestamp: requestTimestamp,
      latency_ms: latencyMs,
      status,
      scenario_label: scenarioLabel,
      response,
      error,
    };
    this._entries.push(entry);
    return entry;
  }

  entries() {
    return this._entries.slice();
  }

  clear() {
    this._entries = [];
    this._seq = 0;
  }

  // Shape consumed by the Agent 3 evaluation lane.
  toExport({ endpoint = null, samplingIntervalSeconds = null } = {}) {
    return {
      app: "meta-sentinel-frontend",
      exported_at: this._nowFn().toISOString(),
      endpoint,
      sampling_interval_seconds: samplingIntervalSeconds,
      entry_count: this._entries.length,
      entries: this.entries(),
    };
  }
}
