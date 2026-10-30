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
  // DETAIL-47 adds the per-product usable-latency-count shares
  // of all entries (okLatencyCountShareOfEntriesByProduct):
  // each DETAIL-36 product count over the session's total
  // entries, so a session where Vigiles measurements are a
  // sixth of everything recorded reads that at a glance,
  // where DETAIL-45's shares of the measurement total alone
  // do not say it — the entry-total mirror of DETAIL-45,
  // and the measurement-count split of DETAIL-13's entry
  // shares: failures and latency-less successes sit in the
  // denominator but move no bucket. Derived only from the
  // DETAIL-36 counts and the entry total, reusing
  // DETAIL-40's shareOfAllEntries helper, not a new rule:
  // failures never contribute, even a failure carrying a
  // latency value; an ok entry with no finite latency is
  // skipped rather than counted as zero; and an ok entry
  // with an unknown or missing product sits in the
  // denominator but moves no bucket, so the three shares
  // sum to the global usable-latency-count share of entries
  // only when every usable-latency success carries a known
  // product. Null per product on an empty log (nothing to
  // divide by); 0 per product with no usable latency once
  // the session holds any entry, including a failure-only
  // log and a success-only log with no finite latency —
  // unlike DETAIL-45, which reads null until the first
  // usable measurement, because its denominator is the
  // measurement count. A 0 ms latency still counts as a
  // measurement, exactly as in DETAIL-45.
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
    // DETAIL-40: the per-product failed shares of all entries
    // (failedShareOfEntriesByProduct): each product's failed
    // count from DETAIL-34 over the session's entry total, so
    // a session where Ignis failures are a third of everything
    // recorded reads that at a glance, where DETAIL-34's raw
    // counts alone do not say it — the failure mirror of
    // DETAIL-37's success shares, and the failed half of
    // DETAIL-13's entry shares. Derived only from the
    // DETAIL-34 counts and the entry total, not a new rule:
    // successes never move a bucket (they sit in the
    // denominator only), the failure's cause never matters
    // here, and a failure with an unknown or missing product
    // sits in the denominator but moves no bucket, so the
    // shares sum to the global DETAIL-25 failed share only
    // when every failure carries a known product. Null per
    // product on an empty log (nothing to divide by); 0 per
    // product with no failures of that product once the
    // session holds any entry, including a success-only log
    // — unlike DETAIL-37, which reads null until the first
    // success, because its denominator is the ok total.
    const shareOfAllEntries = (count) => (this._entries.length === 0 ? null : count / this._entries.length);
    const failedShareOfEntriesByProduct = {
      vigiles: shareOfAllEntries(failedCountByProduct.vigiles),
      ignis: shareOfAllEntries(failedCountByProduct.ignis),
      sanitas: shareOfAllEntries(failedCountByProduct.sanitas),
    };
    // DETAIL-41: the per-product successful-count shares of
    // all entries (okShareOfTotalByProduct): each product's
    // ok count from DETAIL-1 over the session's total entry
    // count, so a session where Ignis successes are a third
    // of everything recorded reads that at a glance, where
    // DETAIL-37's ok-total shares alone do not say it — the
    // entry-total mirror of DETAIL-37, the ok half of
    // DETAIL-13's entry shares, and the success mirror of
    // DETAIL-40's failed shares. Derived only from the
    // DETAIL-1 counts and the entry total, reusing
    // DETAIL-40's shareOfAllEntries helper, not a new rule:
    // failures sit in the denominator but move no bucket
    // (they are not successes), an ok entry with no finite
    // latency still counts here — this is a count share, not
    // a latency share, so DETAIL-35's skip rule does not
    // apply — and an ok entry with an unknown or missing
    // product sits in the denominator but moves no bucket, so
    // the shares sum to the session ok share (DETAIL-25),
    // and to 1 only when every entry is a known-product
    // success, exactly as DETAIL-37's shares do within the
    // ok total. Null per product on an empty log (nothing
    // to divide by); 0 per product with no successes once
    // the session holds any entry — a failure-only log
    // reads 0 per product, not "none", because the
    // denominator exists and the buckets are genuinely
    // empty.
    const okShareOfTotalByProduct = {
      vigiles: shareOfAllEntries(okCountByProduct.vigiles),
      ignis: shareOfAllEntries(okCountByProduct.ignis),
      sanitas: shareOfAllEntries(okCountByProduct.sanitas),
    };
    // DETAIL-42: the per-product failure-cause shares of all
    // entries (failedShareByStatusOfEntriesByProduct): each
    // DETAIL-9 product-cause count over the session's entry
    // total, so a session where Ignis network errors are a
    // sixth of everything recorded reads that at a glance,
    // where DETAIL-29's failed-total cells alone do not say
    // it — the entry-total mirror of DETAIL-29, and the
    // cause split of DETAIL-40's failed shares: the three
    // cause cells for a product sum to that product's
    // DETAIL-40 share. Derived only from the DETAIL-9
    // counts and the entry total, reusing DETAIL-40's
    // shareOfAllEntries helper, not a new rule: successes
    // never move a cell (they sit in the denominator only),
    // and a failure with an unknown or missing product sits
    // in the denominator but moves no cell, so the nine
    // cells sum to the global DETAIL-25 failed share only
    // when every failure carries a known product. Null per
    // cell on an empty log (nothing to divide by); 0 per
    // cell with no failures of that combination once the
    // session holds any entry, including a success-only
    // log — unlike DETAIL-29, which reads null until the
    // first failure, because its denominator is the failed
    // total.
    const failedShareByStatusOfEntriesByProduct = {
      vigiles: {
        network_error: shareOfAllEntries(failedByStatusByProduct.vigiles.network_error),
        http_error: shareOfAllEntries(failedByStatusByProduct.vigiles.http_error),
        invalid_response: shareOfAllEntries(failedByStatusByProduct.vigiles.invalid_response),
      },
      ignis: {
        network_error: shareOfAllEntries(failedByStatusByProduct.ignis.network_error),
        http_error: shareOfAllEntries(failedByStatusByProduct.ignis.http_error),
        invalid_response: shareOfAllEntries(failedByStatusByProduct.ignis.invalid_response),
      },
      sanitas: {
        network_error: shareOfAllEntries(failedByStatusByProduct.sanitas.network_error),
        http_error: shareOfAllEntries(failedByStatusByProduct.sanitas.http_error),
        invalid_response: shareOfAllEntries(failedByStatusByProduct.sanitas.invalid_response),
      },
    };
    // DETAIL-43: the global failure-cause shares of all
    // entries (failedShareByStatusOfEntries): each DETAIL-9
    // global cause count over the session's entry total, so
    // a session where network errors are a sixth of
    // everything recorded reads that at a glance, where
    // DETAIL-31's failed-total shares alone do not say it
    // — the entry-total mirror of DETAIL-31, and the
    // collapsed form of DETAIL-42's nine product-cause
    // cells. Derived only from the DETAIL-9 global counts
    // and the entry total, reusing DETAIL-40's
    // shareOfAllEntries helper, not a new rule: successes
    // never move a cell (they sit in the denominator
    // only), and unlike DETAIL-42's cells these always sum
    // to the global DETAIL-25 failed share once any entry
    // exists, because failedByStatus is product-blind — a
    // failure with an unknown or missing product still
    // moves its cause cell. Null per cause on an empty log
    // (nothing to divide by); 0 per cause with no failures
    // of that cause once the session holds any entry,
    // including a success-only log.
    const failedShareByStatusOfEntries = {
      network_error: shareOfAllEntries(failedByStatus.network_error),
      http_error: shareOfAllEntries(failedByStatus.http_error),
      invalid_response: shareOfAllEntries(failedByStatus.invalid_response),
    };
    // DETAIL-44: the per-product failure-cause shares of that
    // product's own entries (failedShareByStatusOfEntriesWithinProduct):
    // each DETAIL-9 product-cause count over that product's own
    // entry total (DETAIL-14), so the cells say what slice of
    // everything Vigiles recorded is Vigiles network errors, not
    // what slice of the whole session's entries it is — DETAIL-42's
    // cells re-based per product, and the cause split of
    // DETAIL-12's failed-share-by-product line: the three cause
    // cells for a product sum to that product's DETAIL-12 failed
    // share. Derived only from the DETAIL-9 counts and the
    // per-product entry totals, not a new rule: successes of a
    // product sit in that product's denominator but move no
    // cell, and a failure with an unknown or missing product
    // moves no bucket and no denominator here (unlike DETAIL-42's
    // global denominator and DETAIL-43's product-blind cells),
    // exactly as DETAIL-33's within-product cells do. Null per
    // product with no entries of that product — an empty log,
    // and a product with no entries even while other products
    // have them, unlike DETAIL-42, which reads 0 for that
    // product once the session holds any entry at all; 0 per
    // cause with no failures of that cause once that product
    // holds any entry, including a success-only product.
    const shareOfProductEntries = (product, count) =>
      entryCountByProduct[product] === 0 ? null : count / entryCountByProduct[product];
    const failedShareByStatusOfEntriesWithinProduct = {
      vigiles: {
        network_error: shareOfProductEntries("vigiles", failedByStatusByProduct.vigiles.network_error),
        http_error: shareOfProductEntries("vigiles", failedByStatusByProduct.vigiles.http_error),
        invalid_response: shareOfProductEntries("vigiles", failedByStatusByProduct.vigiles.invalid_response),
      },
      ignis: {
        network_error: shareOfProductEntries("ignis", failedByStatusByProduct.ignis.network_error),
        http_error: shareOfProductEntries("ignis", failedByStatusByProduct.ignis.http_error),
        invalid_response: shareOfProductEntries("ignis", failedByStatusByProduct.ignis.invalid_response),
      },
      sanitas: {
        network_error: shareOfProductEntries("sanitas", failedByStatusByProduct.sanitas.network_error),
        http_error: shareOfProductEntries("sanitas", failedByStatusByProduct.sanitas.http_error),
        invalid_response: shareOfProductEntries("sanitas", failedByStatusByProduct.sanitas.invalid_response),
      },
    };
    // DETAIL-45: the per-product usable-latency-count shares
    // (okLatencyCountShareByProduct): each DETAIL-36
    // product count over the session's total usable-latency
    // count, so a session where Vigiles supplied two of
    // three measurements reads that at a glance, where
    // DETAIL-35's latency-sum shares alone do not say it —
    // a product can be slow on average yet supply few
    // measurements, or fast yet supply most of them, so the
    // count share and the sum share answer different
    // questions. Derived only from the DETAIL-36 counts,
    // not a new rule: failures never contribute, even a
    // failure carrying a latency value; an ok entry with
    // no finite latency is skipped rather than counted as
    // zero; and an ok entry with an unknown or missing
    // product counts globally but moves no bucket, so the
    // shares sum to 1 only when every usable-latency
    // success carries a known product, exactly as
    // DETAIL-35's shares do. Null per product when the
    // session holds no usable ok latency at all (an empty
    // log, a failure-only log, and a success-only log with
    // no finite latency alike); 0 per product with no
    // usable latency once any measurement exists. Unlike
    // DETAIL-35, a zero total needs no special case: a
    // 0 ms latency is still a finite measurement, so it
    // counts here, and a session of only 0 ms successes
    // reads real shares, never null and never NaN.
    const shareOfAllLatencies = (count) => (latencyCount === 0 ? null : count / latencyCount);
    const okLatencyCountShareByProduct = {
      vigiles: shareOfAllLatencies(latencyCountByProduct.vigiles),
      ignis: shareOfAllLatencies(latencyCountByProduct.ignis),
      sanitas: shareOfAllLatencies(latencyCountByProduct.sanitas),
    };
    // DETAIL-46: the per-product entry-span shares of the
    // session window (entrySpanShareByProduct): each product's
    // DETAIL-17 entry span over the session's global entry
    // span (DETAIL-24), so a session where Vigiles recordings
    // stretch across the whole window while Ignis covers half
    // of it reads that at a glance — the window-coverage
    // companion to DETAIL-13's entry-count shares, where raw
    // counts alone do not say how long each product was
    // actually recording. Derived only from the DETAIL-17
    // spans and the global span, not a new rule: any status
    // moves the endpoints, and an entry with an unknown or
    // missing product moves no product bucket but still moves
    // the global window, so it stretches the denominator
    // without moving any share. These are raw ratios, never
    // clamped, and they do NOT sum to 1: product windows
    // overlap, and the global window is first-to-last across
    // products, not a sum of product windows — a share above
    // 1 or below 0 means timestamps ran out of insertion
    // order, exactly as DETAIL-17's raw spans do. Null per
    // product when the session holds no usable window at all
    // (an empty log, a single entry, or all entries at one
    // timestamp — a zero global span has no shares to divide,
    // never NaN); null per product whose own span is unknown
    // (entries recorded but no usable timestamp pair — never
    // a fabricated window); 0 per product with no entries
    // once a nonzero window exists, because it covered none
    // of the window — the deliberate contrast with DETAIL-17's
    // null, matching DETAIL-45's 0-once-a-total-exists rule —
    // and 0 per single-entry product, whose zero-length window
    // covers none of a nonzero session window.
    const shareOfSessionWindow = (product, span) => {
      if (globalEntrySpanMs === null || globalEntrySpanMs === 0) return null;
      if (entryCountByProduct[product] === 0) return 0;
      if (span === null) return null;
      return span / globalEntrySpanMs;
    };
    const entrySpanShareByProduct = {
      vigiles: shareOfSessionWindow("vigiles", entrySpanMsByProduct.vigiles),
      ignis: shareOfSessionWindow("ignis", entrySpanMsByProduct.ignis),
      sanitas: shareOfSessionWindow("sanitas", entrySpanMsByProduct.sanitas),
    };
    // DETAIL-47: the per-product usable-latency-count shares
    // of all entries (okLatencyCountShareOfEntriesByProduct):
    // each DETAIL-36 product count over the session's entry
    // total, reusing DETAIL-40's shareOfAllEntries helper.
    // Null per product on an empty log; 0 per product with
    // no usable latency once the session holds any entry.
    const okLatencyCountShareOfEntriesByProduct = {
      vigiles: shareOfAllEntries(latencyCountByProduct.vigiles),
      ignis: shareOfAllEntries(latencyCountByProduct.ignis),
      sanitas: shareOfAllEntries(latencyCountByProduct.sanitas),
    };
    // DETAIL-48: the per-product ok-span shares of the
    // global ok window (okSpanShareByProduct): each product's
    // DETAIL-21 ok span over the session's global ok span
    // (DETAIL-22), so a session where Vigiles successes
    // stretch across the whole ok window while Ignis covers
    // half of it reads that at a glance — the ok-only
    // companion to DETAIL-46's any-status entry-span
    // shares, where entry counts and entry windows alone do
    // not say how long each product was actually succeeding.
    // Derived only from the DETAIL-21 spans and the global
    // ok span, not a new rule: only successes move the
    // endpoints, so failures move neither a bucket nor the
    // global ok window, and an ok entry with an unknown or
    // missing product moves no product bucket but still
    // stretches the global window, so it dilutes every
    // share without moving any bucket. These are raw
    // ratios, never clamped, and they do NOT sum to 1:
    // product ok windows overlap, and the global window
    // is first-to-last across products, not a sum of
    // product windows — a share above 1 or below 0 means
    // timestamps ran out of insertion order, exactly as
    // DETAIL-21's raw spans do. Null per product when the
    // session holds no usable ok window at all (an empty
    // log, a failure-only log, a single success, or all
    // successes at one timestamp — a zero global ok span
    // has no shares to divide, never NaN); null per
    // product whose own ok span is unknown (successes
    // recorded but no usable timestamp pair — never a
    // fabricated window); 0 per product with no successes
    // once a nonzero ok window exists, because it covered
    // none of the window — the deliberate contrast with
    // DETAIL-21's null, matching DETAIL-46's
    // 0-once-a-window-exists rule — and 0 per
    // single-success product, whose zero-length window
    // covers none of a nonzero ok window.
    const shareOfOkWindow = (product, span) => {
      if (okSpanMs === null || okSpanMs === 0) return null;
      if (okCountByProduct[product] === 0) return 0;
      if (span === null) return null;
      return span / okSpanMs;
    };
    const okSpanShareByProduct = {
      vigiles: shareOfOkWindow("vigiles", okSpanMsByProduct.vigiles),
      ignis: shareOfOkWindow("ignis", okSpanMsByProduct.ignis),
      sanitas: shareOfOkWindow("sanitas", okSpanMsByProduct.sanitas),
    };
    // DETAIL-49: the global usable-latency-count share
    // of all entries (okLatencyCountShareOfEntries):
    // the DETAIL-36 global count over the session's entry
    // total, reusing DETAIL-40's shareOfAllEntries helper
    // — the collapsed form of DETAIL-47's per-product
    // shares, so a session where half of everything
    // recorded carries a usable latency reads at a glance.
    // Null on an empty log; 0 once the session holds any
    // entry with no usable latency. Unlike DETAIL-47, an
    // unknown- or missing-product success still moves
    // this share, since the count is product-blind.
    const okLatencyCountShareOfEntries = shareOfAllEntries(latencyCount);
    // DETAIL-50: the per-product failed-span shares of
    // the global failed window (failedSpanShareByProduct):
    // each product's DETAIL-20 failed span over the
    // session's global failed span (DETAIL-23), so a
    // session where Vigiles failures stretch across the
    // whole failed window while Ignis covers half of it
    // reads that at a glance — the failed-only mirror
    // of DETAIL-48's ok-span shares, where failure counts
    // and failure windows alone do not say how long each
    // product was actually failing. Derived only from
    // the DETAIL-20 spans and the global failed span,
    // not a new rule: only failures move the endpoints,
    // so successes move neither a bucket nor the global
    // failed window, and a failure with an unknown or
    // missing product moves no product bucket but still
    // stretches the global window, so it dilutes every
    // share without moving any bucket. These are raw
    // ratios, never clamped, and they do NOT sum to 1:
    // product failed windows overlap, and the global
    // window is first-to-last across products, not a sum
    // of product windows — a share above 1 or below 0
    // means timestamps ran out of insertion order,
    // exactly as DETAIL-20's raw spans do. Null per
    // product when the session holds no usable failed
    // window at all (an empty log, a success-only log, a
    // single failure, or all failures at one timestamp
    // — a zero global failed span has no shares to
    // divide, never NaN); null per product whose own
    // failed span is unknown (failures recorded but no
    // usable timestamp pair — never a fabricated
    // window); 0 per product with no failures once a
    // nonzero failed window exists, because it covered
    // none of the window — the deliberate contrast with
    // DETAIL-20's null, matching DETAIL-48's
    // 0-once-a-window-exists rule — and 0 per
    // single-failure product, whose zero-length window
    // covers none of a nonzero failed window.
    const shareOfFailedWindow = (product, span) => {
      if (failedSpanMs === null || failedSpanMs === 0) return null;
      if (failedCountByProduct[product] === 0) return 0;
      if (span === null) return null;
      return span / failedSpanMs;
    };
    const failedSpanShareByProduct = {
      vigiles: shareOfFailedWindow("vigiles", failedSpanMsByProduct.vigiles),
      ignis: shareOfFailedWindow("ignis", failedSpanMsByProduct.ignis),
      sanitas: shareOfFailedWindow("sanitas", failedSpanMsByProduct.sanitas),
    };
    // DETAIL-51: the global usable-latency-count share
    // of ok successes (okLatencyCountShareOfOk): the
    // DETAIL-36 global count over the session's ok total,
    // reusing DETAIL-37's shareOfAllOk helper — the
    // success-only re-base DETAIL-49's entry-total share
    // implies but does not state, so a session where
    // three of four successes carry a usable latency reads
    // differently from one where the same three
    // measurements sit in a log full of failures. Null
    // when the session holds no successes at all (an
    // empty log and a failure-only log alike — never a
    // divide by zero); 0 once successes exist but none
    // carries a usable latency. Failures sit in neither
    // side: they are not in the ok total and never count
    // as measurements, even a failure carrying a latency
    // value. An ok entry with no finite latency sits in
    // the denominator but moves no measurement, and an
    // unknown- or missing-product success still moves
    // this product-blind share, exactly as DETAIL-49's
    // does. A 0 ms latency still counts as a measurement.
    const okLatencyCountShareOfOk = ok === 0 ? null : latencyCount / ok;
    // DETAIL-52: the per-product usable-latency-count shares
    // of ok successes (okLatencyCountShareOfOkByProduct):
    // each DETAIL-36 product count over the session's ok
    // total, reusing DETAIL-37's shareOfAllOk helper — the
    // by-product split of DETAIL-51's global share, so a
    // session where Vigiles measurements are half of all
    // successes reads at a glance, where the global share
    // alone does not say which product supplied them. The
    // success-only mirror of DETAIL-47's entry-total
    // shares and the measurement-count mirror of
    // DETAIL-37's ok-count shares: the same log reads
    // differently on each base, and only this one says
    // what slice of the successes each product measured.
    // Derived only from the DETAIL-36 counts and the ok
    // total, not a new rule: failures sit in neither side
    // (they are not in the ok total and never count as
    // measurements, even a failure carrying a latency
    // value); an ok entry with no finite latency sits in
    // the denominator but moves no bucket; and an ok entry
    // with an unknown or missing product sits in the
    // denominator but moves no bucket, so the three shares
    // sum to DETAIL-51's global share only when every
    // usable-latency success carries a known product,
    // exactly as DETAIL-37's and DETAIL-47's shares do.
    // Null per product with no successes at all (an empty
    // log and a failure-only log alike — never a divide
    // by zero); 0 per product with no usable latency once
    // the session holds any success, including a
    // success-only log with no finite latency. A 0 ms
    // latency still counts as a measurement.
    const okLatencyCountShareOfOkByProduct = {
      vigiles: shareOfAllOk(latencyCountByProduct.vigiles),
      ignis: shareOfAllOk(latencyCountByProduct.ignis),
      sanitas: shareOfAllOk(latencyCountByProduct.sanitas),
    };
    // DETAIL-53: the per-product ok-span shares of the
    // global entry window (okSpanShareOfEntryWindowByProduct):
    // each product's DETAIL-21 ok span over the session's
    // global entry span (DETAIL-24), so a session where
    // Vigiles successes stretch across half the whole
    // recording window while Ignis covers a tenth of it
    // reads that at a glance — the entry-window re-basing
    // of DETAIL-48's ok-window shares, where the ok window
    // alone does not say how much of the whole session each
    // product was actually succeeding. Derived only from
    // the DETAIL-21 spans and the global entry span, not a
    // new rule: any entry moves the denominator's endpoints,
    // so failures and unknown- or missing-product entries
    // stretch the global window without moving any bucket,
    // diluting every share; only successes move a bucket.
    // These are raw ratios, never clamped, and they do NOT
    // sum to 1: product ok windows overlap, and the global
    // window is first-to-last across products, not a sum of
    // product windows — a share above 1 or below 0 means
    // timestamps ran out of insertion order, exactly as
    // DETAIL-21's raw spans do. Null per product when the
    // session holds no usable entry window at all (an empty
    // log, a single entry, or all entries at one timestamp
    // — a zero global entry span has no shares to divide,
    // never NaN); null per product whose own ok span is
    // unknown (successes recorded but no usable timestamp
    // pair — never a fabricated window); 0 per product
    // with no successes once a nonzero entry window exists,
    // because it covered none of the window — the
    // deliberate contrast with DETAIL-21's null, matching
    // DETAIL-48's 0-once-a-window-exists rule — and 0 per
    // single-success product, whose zero-length window
    // covers none of a nonzero entry window.
    const shareOfEntryWindow = (product, span) => {
      if (globalEntrySpanMs === null || globalEntrySpanMs === 0) return null;
      if (okCountByProduct[product] === 0) return 0;
      if (span === null) return null;
      return span / globalEntrySpanMs;
    };
    const okSpanShareOfEntryWindowByProduct = {
      vigiles: shareOfEntryWindow("vigiles", okSpanMsByProduct.vigiles),
      ignis: shareOfEntryWindow("ignis", okSpanMsByProduct.ignis),
      sanitas: shareOfEntryWindow("sanitas", okSpanMsByProduct.sanitas),
    };
    // DETAIL-54: the per-product usable-latency-count shares
    // of that product's own ok successes (renumbered
    // DETAIL-54 after Rowan's distinct DETAIL-53 landed
    // first, both sides kept in the merge):
    // (okLatencyCountShareOfOwnOkByProduct): each
    // DETAIL-36 product count over that product's own ok
    // count — the within-product re-base DETAIL-52's
    // global-ok shares imply but do not state, so a
    // session where half of Vigiles successes carry a
    // latency reads at a glance even when Vigiles is a
    // small slice of all successes, and a product whose
    // successes are all measured reads 1 whatever its
    // share of the session. Derived only from the
    // DETAIL-36 counts and the per-product ok counts, not
    // a new rule: failures sit in neither side; an ok
    // entry with no finite latency sits in its own
    // product's denominator but moves no bucket; and an
    // ok entry with an unknown or missing product moves
    // no bucket and no product denominator, so it dilutes
    // DETAIL-52's shares without touching these — the
    // deliberate contrast with DETAIL-52, matching
    // DETAIL-44's within-product rule. Null per product
    // with no successes of that product at all (an empty
    // log, a failure-only log, and any product with no
    // successes yet alike — never a divide by zero);
    // 0 per product with successes but no usable latency,
    // including a success-only log with no finite latency.
    // A 0 ms latency still counts as a measurement.
    const okLatencyCountShareOfOwnOkByProduct = {
      vigiles: okCountByProduct.vigiles === 0 ? null : latencyCountByProduct.vigiles / okCountByProduct.vigiles,
      ignis: okCountByProduct.ignis === 0 ? null : latencyCountByProduct.ignis / okCountByProduct.ignis,
      sanitas: okCountByProduct.sanitas === 0 ? null : latencyCountByProduct.sanitas / okCountByProduct.sanitas,
    };
    // DETAIL-55: the per-product failed-span shares of
    // the global entry window
    // (failedSpanShareOfEntryWindowByProduct): each
    // product's DETAIL-20 failed span over the session's
    // global entry span (DETAIL-24), so a session where
    // Vigiles failures stretch across half the whole
    // recording window while Ignis covers a tenth of it
    // reads that at a glance — the failed mirror of
    // DETAIL-53's ok-span shares, and the entry-window
    // re-basing of DETAIL-50's failed-window shares,
    // where the failed window alone does not say how
    // much of the whole session each product was
    // actually failing. Derived only from the DETAIL-20
    // spans and the global entry span, not a new rule:
    // any entry moves the denominator's endpoints, so
    // successes and unknown- or missing-product entries
    // stretch the global window without moving any
    // bucket, diluting every share; only failures move
    // a bucket. These are raw ratios, never clamped,
    // and they do NOT sum to 1: product failed windows
    // overlap, and the global window is first-to-last
    // across products, not a sum of product windows — a
    // share above 1 or below 0 means timestamps ran out
    // of insertion order, exactly as DETAIL-20's raw
    // spans do. Null per product when the session holds
    // no usable entry window at all (an empty log, a
    // single entry, or all entries at one timestamp — a
    // zero global entry span has no shares to divide,
    // never NaN); null per product whose own failed span
    // is unknown (failures recorded but no usable
    // timestamp pair — never a fabricated window); 0 per
    // product with no failures once a nonzero entry
    // window exists, because it covered none of the
    // window — the deliberate contrast with DETAIL-20's
    // null, matching DETAIL-53's 0-once-a-window-exists
    // rule — and 0 per single-failure product, whose
    // zero-length window covers none of a nonzero entry
    // window.
    const shareFailedOfEntryWindow = (product, span) => {
      if (globalEntrySpanMs === null || globalEntrySpanMs === 0) return null;
      if (failedCountByProduct[product] === 0) return 0;
      if (span === null) return null;
      return span / globalEntrySpanMs;
    };
    const failedSpanShareOfEntryWindowByProduct = {
      vigiles: shareFailedOfEntryWindow("vigiles", failedSpanMsByProduct.vigiles),
      ignis: shareFailedOfEntryWindow("ignis", failedSpanMsByProduct.ignis),
      sanitas: shareFailedOfEntryWindow("sanitas", failedSpanMsByProduct.sanitas),
    };
    // DETAIL-56 (renumbered after Rowan's distinct DETAIL-55 landed first, both sides kept in the merge):
    // the per-product usable-latency-count shares
    // of that product's own entries
    // (okLatencyCountShareOfOwnEntriesByProduct): each
    // DETAIL-36 product count over that product's own
    // entry total (DETAIL-14) — the within-product
    // re-base DETAIL-47's entry-total shares imply but do
    // not state, so a session where half of everything
    // Vigiles recorded carries a latency reads at a glance
    // even when Vigiles is a small slice of all entries,
    // and a product whose every entry is a measured
    // success reads 1 whatever its share of the session.
    // Derived only from the DETAIL-36 counts and the
    // per-product entry counts, not a new rule: failures
    // sit in the denominator but move no bucket (they are
    // entries of the product but never measurements, even
    // a failure carrying a latency value); an ok entry
    // with no finite latency sits in its own product's
    // denominator but moves no bucket; and an ok entry
    // with an unknown or missing product moves no bucket
    // and no product denominator, so it dilutes DETAIL-47's
    // shares without touching these — the deliberate
    // contrast with DETAIL-47, matching DETAIL-54's
    // within-product rule and DETAIL-44's. Null per
    // product with no entries of that product at all (an
    // empty log, and any product with no entries yet
    // alike — never a divide by zero); 0 per product with
    // entries but no usable latency, including a
    // failure-only product and a success-only product
    // with no finite latency — the deliberate contrast
    // with DETAIL-54, whose failure-only product reads
    // null because its denominator is the ok count. A
    // 0 ms latency still counts as a measurement.
    const okLatencyCountShareOfOwnEntriesByProduct = {
      vigiles: entryCountByProduct.vigiles === 0 ? null : latencyCountByProduct.vigiles / entryCountByProduct.vigiles,
      ignis: entryCountByProduct.ignis === 0 ? null : latencyCountByProduct.ignis / entryCountByProduct.ignis,
      sanitas: entryCountByProduct.sanitas === 0 ? null : latencyCountByProduct.sanitas / entryCountByProduct.sanitas,
    };
    // DETAIL-57: the global failed-span share of the
    // global entry window (failedSpanShareOfEntryWindow):
    // the session's DETAIL-23 global failed span over
    // its DETAIL-24 global entry span — the collapsed
    // form of DETAIL-55's per-product shares, so a
    // session where failures stretch across half the
    // whole recording window reads that at a glance,
    // where the three by-product shares alone do not
    // say how much of the window failures covered in
    // total. Derived only from the two global spans,
    // not a new rule: any entry moves the denominator's
    // endpoints, so successes stretch the window without
    // moving the numerator. The numerator is
    // product-blind, unlike DETAIL-55: a failure with an
    // unknown or missing product still opens and closes
    // the global failed span (DETAIL-23's endpoints
    // cover it), so it moves this share where it moves
    // no DETAIL-55 bucket — the deliberate contrast
    // with DETAIL-55, matching DETAIL-49's and
    // DETAIL-51's product-blind globals. This is a raw
    // ratio, never clamped, and it is NOT the sum of
    // DETAIL-55's shares: product failed windows overlap
    // and the global window is first-to-last across
    // products, not a sum of product windows — a share
    // above 1 or below 0 means timestamps ran out of
    // insertion order, exactly as DETAIL-23's raw span
    // does. Null when the session holds no usable entry
    // window at all (an empty log, a single entry, or
    // all entries at one timestamp — a zero global entry
    // span has no share to divide, never NaN); null
    // when failures were recorded but the global failed
    // span is unknown (no usable timestamp pair — never
    // a fabricated window); 0 with no failures once a
    // nonzero entry window exists, because failures
    // covered none of the window — the deliberate
    // contrast with DETAIL-23's null — and 0 for a
    // single-failure session, whose zero-length failed
    // window covers none of a nonzero entry window.
    const failedSpanShareOfEntryWindow =
      globalEntrySpanMs === null || globalEntrySpanMs === 0
        ? null
        : failed === 0
          ? 0
          : failedSpanMs === null
            ? null
            : failedSpanMs / globalEntrySpanMs;
    // DETAIL-58: the global ok-span share of the
    // global entry window (okSpanShareOfEntryWindow):
    // the session's DETAIL-22 global ok span over its
    // DETAIL-24 global entry span — the ok mirror of
    // DETAIL-57's failed share, and the collapsed form
    // of DETAIL-53's per-product ok-span shares, so a
    // session where successes stretch across half the
    // whole recording window reads that at a glance,
    // where the three by-product shares alone do not
    // say how much of the window successes covered in
    // total. Derived only from the two global spans,
    // not a new rule: any entry moves the denominator's
    // endpoints, so failures stretch the window without
    // moving the numerator. The numerator is
    // product-blind, unlike DETAIL-53: a success with an
    // unknown or missing product still opens and closes
    // the global ok span (DETAIL-22's endpoints cover
    // it), so it moves this share where it moves no
    // DETAIL-53 bucket — the deliberate contrast with
    // DETAIL-53, matching DETAIL-57's and DETAIL-49's
    // product-blind globals. This is a raw ratio, never
    // clamped, and it is NOT the sum of DETAIL-53's
    // shares: product ok windows overlap and the global
    // window is first-to-last across products, not a sum
    // of product windows — a share above 1 or below 0
    // means timestamps ran out of insertion order,
    // exactly as DETAIL-22's raw span does. Null when
    // the session holds no usable entry window at all
    // (an empty log, a single entry, or all entries at
    // one timestamp — a zero global entry span has no
    // share to divide, never NaN); null when successes
    // were recorded but the global ok span is unknown
    // (no usable timestamp pair — never a fabricated
    // window); 0 with no successes once a nonzero entry
    // window exists, because successes covered none of
    // the window — the deliberate contrast with
    // DETAIL-22's null — and 0 for a single-success
    // session, whose zero-length ok window covers none
    // of a nonzero entry window.
    const okSpanShareOfEntryWindow =
      globalEntrySpanMs === null || globalEntrySpanMs === 0
        ? null
        : ok === 0
          ? 0
          : okSpanMs === null
            ? null
            : okSpanMs / globalEntrySpanMs;
    // DETAIL-59 (renumbered after Rowan's distinct DETAIL-58 landed first, both sides kept in the merge):
    // the per-product failed-span shares of
    // that product's own entry window
    // (failedSpanShareOfOwnEntryWindowByProduct): each
    // product's DETAIL-20 failed span over that
    // product's own DETAIL-17 entry span — the
    // within-product re-base DETAIL-55's global-entry
    // shares imply but do not state, so a session
    // where Vigiles failures stretch across half of
    // everything Vigiles itself recorded reads that at
    // a glance even when Vigiles is a small slice of
    // the whole session, and a product whose failures
    // span its whole own window reads 1 whatever its
    // share of the session. Derived only from the
    // DETAIL-20 spans and the DETAIL-17 spans, not a
    // new rule: only that product's entries move its
    // denominator's endpoints, so other products'
    // entries stretch DETAIL-55's global window
    // without touching these, and an unknown- or
    // missing-product failure moves no bucket and no
    // product denominator, unlike DETAIL-57's
    // product-blind global — the deliberate contrast
    // with DETAIL-57, matching DETAIL-56's and
    // DETAIL-54's within-product rule. These are raw
    // ratios, never clamped: a share above 1 or below
    // 0 means timestamps ran out of insertion order,
    // exactly as DETAIL-20's raw spans do. Null per
    // product with no usable own entry window at all
    // (no entries of that product, a single entry of
    // that product, or all of that product's entries
    // at one timestamp — a zero own entry span has
    // no share to divide, never NaN); null per
    // product whose own failed span is unknown
    // (failures recorded but no usable timestamp pair
    // — never a fabricated window); 0 per product
    // with no failures once a nonzero own entry
    // window exists, because it covered none of its
    // own window — the deliberate contrast with
    // DETAIL-20's null, matching DETAIL-55's
    // 0-once-a-window-exists rule — and 0 per
    // single-failure product, whose zero-length
    // failed window covers none of a nonzero own
    // entry window.
    const shareFailedOfOwnEntryWindow = (product, span) => {
      if (entrySpanMsByProduct[product] === null || entrySpanMsByProduct[product] === 0) return null;
      if (failedCountByProduct[product] === 0) return 0;
      if (span === null) return null;
      return span / entrySpanMsByProduct[product];
    };
    const failedSpanShareOfOwnEntryWindowByProduct = {
      vigiles: shareFailedOfOwnEntryWindow("vigiles", failedSpanMsByProduct.vigiles),
      ignis: shareFailedOfOwnEntryWindow("ignis", failedSpanMsByProduct.ignis),
      sanitas: shareFailedOfOwnEntryWindow("sanitas", failedSpanMsByProduct.sanitas),
    };
    // DETAIL-60: the per-product ok-span shares of
    // that product's own entry window
    // (okSpanShareOfOwnEntryWindowByProduct): each
    // product's DETAIL-21 ok span over that
    // product's own DETAIL-17 entry span — the
    // within-product re-base DETAIL-53's global-entry
    // shares imply but do not state, and the ok
    // mirror of DETAIL-59's failed shares, so a
    // session where Vigiles successes stretch across
    // half of everything Vigiles itself recorded
    // reads that at a glance even when Vigiles is a
    // small slice of the whole session, and a
    // product whose successes span its whole own
    // window reads 1 whatever its share of the
    // session. Derived only from the DETAIL-21 spans
    // and the DETAIL-17 spans, not a new rule: only
    // that product's entries move its denominator's
    // endpoints, so other products' entries stretch
    // DETAIL-53's global window without touching
    // these, and an unknown- or missing-product
    // success moves no bucket and no product
    // denominator, unlike DETAIL-58's product-blind
    // global — the deliberate contrast with
    // DETAIL-58, matching DETAIL-59's and DETAIL-54's
    // within-product rule. These are raw ratios,
    // never clamped: a share above 1 or below 0 means
    // timestamps ran out of insertion order, exactly
    // as DETAIL-21's raw spans do. Null per product
    // with no usable own entry window at all (no
    // entries of that product, a single entry of
    // that product, or all of that product's entries
    // at one timestamp — a zero own entry span has
    // no share to divide, never NaN); null per
    // product whose own ok span is unknown
    // (successes recorded but no usable timestamp
    // pair — never a fabricated window); 0 per
    // product with no successes once a nonzero own
    // entry window exists, because it covered none
    // of its own window — the deliberate contrast
    // with DETAIL-21's null, matching DETAIL-59's
    // 0-once-a-window-exists rule — and 0 per
    // single-success product, whose zero-length ok
    // window covers none of a nonzero own entry
    // window.
    const shareOkOfOwnEntryWindow = (product, span) => {
      if (entrySpanMsByProduct[product] === null || entrySpanMsByProduct[product] === 0) return null;
      if (okCountByProduct[product] === 0) return 0;
      if (span === null) return null;
      return span / entrySpanMsByProduct[product];
    };
    const okSpanShareOfOwnEntryWindowByProduct = {
      vigiles: shareOkOfOwnEntryWindow("vigiles", okSpanMsByProduct.vigiles),
      ignis: shareOkOfOwnEntryWindow("ignis", okSpanMsByProduct.ignis),
      sanitas: shareOkOfOwnEntryWindow("sanitas", okSpanMsByProduct.sanitas),
    };
    // DETAIL-61: the per-product ok-count shares of
    // that product's own entries
    // (okShareOfOwnEntriesByProduct): each product's
    // DETAIL-1 ok count over that product's own
    // entry total — the within-product re-base
    // DETAIL-41's entry-total shares imply but do not
    // state, so a session where Vigiles succeeded on
    // three of its own four entries reads 3/4 at a
    // glance even when Vigiles is a small slice of
    // the whole session, and a product whose every
    // entry succeeded reads 1 whatever its share of
    // the session. This is the product's own success
    // rate, continuing the within-product line of
    // DETAIL-54/56/59/60: only that product's entries
    // move its denominator, so other products'
    // entries dilute DETAIL-41's shares without
    // touching these, and an unknown- or
    // missing-product entry moves no bucket and no
    // product denominator, unlike DETAIL-41 where it
    // sits in the global denominator. Derived only
    // from the DETAIL-1 counts and the per-product
    // entry totals, not a new rule: failures sit in
    // the denominator but move no bucket (they are
    // not successes), an ok entry with no finite
    // latency still counts here — this is a count
    // share, not a latency share, so DETAIL-35's skip
    // rule does not apply — and unlike the span
    // shares, a single entry still divides: a single
    // success reads 1 and a single failure reads 0,
    // because a count denominator is never a zero
    // window. Null per product with no entries of
    // that product at all, empty log alike — nothing
    // to divide by, never NaN; 0 per product with
    // entries but no successes.
    const shareOkOfOwnEntries = (product) =>
      entryCountByProduct[product] === 0 ? null : okCountByProduct[product] / entryCountByProduct[product];
    const okShareOfOwnEntriesByProduct = {
      vigiles: shareOkOfOwnEntries("vigiles"),
      ignis: shareOkOfOwnEntries("ignis"),
      sanitas: shareOkOfOwnEntries("sanitas"),
    };
    // DETAIL-62: the per-product failed-span shares of
    // that product's own success window
    // (failedSpanShareOfOwnOkWindowByProduct): each
    // product's DETAIL-20 failed span over that
    // product's own DETAIL-21 ok span — the cross-span
    // within-product re-base DETAIL-59/60's own-entry
    // shares imply but do not state, so a session
    // where Vigiles failures stretch across half of
    // everything Vigiles itself succeeded across reads
    // that at a glance even when Vigiles failures are
    // a small slice of its whole recording, and a
    // product whose failures span its whole success
    // window reads 1 whatever its share of the
    // session. Derived only from the DETAIL-20 spans
    // and the DETAIL-21 spans, not a new rule: only
    // that product's successes move its denominator's
    // endpoints, so other products' successes stretch
    // no share here, and an unknown- or
    // missing-product success or failure moves no
    // bucket and no product denominator, unlike any
    // product-blind global. These are raw ratios,
    // never clamped: a share above 1 or below 0 means
    // timestamps ran out of insertion order, exactly
    // as DETAIL-20/21's raw spans do. Null per product
    // with no usable own success window at all (no
    // successes of that product, a single success of
    // that product, or all of that product's successes
    // at one timestamp — a zero own ok span has no
    // share to divide, never NaN); null per product
    // whose own failed span is unknown (failures
    // recorded but no usable timestamp pair — never
    // a fabricated window); 0 per product with no
    // failures once a nonzero own success window
    // exists, because failures covered none of its
    // success window — and 0 per single-failure
    // product, whose zero-length failed window covers
    // none of a nonzero success window.
    const shareFailedOfOwnOkWindow = (product, span) => {
      if (okSpanMsByProduct[product] === null || okSpanMsByProduct[product] === 0) return null;
      if (failedCountByProduct[product] === 0) return 0;
      if (span === null) return null;
      return span / okSpanMsByProduct[product];
    };
    const failedSpanShareOfOwnOkWindowByProduct = {
      vigiles: shareFailedOfOwnOkWindow("vigiles", failedSpanMsByProduct.vigiles),
      ignis: shareFailedOfOwnOkWindow("ignis", failedSpanMsByProduct.ignis),
      sanitas: shareFailedOfOwnOkWindow("sanitas", failedSpanMsByProduct.sanitas),
    };
    // DETAIL-63: the per-product ok-span shares of
    // that product's own failure window
    // (okSpanShareOfOwnFailedWindowByProduct): each
    // product's DETAIL-21 ok span over that
    // product's own DETAIL-20 failed span — the
    // mirror of DETAIL-62, the cross-span
    // within-product re-base DETAIL-59/60's own-entry
    // shares imply but do not state from the other
    // side, so a session where Vigiles successes
    // stretch across half of everything Vigiles
    // itself failed across reads that at a glance
    // even when Vigiles successes are a small slice
    // of its whole recording, and a product whose
    // successes span its whole failure window reads 1
    // whatever its share of the session. Derived
    // only from the DETAIL-21 spans and the
    // DETAIL-20 spans, not a new rule: only that
    // product's failures move its denominator's
    // endpoints, so other products' failures stretch
    // no share here, and an unknown- or
    // missing-product success or failure moves no
    // bucket and no product denominator, unlike any
    // product-blind global. These are raw ratios,
    // never clamped: a share above 1 or below 0 means
    // timestamps ran out of insertion order, exactly
    // as DETAIL-20/21's raw spans do. Null per product
    // with no usable own failure window at all (no
    // failures of that product, a single failure of
    // that product, or all of that product's failures
    // at one timestamp — a zero own failed span has
    // no share to divide, never NaN or Infinity);
    // null per product whose own ok span is unknown
    // (successes recorded but no usable timestamp
    // pair — never a fabricated window); 0 per product
    // with no successes once a nonzero own failure
    // window exists, because successes covered none
    // of its failure window — and 0 per single-success
    // product, whose zero-length ok window covers
    // none of a nonzero failure window.
    const shareOkOfOwnFailedWindow = (product, span) => {
      if (failedSpanMsByProduct[product] === null || failedSpanMsByProduct[product] === 0) return null;
      if (okCountByProduct[product] === 0) return 0;
      if (span === null) return null;
      return span / failedSpanMsByProduct[product];
    };
    const okSpanShareOfOwnFailedWindowByProduct = {
      vigiles: shareOkOfOwnFailedWindow("vigiles", okSpanMsByProduct.vigiles),
      ignis: shareOkOfOwnFailedWindow("ignis", okSpanMsByProduct.ignis),
      sanitas: shareOkOfOwnFailedWindow("sanitas", okSpanMsByProduct.sanitas),
    };
    // DETAIL-64: the global ok-span share of the
    // global failed window (okSpanShareOfFailedWindow):
    // the session's DETAIL-22 global ok span over its
    // DETAIL-23 global failed span — the cross-span
    // re-base DETAIL-57's and DETAIL-58's
    // entry-window shares imply but do not state, so
    // a session where successes stretched twice as
    // long as failures reads that at a glance, where
    // the entry-window shares alone do not say how
    // the two windows compare to each other.
    // Derived only from the two global spans, not a
    // new rule. The numerator and the denominator
    // are both product-blind, unlike DETAIL-53's and
    // DETAIL-55's buckets: a success with an unknown
    // or missing product still opens and closes the
    // global ok span, and a failure with an unknown
    // or missing product still opens and closes the
    // global failed span, so either moves this share
    // where it moves no by-product bucket — the
    // deliberate contrast with DETAIL-53/55,
    // matching DETAIL-57's and DETAIL-58's
    // product-blind globals. This is a raw ratio,
    // never clamped, and it is NOT a difference of
    // DETAIL-57's and DETAIL-58's shares: a share
    // above 1 or below 0 means timestamps ran out
    // of insertion order, exactly as DETAIL-22's and
    // DETAIL-23's raw spans do. Null when the
    // session holds no usable failed window at all
    // (an empty log, a single failure, or all
    // failures at one timestamp — a zero failed span
    // has no share to divide, never NaN); null when
    // successes were recorded but the global ok span
    // is unknown (no usable timestamp pair — never
    // a fabricated window); 0 with no successes
    // once a nonzero failed window exists, because
    // successes covered none of the failure window
    // — the deliberate contrast with DETAIL-22's
    // null — and 0 for a single-success session,
    // whose zero-length ok window covers none of a
    // nonzero failed window.
    const okSpanShareOfFailedWindow =
      failedSpanMs === null || failedSpanMs === 0
        ? null
        : ok === 0
          ? 0
          : okSpanMs === null
            ? null
            : okSpanMs / failedSpanMs;
    // DETAIL-65: the global failed-span share of the
    // global ok window (failedSpanShareOfOkWindow):
    // the session's DETAIL-23 global failed span over
    // its DETAIL-22 global ok span — the mirror of
    // DETAIL-64, the cross-span re-base DETAIL-57's
    // and DETAIL-58's entry-window shares imply but
    // do not state from the other side, so a session
    // where failures stretched twice as long as
    // successes reads that at a glance, where the
    // entry-window shares alone do not say how the
    // two windows compare to each other. Derived
    // only from the two global spans, not a new rule.
    // The numerator and the denominator are both
    // product-blind, unlike DETAIL-53's and
    // DETAIL-55's buckets: a failure with an unknown
    // or missing product still opens and closes the
    // global failed span, and a success with an
    // unknown or missing product still opens and
    // closes the global ok span, so either moves
    // this share where it moves no by-product
    // bucket — the deliberate contrast with
    // DETAIL-53/55, matching DETAIL-57's, DETAIL-58's
    // and DETAIL-64's product-blind globals. This is
    // a raw ratio, never clamped, and it is NOT a
    // difference of DETAIL-57's and DETAIL-58's
    // shares: a share above 1 or below 0 means
    // timestamps ran out of insertion order, exactly
    // as DETAIL-22's and DETAIL-23's raw spans do.
    // Null when the session holds no usable ok
    // window at all (an empty log, a single success,
    // or all successes at one timestamp — a zero ok
    // span has no share to divide, never NaN); null
    // when failures were recorded but the global
    // failed span is unknown (no usable timestamp
    // pair — never a fabricated window); 0 with no
    // failures once a nonzero ok window exists,
    // because failures covered none of the success
    // window — the deliberate contrast with
    // DETAIL-23's null — and 0 for a single-failure
    // session, whose zero-length failed window
    // covers none of a nonzero ok window.
    const failedSpanShareOfOkWindow =
      okSpanMs === null || okSpanMs === 0
        ? null
        : failed === 0
          ? 0
          : failedSpanMs === null
            ? null
            : failedSpanMs / okSpanMs;
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
      // DETAIL-40: the per-product failed shares of all
      // entries (failedShareOfEntriesByProduct): each
      // product's DETAIL-34 failed count over the session
      // entry total — the failure mirror of DETAIL-37's
      // success shares. Null per product on an empty log;
      // 0 per product with no failures of that product once
      // the session holds any entry.
      failedShareOfEntriesByProduct,
      // DETAIL-41: the per-product successful-count shares
      // of all entries (okShareOfTotalByProduct): each
      // product's ok count over the session total entry
      // count — the entry-total mirror of DETAIL-37's
      // ok-total shares and the success mirror of
      // DETAIL-40's failed shares. Null per product on an
      // empty log; 0 per product with no successes once the
      // session holds any entry, failure-only log included.
      okShareOfTotalByProduct,
      // DETAIL-42: the per-product failure-cause shares of
      // all entries (failedShareByStatusOfEntriesByProduct):
      // each DETAIL-9 product-cause count over the session
      // entry total — the entry-total mirror of DETAIL-29's
      // failed-total cells and the cause split of
      // DETAIL-40's failed shares. Null per cell on an
      // empty log; 0 per cell with no failures of that
      // combination once the session holds any entry.
      failedShareByStatusOfEntriesByProduct,
      // DETAIL-43: the global failure-cause shares of all
      // entries (failedShareByStatusOfEntries): each
      // DETAIL-9 global cause count over the session
      // entry total — the entry-total mirror of
      // DETAIL-31's failed-total shares and the collapsed
      // form of DETAIL-42's nine cells. Null per cause on
      // an empty log; 0 per cause with no failures of that
      // cause once the session holds any entry. The three
      // cells always sum to the global failed share.
      failedShareByStatusOfEntries,
      // DETAIL-44: the per-product failure-cause shares of
      // that product's own entries
      // (failedShareByStatusOfEntriesWithinProduct): each
      // DETAIL-9 product-cause count over that product's own
      // entry total — the within-product mirror of DETAIL-42's
      // global-entry cells and the cause split of DETAIL-12's
      // per-product failed shares. Null per product with no
      // entries of that product; 0 per cause with no failures
      // of that cause once that product holds any entry.
      failedShareByStatusOfEntriesWithinProduct,
      // DETAIL-45: the per-product usable-latency-count
      // shares (okLatencyCountShareByProduct): each
      // DETAIL-36 product count over the session's total
      // usable-latency count — the count mirror of
      // DETAIL-35's latency-sum shares. Null per product
      // with no usable ok latency in the session; 0 per
      // product with no usable latency once any
      // measurement exists, including a session of only
      // 0 ms successes.
      okLatencyCountShareByProduct,
      // DETAIL-46: the per-product entry-span shares of the
      // session window (entrySpanShareByProduct): each
      // product's DETAIL-17 entry span over the global entry
      // span — the window-coverage companion to DETAIL-13's
      // entry-count shares. Raw ratios, never clamped, and
      // they do NOT sum to 1 (product windows overlap).
      // Null per product with no usable session window, or
      // with entries but no usable timestamp pair; 0 per
      // product with no entries once a nonzero window exists.
      entrySpanShareByProduct,
      // DETAIL-47: the per-product usable-latency-count
      // shares of all entries
      // (okLatencyCountShareOfEntriesByProduct): each
      // product's DETAIL-36 count over the session entry
      // total — the entry-total mirror of DETAIL-45's
      // measurement-total shares. Null per product on an
      // empty log; 0 per product with no usable latency
      // once the session holds any entry.
      okLatencyCountShareOfEntriesByProduct,
      // DETAIL-48: the per-product ok-span shares of the
      // global ok window (okSpanShareByProduct): each
      // product's DETAIL-21 ok span over the global ok
      // span — the ok-only companion to DETAIL-46's
      // entry-span shares. Raw ratios, never clamped, and
      // they do NOT sum to 1 (product ok windows overlap).
      // Null per product with no usable ok window, or
      // with successes but no usable timestamp pair; 0 per
      // product with no successes once a nonzero ok
      // window exists.
      okSpanShareByProduct,
      // DETAIL-49: the global usable-latency-count share
      // of all entries (okLatencyCountShareOfEntries):
      // the DETAIL-36 global count over the session entry
      // total — the collapsed form of DETAIL-47's
      // per-product shares. Null on an empty log; 0 once
      // the session holds any entry with no usable
      // latency. It equals the sum of DETAIL-47's shares
      // only when every usable-latency success carries a
      // known product; an unknown- or missing-product
      // success sits in this share but moves no bucket.
      okLatencyCountShareOfEntries,
      // DETAIL-50: the per-product failed-span shares of
      // the global failed window
      // (failedSpanShareByProduct): each product's
      // DETAIL-20 failed span over the global failed
      // span — the failed-only mirror of DETAIL-48's
      // ok-span shares. Raw ratios, never clamped, and
      // they do NOT sum to 1 (product failed windows
      // overlap). Null per product with no usable failed
      // window, or with failures but no usable timestamp
      // pair; 0 per product with no failures once a
      // nonzero failed window exists.
      failedSpanShareByProduct,
      // DETAIL-51: the global usable-latency-count share
      // of ok successes (okLatencyCountShareOfOk): the
      // DETAIL-36 global count over the session ok total
      // — the success-only re-base of DETAIL-49's
      // entry-total share. Null with no successes at all;
      // 0 once successes exist but none carries a usable
      // latency. Failures move neither side; an ok entry
      // with no finite latency sits in the denominator
      // only; a 0 ms latency still counts.
      okLatencyCountShareOfOk,
      // DETAIL-52: the per-product usable-latency-count
      // shares of ok successes
      // (okLatencyCountShareOfOkByProduct): each
      // DETAIL-36 product count over the session ok total
      // — the by-product split of DETAIL-51's global
      // share. Null per product with no successes at all;
      // 0 per product with no usable latency once the
      // session holds any success. The shares sum to
      // DETAIL-51 only when every usable-latency success
      // carries a known product; an unknown- or
      // missing-product success sits in the denominator
      // but moves no bucket.
      okLatencyCountShareOfOkByProduct,
      // DETAIL-53: the per-product ok-span shares of the
      // global entry window
      // (okSpanShareOfEntryWindowByProduct): each
      // product's DETAIL-21 ok span over the global entry
      // span — the entry-window re-basing of DETAIL-48's
      // ok-window shares. Raw ratios, never clamped, and
      // they do NOT sum to 1 (product ok windows overlap).
      // Null per product with no usable entry window, or
      // with successes but no usable timestamp pair; 0 per
      // product with no successes once a nonzero entry
      // window exists.
      okSpanShareOfEntryWindowByProduct,
      // DETAIL-54: the per-product usable-latency-count
      // shares of that product's own ok successes
      // (okLatencyCountShareOfOwnOkByProduct): each
      // DETAIL-36 product count over that product's own
      // ok count — the within-product re-base of
      // DETAIL-52's global-ok shares. Null per product
      // with no successes of that product; 0 per product
      // with successes but no usable latency. An unknown-
      // or missing-product success moves no bucket and no
      // product denominator, unlike DETAIL-52.
      okLatencyCountShareOfOwnOkByProduct,
      // DETAIL-55: the per-product failed-span shares of
      // the global entry window
      // (failedSpanShareOfEntryWindowByProduct): each
      // product's DETAIL-20 failed span over the global
      // entry span — the failed mirror of DETAIL-53's
      // ok-span shares, and the entry-window re-basing
      // of DETAIL-50's failed-window shares. Raw ratios,
      // never clamped, and they do NOT sum to 1 (product
      // failed windows overlap). Null per product with
      // no usable entry window, or with failures but no
      // usable timestamp pair; 0 per product with no
      // failures once a nonzero entry window exists.
      failedSpanShareOfEntryWindowByProduct,
      // DETAIL-56: the per-product usable-latency-count
      // shares of that product's own entries
      // (okLatencyCountShareOfOwnEntriesByProduct): each
      // product's DETAIL-36 count over that product's own
      // entry total — the within-product re-base of
      // DETAIL-47's entry-total shares. Null per product
      // with no entries of that product; 0 per product
      // with entries but no usable latency, failure-only
      // product included. An unknown- or missing-product
      // entry moves no bucket and no product denominator,
      // unlike DETAIL-47.
      okLatencyCountShareOfOwnEntriesByProduct,
      // DETAIL-57: the global failed-span share of the
      // global entry window (failedSpanShareOfEntryWindow):
      // the DETAIL-23 global failed span over the
      // DETAIL-24 global entry span — the collapsed form
      // of DETAIL-55's per-product shares. Null with no
      // usable entry window, or with failures but no
      // usable failed span; 0 with no failures once a
      // nonzero entry window exists. Unknown- or
      // missing-product failures move this product-blind
      // share, unlike DETAIL-55.
      failedSpanShareOfEntryWindow,
      // DETAIL-58: the global ok-span share of the
      // global entry window (okSpanShareOfEntryWindow):
      // the DETAIL-22 global ok span over the DETAIL-24
      // global entry span — the ok mirror of DETAIL-57
      // and the collapsed form of DETAIL-53's per-product
      // shares. Null with no usable entry window, or with
      // successes but no usable ok span; 0 with no
      // successes once a nonzero entry window exists.
      // Unknown- or missing-product successes move this
      // product-blind share, unlike DETAIL-53.
      okSpanShareOfEntryWindow,
      // DETAIL-59: the per-product failed-span shares
      // of that product's own entry window
      // (failedSpanShareOfOwnEntryWindowByProduct): each
      // product's DETAIL-20 failed span over that
      // product's own DETAIL-17 entry span — the
      // within-product re-base of DETAIL-55's
      // global-entry shares. Null per product with no
      // usable own entry window, or with failures but
      // no usable failed timestamp pair; 0 per product
      // with no failures once a nonzero own entry
      // window exists. An unknown- or missing-product
      // failure moves no bucket and no denominator,
      // unlike DETAIL-57.
      failedSpanShareOfOwnEntryWindowByProduct,
      // DETAIL-60: the per-product ok-span shares
      // of that product's own entry window
      // (okSpanShareOfOwnEntryWindowByProduct): each
      // product's DETAIL-21 ok span over that
      // product's own DETAIL-17 entry span — the
      // within-product re-base of DETAIL-53's
      // global-entry shares, and the ok mirror of
      // DETAIL-59. Null per product with no usable
      // own entry window, or with successes but no
      // usable ok timestamp pair; 0 per product with
      // no successes once a nonzero own entry window
      // exists. An unknown- or missing-product
      // success moves no bucket and no denominator,
      // unlike DETAIL-58.
      okSpanShareOfOwnEntryWindowByProduct,
      // DETAIL-61: the per-product ok-count shares
      // of that product's own entries
      // (okShareOfOwnEntriesByProduct): each
      // product's DETAIL-1 ok count over that
      // product's own entry total — the
      // within-product re-base of DETAIL-41's
      // entry-total shares, the product's own success
      // rate. Null per product with no entries of
      // that product; 0 with entries but no
      // successes; 1 when every entry of that product
      // succeeded. An unknown- or missing-product
      // entry moves no bucket and no denominator,
      // unlike DETAIL-41.
      okShareOfOwnEntriesByProduct,
      // DETAIL-62: the per-product failed-span shares
      // of that product's own success window
      // (failedSpanShareOfOwnOkWindowByProduct): each
      // product's DETAIL-20 failed span over that
      // product's own DETAIL-21 ok span. Null per
      // product with no usable own success window, or
      // with failures but no usable failed timestamp
      // pair; 0 per product with no failures once a
      // nonzero success window exists. An unknown- or
      // missing-product entry moves no bucket and no
      // denominator.
      failedSpanShareOfOwnOkWindowByProduct,
      // DETAIL-63: the per-product ok-span shares
      // of that product's own failure window
      // (okSpanShareOfOwnFailedWindowByProduct): each
      // product's DETAIL-21 ok span over that
      // product's own DETAIL-20 failed span. Null per
      // product with no usable own failure window, or
      // with successes but no usable ok timestamp
      // pair; 0 per product with no successes once a
      // nonzero failure window exists. An unknown- or
      // missing-product entry moves no bucket and no
      // denominator.
      okSpanShareOfOwnFailedWindowByProduct,
      // DETAIL-64: the global ok-span share of the
      // global failed window
      // (okSpanShareOfFailedWindow): the DETAIL-22
      // global ok span over the DETAIL-23 global
      // failed span — the cross-span re-base
      // DETAIL-57's and DETAIL-58's entry-window
      // shares imply but do not state. Null with no
      // usable failed window, or with successes but
      // no usable ok span; 0 with no successes once
      // a nonzero failed window exists. Both spans
      // are product-blind, unlike DETAIL-53/55.
      okSpanShareOfFailedWindow,
      // DETAIL-65: the global failed-span share of
      // the global ok window
      // (failedSpanShareOfOkWindow): the DETAIL-23
      // global failed span over the DETAIL-22 global
      // ok span — the mirror of DETAIL-64, the
      // cross-span re-base DETAIL-57's and
      // DETAIL-58's entry-window shares imply but do
      // not state from the other side. Null with no
      // usable ok window, or with failures but no
      // usable failed span; 0 with no failures once
      // a nonzero ok window exists. Both spans are
      // product-blind, unlike DETAIL-53/55.
      failedSpanShareOfOkWindow,
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
