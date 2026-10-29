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
  // DETAIL-7 mirrors DETAIL-5 on the failure side
  // (lastFailedAtByProduct, null per product with no failure): a
  // session where Ignis just failed but Vigiles has not failed all
  // day reads differently from one where all three failed together.
  // Same rules as DETAIL-5, per bucket: successes never move a
  // bucket, a failure with an unknown or missing product moves no
  // bucket, and a failure with no usable request timestamp leaves
  // its bucket's previous value in place. It uses the entry's
  // request timestamp — the same value the history renders — not
  // the log-write time.
  // DETAIL-8 splits DETAIL-4's mean per product
  // (avgOkLatencyMsByProduct, null per product with no ok entry
  // carrying a usable latency): a session where Ignis successes
  // are slow but Vigiles successes are fast reads differently from
  // one where all three are slow together. Same measurement rules
  // as DETAIL-4, per bucket: failures never contribute, an ok
  // entry with an unknown or missing product moves no bucket, and
  // an ok entry with no finite latency_ms is skipped rather than
  // counted as zero, so each mean is always over real recorded
  // measurements for that product. The panel renders each mean
  // rounded to whole milliseconds.
  // DETAIL-9 splits DETAIL-2's cause breakdown per product
  // (failedByStatusByProduct, zeros per product with no failure of
  // that cause): a session where Ignis failures are all network
  // errors but Vigiles failures are all HTTP errors reads
  // differently from one where both fail the same way. Same rules
  // as DETAIL-2, per bucket: successes never move a bucket, a
  // failure with an unknown or missing product moves no bucket,
  // and a failure still counts in the session failed total and
  // the global cause breakdown even when it moves no product
  // bucket, so the buckets never invent a product or a cause.
  // DETAIL-10 splits DETAIL-6's range per product
  // (minOkLatencyMsByProduct / maxOkLatencyMsByProduct, null per
  // product with no ok entry carrying a usable latency): a session
  // where Ignis successes span 50–900 ms but Vigiles successes are
  // all near 100 ms reads differently from one where all three span
  // the same range. Same measurement rules as DETAIL-6, per bucket:
  // failures never contribute, an ok entry with an unknown or
  // missing product moves no bucket, and an ok entry with no finite
  // latency_ms is skipped rather than counted as zero, so both ends
  // of each range are always real recorded measurements for that
  // product. The panel renders each range rounded to whole
  // milliseconds, or "none" per product with no usable latency.
  // DETAIL-11 adds the per-product successful share
  // (okShareByProduct, null per product with no entry of that
  // product): a session where Ignis succeeds 9 times in 10 but
  // Vigiles succeeds 3 times in 10 reads differently from one
  // where both succeed at the same rate, and the raw counts alone
  // do not say that at a glance. Each share is that product's ok
  // entries over that product's own entries (ok plus failed), so
  // a product that only failed reads 0, not null, and a product
  // with no entries reads null. Same bucket rules as the other
  // per-product fields: an entry with an unknown or missing
  // product moves no bucket (though it still counts in the
  // global ok/failed totals), so the shares never invent a
  // product. The panel renders each share as a whole percent, or
  // "none" per product with no entries.
  // DETAIL-12 adds the mirror: the per-product failed share
  // (failedShareByProduct, null per product with no entry of that
  // product): each share is that product's failed entries over
  // that product's own entries (ok plus failed), so a product
  // that only succeeded reads 0, not null, a product that only
  // failed reads 1, and okShare + failedShare sum to 1 wherever
  // either is non-null. Same bucket rules as DETAIL-11: an entry
  // with an unknown or missing product moves no bucket (though
  // it still counts in the global ok/failed totals). The panel
  // renders each share as a whole percent, or "none" per product
  // with no entries.
  // DETAIL-13 adds the session-mix share (entryShareByProduct):
  // each product's entries over the session's total entries, so
  // a session split 2/1/1 across the products reads differently
  // from one where a single product dominates, and the raw
  // counts alone do not say that at a glance. The denominator
  // here is the session total, not the product's own entries,
  // so the null rule differs from DETAIL-11/12 on purpose: an
  // empty log reads null per product (no total to divide by),
  // but once the log holds any entry, a product with no entries
  // reads 0 — it genuinely holds 0% of the session — never
  // "none". The three shares sum to 1 when every entry carries
  // a known product, and to less than 1 when unknown-product
  // entries sit in the total but in no bucket. Same bucket
  // rules as DETAIL-11: an entry with an unknown or missing
  // product moves no bucket (though it still counts in the
  // total). The panel renders each share as a whole percent,
  // or "none" per product only on an empty log.
  // DETAIL-14 exposes the counts behind DETAIL-13's shares
  // (entryCountByProduct): each product's entries, ok plus
  // failed, as plain counts — the denominator DETAIL-11/12
  // already divide by, and the numerator DETAIL-13 divides by
  // the session total. Unlike byProduct, which counts only
  // successes, a product that only failed still reads its full
  // count here. Always-renders zeros, never null: an empty log
  // reads 0 per product, and a product with no entries reads 0
  // in a non-empty session. Same bucket rules: an entry with an
  // unknown or missing product moves no bucket (though it still
  // counts in the total), so the three counts sum to the total
  // only when every entry carries a known product.
  // DETAIL-16 adds the closing counterpart to DETAIL-15's first
  // entry (lastEntryAtByProduct, null per product with no entry
  // carrying a usable timestamp): each product's bucket holds the
  // request timestamp of its MOST RECENT recorded entry, any
  // status — overwritten on every usable entry, so it reads when
  // recording for a product last happened, not when it last
  // succeeded (DETAIL-5) or last failed (DETAIL-7). Same bucket
  // rules as DETAIL-15: an entry with an unknown or missing
  // product moves no bucket, and an entry without a usable
  // timestamp leaves its bucket's previous value in place.
  // DETAIL-17 spans DETAIL-15 to DETAIL-16 per product
  // (entrySpanMsByProduct, null per product with no usable entry
  // pair): the milliseconds between a product's first and last
  // recorded entry timestamps, any status — how long that
  // product's recording stretches, where the two endpoint lines
  // alone do not say it at a glance. Derived only from the
  // DETAIL-15/16 buckets, so the same bucket rules apply: an
  // entry with an unknown or missing product moves no bucket,
  // and an entry without a usable timestamp leaves both endpoints
  // in place. A product with exactly one usable entry reads 0
  // (first and last are the same timestamp), not null — one
  // entry spans no time. A bucket timestamp that does not parse
  // (the endpoints accept any non-empty string) reads null, never
  // NaN. The difference is kept raw, not clamped: a negative span
  // means entries were recorded out of timestamp order, which the
  // insertion-order endpoints preserve honestly. The panel renders
  // each span in whole milliseconds, or "none" per product with no
  // usable entry pair.
  // DETAIL-18 adds the opening counterpart to DETAIL-5's last
  // success (firstOkAtByProduct, null per product with no ok entry
  // carrying a usable timestamp): each product's bucket holds the
  // request timestamp of its FIRST recorded success, by insertion
  // order — set once, never overwritten, so a later success (even
  // one carrying an earlier timestamp string) never moves the
  // bucket, and the pair with DETAIL-5 says when a product's
  // successes began and when they last happened. Same bucket
  // rules as DETAIL-5: failures never move a bucket, an ok entry
  // with an unknown or missing product moves no bucket, and an ok
  // entry without a usable request timestamp leaves its bucket
  // open for a later usable success. The panel renders "none"
  // per product with no success.
  // Pure read over the entries: no sampling, no model.
  stats() {
    const byProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    const failedByStatus = { network_error: 0, http_error: 0, invalid_response: 0 };
    const failedByStatusByProduct = {
      vigiles: { network_error: 0, http_error: 0, invalid_response: 0 },
      ignis: { network_error: 0, http_error: 0, invalid_response: 0 },
      sanitas: { network_error: 0, http_error: 0, invalid_response: 0 },
    };
    const lastOkAtByProduct = { vigiles: null, ignis: null, sanitas: null };
    const firstOkAtByProduct = { vigiles: null, ignis: null, sanitas: null };
    const lastFailedAtByProduct = { vigiles: null, ignis: null, sanitas: null };
    const firstEntryAtByProduct = { vigiles: null, ignis: null, sanitas: null };
    const lastEntryAtByProduct = { vigiles: null, ignis: null, sanitas: null };
    let ok = 0;
    let failed = 0;
    let lastOkAt = null;
    let latencySum = 0;
    let latencyCount = 0;
    const latencySumByProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    const latencyCountByProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    let minOkLatencyMs = null;
    let maxOkLatencyMs = null;
    const minOkLatencyMsByProduct = { vigiles: null, ignis: null, sanitas: null };
    const maxOkLatencyMsByProduct = { vigiles: null, ignis: null, sanitas: null };
    const okCountByProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    const failedCountByProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    const entryCountByProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    for (const entry of this._entries) {
      // DETAIL-15: the first recorded entry per product, any status,
      // by insertion order — set once, never overwritten, so a later
      // entry (even one carrying an earlier timestamp string) never
      // moves the bucket. An entry without a usable timestamp or
      // with an unknown/missing product moves no bucket, and a later
      // usable entry can still fill it.
      if (
        typeof entry.request_timestamp === "string" &&
        entry.request_timestamp !== "" &&
        Object.hasOwn(firstEntryAtByProduct, entry.product) &&
        firstEntryAtByProduct[entry.product] === null
      ) {
        firstEntryAtByProduct[entry.product] = entry.request_timestamp;
      }
      // DETAIL-16: the most recent recorded entry per product, any
      // status, by insertion order — overwritten on every usable
      // entry, so a later entry (even one carrying an earlier
      // timestamp string) always moves the bucket. An entry
      // without a usable timestamp or with an unknown/missing
      // product moves no bucket.
      if (
        typeof entry.request_timestamp === "string" &&
        entry.request_timestamp !== "" &&
        Object.hasOwn(lastEntryAtByProduct, entry.product)
      ) {
        lastEntryAtByProduct[entry.product] = entry.request_timestamp;
      }
      if (entry.status === "ok") {
        ok += 1;
        if (Object.hasOwn(byProduct, entry.product)) {
          byProduct[entry.product] += 1;
        }
        if (Object.hasOwn(okCountByProduct, entry.product)) {
          okCountByProduct[entry.product] += 1;
          entryCountByProduct[entry.product] += 1;
        }
        if (typeof entry.request_timestamp === "string" && entry.request_timestamp !== "") {
          lastOkAt = entry.request_timestamp;
          if (Object.hasOwn(lastOkAtByProduct, entry.product)) {
            lastOkAtByProduct[entry.product] = entry.request_timestamp;
          }
          // DETAIL-18: first success per product, set once by
          // insertion order — a later ok entry never overwrites
          // it, and a timestamp-less ok entry leaves the bucket
          // open for a later usable success.
          if (Object.hasOwn(firstOkAtByProduct, entry.product) && firstOkAtByProduct[entry.product] === null) {
            firstOkAtByProduct[entry.product] = entry.request_timestamp;
          }
        }
        if (Number.isFinite(entry.latency_ms)) {
          latencySum += entry.latency_ms;
          latencyCount += 1;
          if (Object.hasOwn(latencySumByProduct, entry.product)) {
            latencySumByProduct[entry.product] += entry.latency_ms;
            latencyCountByProduct[entry.product] += 1;
          }
          if (minOkLatencyMs === null || entry.latency_ms < minOkLatencyMs) {
            minOkLatencyMs = entry.latency_ms;
          }
          if (maxOkLatencyMs === null || entry.latency_ms > maxOkLatencyMs) {
            maxOkLatencyMs = entry.latency_ms;
          }
          if (Object.hasOwn(minOkLatencyMsByProduct, entry.product)) {
            if (minOkLatencyMsByProduct[entry.product] === null || entry.latency_ms < minOkLatencyMsByProduct[entry.product]) {
              minOkLatencyMsByProduct[entry.product] = entry.latency_ms;
            }
            if (maxOkLatencyMsByProduct[entry.product] === null || entry.latency_ms > maxOkLatencyMsByProduct[entry.product]) {
              maxOkLatencyMsByProduct[entry.product] = entry.latency_ms;
            }
          }
        }
      } else {
        failed += 1;
        if (Object.hasOwn(entryCountByProduct, entry.product)) {
          entryCountByProduct[entry.product] += 1;
          failedCountByProduct[entry.product] += 1;
        }
        if (Object.hasOwn(failedByStatus, entry.status)) {
          failedByStatus[entry.status] += 1;
        }
        if (Object.hasOwn(failedByStatusByProduct, entry.product) && Object.hasOwn(failedByStatus, entry.status)) {
          failedByStatusByProduct[entry.product][entry.status] += 1;
        }
        if (typeof entry.request_timestamp === "string" && entry.request_timestamp !== "") {
          if (Object.hasOwn(lastFailedAtByProduct, entry.product)) {
            lastFailedAtByProduct[entry.product] = entry.request_timestamp;
          }
        }
      }
    }
    // DETAIL-17: span between the DETAIL-15 first and DETAIL-16
    // last endpoints per product; null when either endpoint is
    // missing or unparseable, 0 for a single usable entry.
    const entrySpanMs = (first, last) => {
      if (first === null || last === null) return null;
      const span = Date.parse(last) - Date.parse(first);
      return Number.isFinite(span) ? span : null;
    };
    const entrySpanMsByProduct = {
      vigiles: entrySpanMs(firstEntryAtByProduct.vigiles, lastEntryAtByProduct.vigiles),
      ignis: entrySpanMs(firstEntryAtByProduct.ignis, lastEntryAtByProduct.ignis),
      sanitas: entrySpanMs(firstEntryAtByProduct.sanitas, lastEntryAtByProduct.sanitas),
    };
    return {
      total: this._entries.length,
      ok,
      failed,
      byProduct,
      entryCountByProduct,
      failedByStatus,
      failedByStatusByProduct,
      lastOkAt,
      lastOkAtByProduct,
      firstOkAtByProduct,
      lastFailedAtByProduct,
      firstEntryAtByProduct,
      lastEntryAtByProduct,
      entrySpanMsByProduct,
      avgOkLatencyMs: latencyCount === 0 ? null : latencySum / latencyCount,
      avgOkLatencyMsByProduct: {
        vigiles: latencyCountByProduct.vigiles === 0 ? null : latencySumByProduct.vigiles / latencyCountByProduct.vigiles,
        ignis: latencyCountByProduct.ignis === 0 ? null : latencySumByProduct.ignis / latencyCountByProduct.ignis,
        sanitas: latencyCountByProduct.sanitas === 0 ? null : latencySumByProduct.sanitas / latencyCountByProduct.sanitas,
      },
      minOkLatencyMs,
      maxOkLatencyMs,
      minOkLatencyMsByProduct,
      maxOkLatencyMsByProduct,
      okShareByProduct: {
        vigiles: entryCountByProduct.vigiles === 0 ? null : okCountByProduct.vigiles / entryCountByProduct.vigiles,
        ignis: entryCountByProduct.ignis === 0 ? null : okCountByProduct.ignis / entryCountByProduct.ignis,
        sanitas: entryCountByProduct.sanitas === 0 ? null : okCountByProduct.sanitas / entryCountByProduct.sanitas,
      },
      failedShareByProduct: {
        vigiles: entryCountByProduct.vigiles === 0 ? null : failedCountByProduct.vigiles / entryCountByProduct.vigiles,
        ignis: entryCountByProduct.ignis === 0 ? null : failedCountByProduct.ignis / entryCountByProduct.ignis,
        sanitas: entryCountByProduct.sanitas === 0 ? null : failedCountByProduct.sanitas / entryCountByProduct.sanitas,
      },
      entryShareByProduct: {
        vigiles: this._entries.length === 0 ? null : entryCountByProduct.vigiles / this._entries.length,
        ignis: this._entries.length === 0 ? null : entryCountByProduct.ignis / this._entries.length,
        sanitas: this._entries.length === 0 ? null : entryCountByProduct.sanitas / this._entries.length,
      },
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
