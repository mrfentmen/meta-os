// Meta OS agent layer — the two-reading ruling (R11-286).
//
// When two sources disagree, the honest ruling is "inconclusive". A coin flip is not a tie
// breaker, it is a fabricated third source. This judge refuses rather than picks: the caller
// gets the readings, the gap, and a reason, and no field that looks like a decision.
export const RULING_INCONCLUSIVE = "inconclusive";
export const RULING_AGREE = "agree";

export class JudgeError extends Error {}

function numeric(v) {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

// readings: [{ source, value }]. tolerance is in the same units as value.
export function rule(readings, { tolerance = 0.2 } = {}) {
  if (!Array.isArray(readings) || readings.length < 2) {
    return {
      ruling: RULING_INCONCLUSIVE,
      reason: "fewer-than-two-readings",
      detail: "one reading cannot contradict or confirm anything",
      readings: readings || [],
    };
  }
  if (!(tolerance >= 0) || !Number.isFinite(tolerance)) throw new JudgeError("judge: tolerance must be a non-negative number");

  const nums = readings.map((r) => ({ ...r, n: numeric(r.value) }));
  const unreadable = nums.filter((r) => r.n == null);
  if (unreadable.length) {
    return {
      ruling: RULING_INCONCLUSIVE,
      reason: "unreadable-reading",
      detail: "a reading with no number cannot be compared: " + unreadable.map((r) => r.source).join(", "),
      readings: nums,
    };
  }

  const values = nums.map((r) => r.n);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const gap = max - min;
  if (gap > tolerance) {
    return {
      ruling: RULING_INCONCLUSIVE,
      reason: "contradictory-readings",
      detail: "readings differ by " + Number(gap.toFixed(6)) + ", beyond tolerance " + tolerance,
      gap: Number(gap.toFixed(6)),
      tolerance,
      readings: nums,
    };
  }
  return {
    ruling: RULING_AGREE,
    reason: "within-tolerance",
    detail: "readings differ by " + Number(gap.toFixed(6)) + ", within tolerance " + tolerance,
    gap: Number(gap.toFixed(6)),
    tolerance,
    readings: nums,
  };
}
