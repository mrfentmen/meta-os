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
  // DETAIL-19 adds the opening counterpart to DETAIL-7's last
  // failure (firstFailedAtByProduct, null per product with no
  // failure carrying a usable timestamp): each product's bucket
  // holds the request timestamp of its FIRST recorded failure, by
  // insertion order — set once, never overwritten, so a later
  // failure (even one carrying an earlier timestamp string) never
  // moves the bucket, and the pair with DETAIL-7 says when a
  // product's failures began and when they last happened. Same
  // bucket rules as DETAIL-7: successes never move a bucket, a
  // failure with an unknown or missing product moves no bucket,
  // and a failure without a usable request timestamp leaves its
  // bucket open for a later usable failure. The panel renders
  // "none" per product with no failure.
  // DETAIL-20 spans DETAIL-19 to DETAIL-7 per product
  // (failedSpanMsByProduct, null per product with no usable
  // failure pair): the milliseconds between a product's first and
  // last recorded failure timestamps — how long that product's
  // failures stretch, where the two endpoint lines alone do not
  // say it at a glance. Derived only from the DETAIL-19/7
  // buckets, so the same bucket rules apply: successes never move
  // a bucket, a failure with an unknown or missing product moves
  // no bucket, and a failure without a usable timestamp leaves
  // both endpoints in place. A product with exactly one usable
  // failure reads 0 (first and last are the same timestamp), not
  // null — one failure spans no time. A bucket timestamp that
  // does not parse (the endpoints accept any non-empty string)
  // reads null, never NaN. The difference is kept raw, not
  // clamped: a negative span means failures were recorded out of
  // timestamp order, which the insertion-order endpoints preserve
  // honestly. The panel renders each span in whole milliseconds,
  // or "none" per product with no usable failure pair.
  // DETAIL-21 spans DETAIL-18 to DETAIL-5 per product
  // (okSpanMsByProduct, null per product with no usable
  // success pair): the milliseconds between a product's first and
  // last recorded success timestamps — how long that product's
  // successes stretch, where the two endpoint lines alone do not
  // say it at a glance. Derived only from the DETAIL-18/5
  // buckets, so the same bucket rules apply: failures never move
  // a bucket, a success with an unknown or missing product moves
  // no bucket, and a success without a usable timestamp leaves
  // both endpoints in place. A product with exactly one usable
  // success reads 0 (first and last are the same timestamp), not
  // null — one success spans no time. A bucket timestamp that
  // does not parse (the endpoints accept any non-empty string)
  // reads null, never NaN. The difference is kept raw, not
  // clamped: a negative span means successes were recorded out of
  // timestamp order, which the insertion-order endpoints preserve
  // honestly. The panel renders each span in whole milliseconds,
  // or "none" per product with no usable success pair.
  // DETAIL-22 spans the global first-to-last success
  // (okSpanMs, null with no usable success pair): the
  // milliseconds between the session's first and last recorded
  // success timestamps, across products — how long the session's
  // successes stretch, where the per-product DETAIL-21 spans
  // alone do not say it at a glance. Derived only from the
  // global firstOkAt/lastOkAt endpoints, so the same endpoint
  // rules apply: a success with an unknown or missing product
  // still opens and closes the global span (the per-product
  // buckets stay product-gated), and a success without a usable
  // timestamp leaves both endpoints in place. A session with
  // exactly one usable success reads 0, not null — one success
  // spans no time. A bucket timestamp that does not parse reads
  // null, never NaN, and the difference is kept raw, not
  // clamped: a negative span means successes were recorded out
  // of timestamp order, which the insertion-order endpoints
  // preserve honestly. The panel renders the span in whole
  // milliseconds, or "none" with no usable success pair.
  // DETAIL-23 spans the global first-to-last failure
  // (failedSpanMs, null with no usable failure pair): the
  // milliseconds between the session's first and last recorded
  // failure timestamps, across products — how long the session's
  // failures stretch, where the per-product DETAIL-20 spans
  // alone do not say it at a glance. It introduces the global
  // firstFailedAt/lastFailedAt endpoints, mirroring DETAIL-22's
  // firstOkAt/lastOkAt: a failure with an unknown or missing
  // product still opens and closes the global span (the
  // per-product buckets stay product-gated), and a failure
  // without a usable timestamp leaves both endpoints in place.
  // A session with exactly one usable failure reads 0, not
  // null — one failure spans no time. A bucket timestamp that
  // does not parse reads null, never NaN, and the difference is
  // kept raw, not clamped: a negative span means failures were
  // recorded out of timestamp order, which the insertion-order
  // endpoints preserve honestly. Derived only from those two
  // global endpoints, reusing DETAIL-17's span helper, not a
  // new rule. The panel renders the span in whole
  // milliseconds, or "none" with no usable failure pair.
  // DETAIL-24 spans the global first-to-last entry
  // (entrySpanMs, null with no usable entry pair): the
  // milliseconds between the session's first and last recorded
  // entry timestamps, across products and across statuses —
  // how long the session's recorded activity stretches, where
  // the per-product DETAIL-17 spans alone do not say it at a
  // glance. It introduces the global firstEntryAt/lastEntryAt
  // endpoints, mirroring DETAIL-22's firstOkAt/lastOkAt: an
  // entry of any status, with an unknown or missing product,
  // still opens and closes the global span (the per-product
  // buckets stay product-gated), and an entry without a usable
  // timestamp leaves both endpoints in place. A session with
  // exactly one usable entry reads 0, not null — one entry
  // spans no time. A bucket timestamp that does not parse reads
  // null, never NaN, and the difference is kept raw, not
  // clamped: a negative span means entries were recorded out
  // of timestamp order, which the insertion-order endpoints
  // preserve honestly. Derived only from those two global
  // endpoints, reusing DETAIL-17's span helper, not a new rule.
  // The panel renders the span in whole milliseconds, or
  // "none" with no usable entry pair.
  // DETAIL-25 adds the global successful and failed shares
  // (okShare / failedShare, null on an empty log): each is
  // that outcome's entries over the session total, so a
  // session with 2 successes and 1 failure reads 2/3
  // successful and 1/3 failed, where the per-product
  // DETAIL-11/12 shares alone do not say it at a glance —
  // they divide by each product's own entries, and a
  // product with no entries reads null there. The global
  // denominator is the session total, so the null rule
  // differs on purpose: an empty log reads null for both
  // (no total to divide by), but once the log holds any
  // entry, a session with no successes reads 0 for okShare
  // and 1 for failedShare, never "none". The two shares
  // sum to 1 wherever either is non-null, because every
  // recorded entry is either ok or one of the three
  // failure statuses. Unlike the per-product buckets, the
  // global shares count unknown- or missing-product
  // entries: they sit in the session total, so they count
  // here just as they open and close the global spans.
  // The panel renders each share as a whole percent, or
  // "none" on an empty log.
  // DETAIL-26 adds the median successful latency
  // (medianOkLatencyMs, null when no ok entry carries a usable
  // latency): the middle recorded round-trip latency, where
  // DETAIL-4's mean can be pulled by one very slow success and
  // DETAIL-6's range alone does not say where the typical
  // success sits. Same measurement rules as DETAIL-4/6:
  // failures never contribute, and an ok entry with no finite
  // latency_ms is skipped rather than counted as zero, so the
  // median is always over real recorded measurements, across
  // products — an ok entry with an unknown or missing product
  // still counts here, just as it counts in the global mean
  // and range. An odd count reads its middle value; an even
  // count reads the mean of its two middle values, so a
  // two-success session reads the midpoint, not one end.
  // The panel renders it rounded to whole milliseconds, or
  // "none" when no success carries a usable latency.
  // DETAIL-28 adds the per-product medians
  // (medianOkLatencyMsByProduct, null per product with no usable
  // latency): DETAIL-26's global median split per product, so a
  // session where Ignis successes are typically slow but Vigiles
  // successes are typically fast reads differently from one
  // where all three sit together. Same measurement rules as the
  // global median and the per-product mean/range: failures never
  // contribute, an ok entry with no finite latency_ms is skipped,
  // and an ok entry with an unknown or missing product moves no
  // bucket. The panel renders each bucket rounded to whole
  // milliseconds, or "none" per product.
  // DETAIL-29 adds the per-product failure-cause shares of all
  // failures (failedShareByStatusByProduct): each product-cause
  // count from DETAIL-9 over the session's failed total, so a
  // session where half of all failures are Ignis network errors
  // reads differently from one where the same count is a small
  // slice of a much larger failure total — the DETAIL-9 counts
  // alone do not say that at a glance. The denominator is the
  // failed total, not the product's own failures, so the null
  // rule differs from DETAIL-11/12 on purpose: a session with
  // no failures at all reads null per cell (no failures to
  // divide by — an empty log and a success-only log alike),
  // but once the session holds any failure, a product-cause
  // cell with no failures reads 0, never "none". The cells sum
  // to 1 when every failure carries a known product, and to
  // less than 1 when unknown- or missing-product failures sit
  // in the denominator but in no cell, exactly as DETAIL-13's
  // shares do. Successes never move a cell. The panel renders
  // each cell as a whole percent, or "none" per cell with no
  // failures in the session.
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
    const firstFailedAtByProduct = { vigiles: null, ignis: null, sanitas: null };
    const firstEntryAtByProduct = { vigiles: null, ignis: null, sanitas: null };
    const lastEntryAtByProduct = { vigiles: null, ignis: null, sanitas: null };
    let ok = 0;
    let failed = 0;
    let lastOkAt = null;
    let firstOkAt = null;
    let lastFailedAt = null;
    let firstFailedAt = null;
    let lastEntryAt = null;
    let firstEntryAt = null;
    let latencySum = 0;
    let latencyCount = 0;
    const okLatencies = [];
    const latencySumByProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    const latencyCountByProduct = { vigiles: 0, ignis: 0, sanitas: 0 };
    const okLatenciesByProduct = { vigiles: [], ignis: [], sanitas: [] };
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
      // DETAIL-24: first/last entry across products, any status,
      // by insertion order — mirrors firstOkAt/lastOkAt, so it
      // covers an entry with an unknown or missing product too,
      // and a timestamp-less entry leaves both endpoints open
      // for a later usable entry.
      if (typeof entry.request_timestamp === "string" && entry.request_timestamp !== "") {
        if (firstEntryAt === null) {
          firstEntryAt = entry.request_timestamp;
        }
        lastEntryAt = entry.request_timestamp;
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
          // DETAIL-22: first success across products, set once by
          // insertion order — mirrors lastOkAt, so it covers an ok
          // entry with an unknown or missing product too, and a
          // timestamp-less ok entry leaves it open for a later
          // usable success.
          if (firstOkAt === null) {
            firstOkAt = entry.request_timestamp;
          }
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
          okLatencies.push(entry.latency_ms);
          if (Object.hasOwn(latencySumByProduct, entry.product)) {
            latencySumByProduct[entry.product] += entry.latency_ms;
            latencyCountByProduct[entry.product] += 1;
            okLatenciesByProduct[entry.product].push(entry.latency_ms);
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
          // DETAIL-23: first/last failure across products, set
          // by insertion order — mirrors firstOkAt/lastOkAt, so
          // it covers a failure with an unknown or missing
          // product too, and a timestamp-less failure leaves
          // both endpoints open for a later usable failure.
          if (firstFailedAt === null) {
            firstFailedAt = entry.request_timestamp;
          }
          lastFailedAt = entry.request_timestamp;
          if (Object.hasOwn(lastFailedAtByProduct, entry.product)) {
            lastFailedAtByProduct[entry.product] = entry.request_timestamp;
          }
          // DETAIL-19: first failure per product, set once by
          // insertion order — a later failure never overwrites
          // it, and a timestamp-less failure leaves the bucket
          // open for a later usable failure.
          if (Object.hasOwn(firstFailedAtByProduct, entry.product) && firstFailedAtByProduct[entry.product] === null) {
            firstFailedAtByProduct[entry.product] = entry.request_timestamp;
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
    // DETAIL-20: span between the DETAIL-19 first and DETAIL-7
    // last failure endpoints per product; null when either
    // endpoint is missing or unparseable, 0 for a single usable
    // failure. Reuses DETAIL-17's span helper, not a new rule.
    const failedSpanMsByProduct = {
      vigiles: entrySpanMs(firstFailedAtByProduct.vigiles, lastFailedAtByProduct.vigiles),
      ignis: entrySpanMs(firstFailedAtByProduct.ignis, lastFailedAtByProduct.ignis),
      sanitas: entrySpanMs(firstFailedAtByProduct.sanitas, lastFailedAtByProduct.sanitas),
    };
    // DETAIL-21: span between the DETAIL-18 first and DETAIL-5
    // last success endpoints per product; null when either
    // endpoint is missing or unparseable, 0 for a single usable
    // success. Reuses DETAIL-17's span helper, not a new rule.
    const okSpanMsByProduct = {
      vigiles: entrySpanMs(firstOkAtByProduct.vigiles, lastOkAtByProduct.vigiles),
      ignis: entrySpanMs(firstOkAtByProduct.ignis, lastOkAtByProduct.ignis),
      sanitas: entrySpanMs(firstOkAtByProduct.sanitas, lastOkAtByProduct.sanitas),
    };
    // DETAIL-22: the global success span (okSpanMs, null with no
    // usable success pair): the milliseconds between the session's
    // first and last recorded success timestamps, across products
    // — how long the session's successes stretch, where the
    // per-product DETAIL-21 spans alone do not say it at a glance.
    // Derived only from the global firstOkAt/lastOkAt endpoints,
    // reusing DETAIL-17's span helper, not a new rule: the
    // endpoints mirror DETAIL-3's lastOkAt, so a success with an
    // unknown or missing product still opens and closes the global
    // span (the per-product buckets stay product-gated), and a
    // success without a usable timestamp leaves both endpoints in
    // place. A session with exactly one usable success reads 0
    // (first and last are the same timestamp), not null. A bucket
    // timestamp that does not parse reads null, never NaN, and the
    // difference is kept raw, not clamped: a negative span means
    // successes were recorded out of timestamp order, which the
    // insertion-order endpoints preserve honestly. The panel
    // renders the span in whole milliseconds, or "none" with no
    // usable success pair.
    const okSpanMs = entrySpanMs(firstOkAt, lastOkAt);
    // DETAIL-23: the global failure span (failedSpanMs, null
    // with no usable failure pair): the milliseconds between
    // the session's first and last recorded failure
    // timestamps, across products — how long the session's
    // failures stretch, where the per-product DETAIL-20 spans
    // alone do not say it at a glance. Derived only from the
    // global firstFailedAt/lastFailedAt endpoints, reusing
    // DETAIL-17's span helper, not a new rule: the endpoints
    // mirror DETAIL-22's firstOkAt/lastOkAt, so a failure with
    // an unknown or missing product still opens and closes
    // the global span (the per-product buckets stay
    // product-gated), and a failure without a usable
    // timestamp leaves both endpoints in place. A session
    // with exactly one usable failure reads 0 (first and last
    // are the same timestamp), not null. A bucket timestamp
    // that does not parse reads null, never NaN, and the
    // difference is kept raw, not clamped: a negative span
    // means failures were recorded out of timestamp order,
    // which the insertion-order endpoints preserve honestly.
    // The panel renders the span in whole milliseconds, or
    // "none" with no usable failure pair.
    const failedSpanMs = entrySpanMs(firstFailedAt, lastFailedAt);
    // DETAIL-24: the global entry span (entrySpanMs, null with no
    // usable entry pair): the milliseconds between the session's
    // first and last recorded entry timestamps, across products
    // and across statuses — how long the session's recorded
    // activity stretches, where the per-product DETAIL-17 spans
    // alone do not say it at a glance. Derived only from the
    // global firstEntryAt/lastEntryAt endpoints, reusing
    // DETAIL-17's span helper, not a new rule: the endpoints
    // mirror DETAIL-22's firstOkAt/lastOkAt, so an entry of any
    // status, with an unknown or missing product, still opens
    // and closes the global span (the per-product buckets stay
    // product-gated), and an entry without a usable timestamp
    // leaves both endpoints in place. A session with exactly one
    // usable entry reads 0 (first and last are the same
    // timestamp), not null. A bucket timestamp that does not
    // parse reads null, never NaN, and the difference is kept
    // raw, not clamped: a negative span means entries were
    // recorded out of timestamp order, which the insertion-order
    // endpoints preserve honestly. The panel renders the span in
    // whole milliseconds, or "none" with no usable entry pair.
    const globalEntrySpanMs = entrySpanMs(firstEntryAt, lastEntryAt);
    // DETAIL-25: the global shares (okShare / failedShare,
    // null on an empty log): each outcome over the session
    // total, so unknown- or missing-product entries count
    // here, and the two sum to 1 wherever either is
    // non-null. Derived only from the ok/failed totals, not
    // a new rule.
    const okShare = this._entries.length === 0 ? null : ok / this._entries.length;
    const failedShare = this._entries.length === 0 ? null : failed / this._entries.length;
    // DETAIL-26: the median successful latency, over the same
    // usable measurements DETAIL-4/6 use, sorted ascending so
    // insertion order never moves it; null with no usable
    // latency, never NaN.
    const sortedOkLatencies = okLatencies.slice().sort((a, b) => a - b);
    let medianOkLatencyMs = null;
    if (sortedOkLatencies.length > 0) {
      const mid = Math.floor(sortedOkLatencies.length / 2);
      medianOkLatencyMs =
        sortedOkLatencies.length % 2 === 1
          ? sortedOkLatencies[mid]
          : (sortedOkLatencies[mid - 1] + sortedOkLatencies[mid]) / 2;
    }
    // DETAIL-28: the per-product medians split DETAIL-26's global
    // median per product, under the exact same rule — each bucket
    // sorted ascending so insertion order never moves it, odd
    // count reads its middle value, even count reads the mean of
    // its two middle values, null per product with no usable
    // latency. Failures never contribute, an ok entry with no
    // finite latency is skipped, and an ok entry with an unknown
    // or missing product moves no bucket, exactly as the
    // per-product mean and range do — the global median still
    // counts it, the buckets do not.
    const medianOf = (values) => {
      if (values.length === 0) return null;
      const sorted = values.slice().sort((a, b) => a - b);
      const mid = Math.floor(sorted.length / 2);
      return sorted.length % 2 === 1
        ? sorted[mid]
        : (sorted[mid - 1] + sorted[mid]) / 2;
    };
    const medianOkLatencyMsByProduct = {
      vigiles: medianOf(okLatenciesByProduct.vigiles),
      ignis: medianOf(okLatenciesByProduct.ignis),
      sanitas: medianOf(okLatenciesByProduct.sanitas),
    };
    // DETAIL-29: each DETAIL-9 product-cause count over the
    // session failed total, so the cells say what slice of all
    // failures each product-cause combination is. Null per cell
    // with no failures at all (nothing to divide by, empty log
    // and success-only log alike); 0 per cell with no failures
    // of that combination once the session holds any failure.
    // Derived only from the DETAIL-9 counts and the failed
    // total, not a new rule: a failure with an unknown or
    // missing product sits in the denominator but moves no
    // cell, so the cells sum to less than 1 in that case, and
    // successes never move a cell.
    const shareOfAllFailures = (count) => (failed === 0 ? null : count / failed);
    const failedShareByStatusByProduct = {
      vigiles: {
        network_error: shareOfAllFailures(failedByStatusByProduct.vigiles.network_error),
        http_error: shareOfAllFailures(failedByStatusByProduct.vigiles.http_error),
        invalid_response: shareOfAllFailures(failedByStatusByProduct.vigiles.invalid_response),
      },
      ignis: {
        network_error: shareOfAllFailures(failedByStatusByProduct.ignis.network_error),
        http_error: shareOfAllFailures(failedByStatusByProduct.ignis.http_error),
        invalid_response: shareOfAllFailures(failedByStatusByProduct.ignis.invalid_response),
      },
      sanitas: {
        network_error: shareOfAllFailures(failedByStatusByProduct.sanitas.network_error),
        http_error: shareOfAllFailures(failedByStatusByProduct.sanitas.http_error),
        invalid_response: shareOfAllFailures(failedByStatusByProduct.sanitas.invalid_response),
      },
    };
    // DETAIL-31: the global failure-cause shares of all failures
    // (failedShareByStatus): each DETAIL-9 global cause count over
    // the session failed total — DETAIL-29's per-product cells
    // collapsed across products, so a session where network
    // errors are half of all failures reads that at a glance
    // without adding the nine product-cause cells. Same null
    // rule as DETAIL-29: null per cause with no failures at all
    // (empty log and success-only log alike), 0 per cause with
    // no failures of that cause once the session holds any
    // failure. Unlike DETAIL-29's cells, these always sum to 1
    // once any failure exists: failedByStatus is product-blind,
    // so a failure with an unknown or missing product still
    // moves its cause cell, and record() rejects any other
    // status, so no failure can sit in the denominator without
    // a cell. Successes never move a cell.
    const failedShareByStatus = {
      network_error: shareOfAllFailures(failedByStatus.network_error),
      http_error: shareOfAllFailures(failedByStatus.http_error),
      invalid_response: shareOfAllFailures(failedByStatus.invalid_response),
    };
    // DETAIL-33: the per-product failure-cause shares of that
    // product's own failures (failedShareByStatusWithinProduct):
    // each DETAIL-9 product-cause count over that product's own
    // failed total, so the cells say what slice of Vigiles'
    // failures are network errors, not what slice of all
    // failures Vigiles' network errors are — DETAIL-29's cells
    // re-based per product. Null per product with no failures
    // of that product (empty log, success-only log, and a
    // product with successes but no failures alike); 0 per
    // cause with no failures of that cause once that product
    // holds any failure. The cells for a product sum to 1 once
    // it holds any failure: failedCountByProduct counts exactly
    // the bucketed failures, so a failure with an unknown or
    // missing product moves no bucket and no denominator here
    // (unlike DETAIL-31's product-blind cells), and successes
    // never move a cell.
    const shareOfProductFailures = (product, count) =>
      failedCountByProduct[product] === 0 ? null : count / failedCountByProduct[product];
    const failedShareByStatusWithinProduct = {
      vigiles: {
        network_error: shareOfProductFailures("vigiles", failedByStatusByProduct.vigiles.network_error),
        http_error: shareOfProductFailures("vigiles", failedByStatusByProduct.vigiles.http_error),
        invalid_response: shareOfProductFailures("vigiles", failedByStatusByProduct.vigiles.invalid_response),
      },
      ignis: {
        network_error: shareOfProductFailures("ignis", failedByStatusByProduct.ignis.network_error),
        http_error: shareOfProductFailures("ignis", failedByStatusByProduct.ignis.http_error),
        invalid_response: shareOfProductFailures("ignis", failedByStatusByProduct.ignis.invalid_response),
      },
      sanitas: {
        network_error: shareOfProductFailures("sanitas", failedByStatusByProduct.sanitas.network_error),
        http_error: shareOfProductFailures("sanitas", failedByStatusByProduct.sanitas.http_error),
        invalid_response: shareOfProductFailures("sanitas", failedByStatusByProduct.sanitas.invalid_response),
      },
    };
    // DETAIL-35: the per-product successful-latency shares
    // (okLatencyShareByProduct): each product's sum of usable
    // ok latencies over the session's total usable ok latency
    // sum, so a session where Ignis successes ate most of the
    // measured round-trip time reads that at a glance, where
    // the DETAIL-8 means alone do not say it — a product can
    // be slow on average yet small in total, or fast on
    // average yet dominant in total. Derived only from the
    // DETAIL-4/8 sums, not a new rule: failures never
    // contribute, an ok entry with no finite latency_ms is
    // skipped, and an ok entry with an unknown or missing
    // product moves no bucket but still sits in the total, so
    // the shares sum to 1 only when every usable-latency
    // success carries a known product, exactly as
    // DETAIL-13's shares do. Null per product when the
    // session holds no usable ok latency at all (an empty
    // log, a failure-only log, and a success-only log with
    // no finite latency alike), and null per product when
    // the usable latencies sum to zero — a zero total has
    // no shares to divide — never NaN; once a nonzero
    // total exists, a product with no usable latency reads
    // 0, never "none".
    const okLatencyShareByProduct = {
      vigiles: latencyCount === 0 || latencySum === 0 ? null : latencySumByProduct.vigiles / latencySum,
      ignis: latencyCount === 0 || latencySum === 0 ? null : latencySumByProduct.ignis / latencySum,
      sanitas: latencyCount === 0 || latencySum === 0 ? null : latencySumByProduct.sanitas / latencySum,
    };
    // DETAIL-37: the per-product successful-count shares
    // (okShareOfOkByProduct): each product's ok count from
    // DETAIL-1 over the session's ok total, so a session where
    // Ignis successes are half of all successes reads that at a
    // glance, where DETAIL-1's raw counts alone do not say it —
    // the count mirror of DETAIL-35's latency-total shares, and
    // the ok-total mirror of DETAIL-13's entry shares. Derived
    // only from the DETAIL-1 counts and the ok total, not a new
    // rule: failures never contribute (they are not in the ok
    // total and move no bucket), an ok entry with no finite
    // latency still counts here — this is a count share, not a
    // latency share, so DETAIL-35's skip rule does not apply —
    // and an ok entry with an unknown or missing product sits
    // in the denominator but moves no bucket, so the shares sum
    // to 1 only when every success carries a known product,
    // exactly as DETAIL-13's and DETAIL-35's shares do. Null
    // per product with no successes at all (an empty log and a
    // failure-only log alike); 0 per product with no successes
    // once the session holds any success.
    const shareOfAllOk = (count) => (ok === 0 ? null : count / ok);
    const okShareOfOkByProduct = {
      vigiles: shareOfAllOk(okCountByProduct.vigiles),
      ignis: shareOfAllOk(okCountByProduct.ignis),
      sanitas: shareOfAllOk(okCountByProduct.sanitas),
    };
    // DETAIL-39: the per-product failed-count shares
    // (failedShareOfFailedByProduct): each product's failed
    // count from DETAIL-34 over the session's failed total,
    // so a session where Ignis failures are half of all
    // failures reads that at a glance, where DETAIL-34's raw
    // counts alone do not say it — the failure mirror of
    // DETAIL-37's ok-count shares, and the failed-total
    // mirror of DETAIL-13's entry shares. Derived only from
    // the DETAIL-34 counts and the failed total, not a new
    // rule: successes never contribute (they are not in the
    // failed total and move no bucket), a failure's cause
    // does not matter here — every failed status counts
    // alike, unlike DETAIL-29/31/33's cause splits — and a
    // failure with an unknown or missing product sits in
    // the denominator but moves no bucket, so the shares sum
    // to 1 only when every failure carries a known product,
    // exactly as DETAIL-37's shares do. Null per product
    // with no failures at all (an empty log and a
    // success-only log alike); 0 per product with no
    // failures once the session holds any failure.
    const shareOfAllFailed = (count) => (failed === 0 ? null : count / failed);
    const failedShareOfFailedByProduct = {
      vigiles: shareOfAllFailed(failedCountByProduct.vigiles),
      ignis: shareOfAllFailed(failedCountByProduct.ignis),
      sanitas: shareOfAllFailed(failedCountByProduct.sanitas),
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
      firstOkAt,
      lastOkAtByProduct,
      firstOkAtByProduct,
      lastFailedAtByProduct,
      firstFailedAtByProduct,
      lastFailedAt,
      firstFailedAt,
      firstEntryAtByProduct,
      lastEntryAtByProduct,
      firstEntryAt,
      lastEntryAt,
      entrySpanMsByProduct,
      failedSpanMsByProduct,
      okSpanMsByProduct,
      okSpanMs,
      failedSpanMs,
      entrySpanMs: globalEntrySpanMs,
      okShare,
      failedShare,
      avgOkLatencyMs: latencyCount === 0 ? null : latencySum / latencyCount,
      avgOkLatencyMsByProduct: {
        vigiles: latencyCountByProduct.vigiles === 0 ? null : latencySumByProduct.vigiles / latencyCountByProduct.vigiles,
        ignis: latencyCountByProduct.ignis === 0 ? null : latencySumByProduct.ignis / latencyCountByProduct.ignis,
        sanitas: latencyCountByProduct.sanitas === 0 ? null : latencySumByProduct.sanitas / latencyCountByProduct.sanitas,
      },
      minOkLatencyMs,
      maxOkLatencyMs,
      medianOkLatencyMs,
      medianOkLatencyMsByProduct,
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
      failedShareByStatusByProduct,
      failedShareByStatus,
      failedShareByStatusWithinProduct,
      // DETAIL-34: the per-product failed counts
      // (failedCountByProduct): the count behind DETAIL-12's
      // failed shares and DETAIL-33's within-product
      // denominators, exposed on its own — the failure mirror
      // of DETAIL-1's per-product ok counts (byProduct) and
      // the failure half of DETAIL-14's entry counts. Always
      // plain counts, never null: a product with no failures
      // reads 0, and the three buckets sum to the global
      // failed total only when every failure carries a known
      // product — a failure with an unknown or missing
      // product still counts in the global failed total but
      // moves no bucket, exactly as DETAIL-9's cause buckets
      // do. Successes never move a bucket.
      failedCountByProduct,
      // DETAIL-35: the per-product successful-latency shares
      // (okLatencyShareByProduct): each product's usable ok
      // latency sum over the session's total usable ok
      // latency sum — the latency-total mirror of
      // DETAIL-13's entry shares. Null per product with no
      // usable ok latency in the session, or a zero total;
      // 0 per product with no usable latency once a nonzero
      // total exists.
      okLatencyShareByProduct,
      // DETAIL-36: the usable-latency counts (okLatencyCount
      // / okLatencyCountByProduct): the count behind
      // DETAIL-4's global mean and DETAIL-8's per-product
      // means — how many successes carried a usable latency,
      // so a mean over one measurement reads differently from
      // a mean over a hundred. No new counting rule: the loop
      // already counts them for the means, so the same rules
      // apply — failures never contribute, even a failure
      // carrying a latency value; an ok entry with no finite
      // latency is skipped rather than counted as zero; and
      // an ok entry with an unknown or missing product counts
      // globally but moves no bucket, exactly as DETAIL-4/8's
      // means do. Always plain counts, never null: a session
      // or product with no usable latency reads 0.
      okLatencyCount: latencyCount,
      okLatencyCountByProduct: latencyCountByProduct,
      // DETAIL-37: the per-product successful-count shares
      // (okShareOfOkByProduct): each product's ok count over
      // the session ok total — the count mirror of DETAIL-35's
      // latency-total shares. Null per product with no
      // successes in the session; 0 per product with no
      // successes once any success exists.
      okShareOfOkByProduct,
      // DETAIL-38: the usable-latency sums (okLatencySum /
      // okLatencySumByProduct): the total behind DETAIL-4's
      // global mean, DETAIL-8's per-product means, and
      // DETAIL-35's per-product shares — the denominator those
      // shares divide by, so a share of half the total reads
      // against a real millisecond total, not just a fraction.
      // No new summing rule: the loop already sums them for
      // the means and shares, so the same rules apply —
      // failures never contribute, even a failure carrying a
      // latency value; an ok entry with no finite latency is
      // skipped rather than summed as zero; and an ok entry
      // with an unknown or missing product sums globally but
      // moves no bucket, exactly as DETAIL-4/8/35 do. Always
      // plain sums, never null: a session or product with no
      // usable latency reads 0.
      okLatencySum: latencySum,
      okLatencySumByProduct: latencySumByProduct,
      // DETAIL-39: the per-product failed-count shares
      // (failedShareOfFailedByProduct): each product's failed
      // count over the session failed total — the failure
      // mirror of DETAIL-37's ok-count shares. Null per
      // product with no failures in the session; 0 per
      // product with no failures once any failure exists.
      failedShareOfFailedByProduct,
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
