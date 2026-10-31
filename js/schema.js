// Strict validation for the Meta Trio v2 assessment contract
// (MASTER_DIRECTIVE_V2.md section 9), mirroring
// native/Sources/MetaTrio/Services/ContractValidator.swift. Pure function,
// no DOM access: safe to import from browser and from node tests.
//
// Contract (response to POST { product, timestamp, image }):
// {
//   "product": "vigiles" | "ignis" | "medicus" (must match the request),
//   "timestamp": "ISO-8601 timestamp",
//   "observations": [
//     { "category": string, "description": string, "evidence": string,
//       "confidence": null | 0.0..1.0 }
//   ],
//   "assessment": {
//     "category": string,
//     "summary": string,
//     "uncertainty": [string, ...],
//     "requires_human_review": true|false
//   },
//   "processing": { "model": string, "latency_ms": null | number >= 0 }
// }
//
// Strictness notes (ambiguous points resolved to the stricter side, as in
// the native validator):
// - `timestamp` must be ISO-8601 with a `T` separator, a timezone (Z or
//   numeric offset), and a real calendar date — a plain Date.parse pass
//   is not enough ("Oct 28 2026" and impossible dates are rejected).
// - `confidence` and `latency_ms` must be PRESENT: null is accepted (the
//   model/server did not report a value), a missing key is rejected, and
//   booleans are never accepted as numbers.
// - `evidence`, `summary`, and `uncertainty` items must be strings, but
//   may be empty; `category`, `description`, `product`, and
//   `processing.model` must be non-empty strings.
// - `observations` and `uncertainty` may be empty arrays.
// - Extra fields are tolerated; nothing here fabricates a value.
// - Category membership IS enforced (2026-10-30): the assessment
//   category and every observation category must belong to the
//   selected product's own category list in js/products.js — the
//   prompts already promise this; the validator now holds the line
//   instead of accepting any non-empty string.
// - Medicus human review IS enforced (2026-10-30): a Medicus
//   assessment with requires_human_review === false is rejected.
//   The Medicus config (js/products.js) states every assessment
//   requires human verification; previously the validator only
//   checked the field was a boolean.

import { PRODUCT_BY_ID } from "./products.js";

function isPlainObject(v) {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isNonEmptyString(v) {
  return typeof v === "string" && v.trim().length > 0;
}

// ISO-8601 with T separator, optional seconds/fraction, and a timezone.
// Rejects free-form dates that Date.parse would accept, and impossible
// calendar dates (e.g. Feb 30) via a component round-trip check.
const ISO_8601_RE =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$/;

function daysInMonth(year, month) {
  // month is 1-based; Date.UTC rolls over out-of-range days, so the range
  // must be checked explicitly instead of trusting the constructor.
  if (month === 2) {
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    return leap ? 29 : 28;
  }
  return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
}

function isValidIso8601(value) {
  if (typeof value !== "string") return false;
  const m = ISO_8601_RE.exec(value);
  if (!m) return false;
  const [, year, month, day, hour, minute, second] = m;
  const y = Number(year);
  const mo = Number(month);
  const da = Number(day);
  const h = Number(hour);
  const mi = Number(minute);
  const s = second === undefined ? 0 : Number(second);
  // Range checks first: Date.UTC normalizes out-of-range components
  // (Feb 30 becomes Mar 2), so it cannot catch impossible dates alone.
  if (mo < 1 || mo > 12) return false;
  if (da < 1 || da > daysInMonth(y, mo)) return false;
  if (h > 23 || mi > 59 || s > 59) return false;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return false;
  // Build the expected UTC instant from the components minus the offset
  // and compare epoch milliseconds, so a rolled-over parse is caught.
  const offsetPart = m[8];
  let offsetMinutes = 0;
  if (offsetPart !== "Z") {
    const sign = offsetPart[0] === "-" ? -1 : 1;
    const digits = offsetPart.slice(1).replace(":", "");
    const offH = Number(digits.slice(0, 2));
    const offM = Number(digits.slice(2, 4));
    if (offH > 23 || offM > 59) return false;
    offsetMinutes = sign * (offH * 60 + offM);
  }
  const frac = m[7] ? Number(`0${m[7]}`) : 0;
  const expected = Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    second === undefined ? 0 : Number(second),
    Math.round(frac * 1000),
  ) - offsetMinutes * 60 * 1000;
  return d.getTime() === expected;
}

// A nullable number field: the key must exist; null is accepted, a finite
// number in range is accepted, anything else (missing, string, boolean,
// NaN, out of range, negative where disallowed) is an error.
function checkNullableNumber(obj, key, field, errors, { min = null, max = null } = {}) {
  if (!Object.hasOwn(obj, key)) {
    errors.push(`${field}: missing (must be present, null when unreported)`);
    return;
  }
  const v = obj[key];
  if (v === null) return;
  if (typeof v !== "number" || Number.isNaN(v)) {
    errors.push(`${field}: must be null or a number`);
    return;
  }
  if (min !== null && v < min) {
    errors.push(`${field}: must not be below ${min}`);
    return;
  }
  if (max !== null && v > max) {
    errors.push(`${field}: out of range ${min}..${max}`);
  }
}

export function validateAssessment(value, expectedProduct) {
  const errors = [];

  if (!isPlainObject(value)) {
    return { ok: false, errors: ["response is not a JSON object"] };
  }

  // The product whose rules govern this assessment: the requested
  // product when it is a known one, else the response's own product
  // when that is known. The permitted categories come from
  // js/products.js — the same source the prompts are built from,
  // never a second hand-typed list here.
  const productId =
    typeof expectedProduct === "string" && Object.hasOwn(PRODUCT_BY_ID, expectedProduct)
      ? expectedProduct
      : typeof value.product === "string" && Object.hasOwn(PRODUCT_BY_ID, value.product)
        ? value.product
        : null;
  const permittedCategories = productId ? new Set(PRODUCT_BY_ID[productId].categories) : null;

  if (typeof expectedProduct !== "string" || expectedProduct.length === 0) {
    errors.push("expected product: missing or invalid (validator requires the requested product)");
  } else if (!isNonEmptyString(value.product)) {
    errors.push("product: missing or not a non-empty string");
  } else if (value.product !== expectedProduct) {
    errors.push(`product: expected "${expectedProduct}", got "${value.product}"`);
  }

  if (!isNonEmptyString(value.timestamp)) {
    errors.push("timestamp: missing or not a string");
  } else if (!isValidIso8601(value.timestamp)) {
    errors.push("timestamp: not a parseable ISO-8601 date");
  }

  if (!Array.isArray(value.observations)) {
    errors.push("observations: missing or not an array");
  } else {
    value.observations.forEach((obs, i) => {
      const prefix = `observations[${i}]`;
      if (!isPlainObject(obs)) {
        errors.push(`${prefix}: not an object`);
        return;
      }
      if (!isNonEmptyString(obs.category)) {
        errors.push(`${prefix}.category: missing or not a non-empty string`);
      } else if (permittedCategories && !permittedCategories.has(obs.category)) {
        errors.push(
          `${prefix}.category: "${obs.category}" is not a permitted category for product "${productId}"`,
        );
      }
      if (!isNonEmptyString(obs.description)) {
        errors.push(`${prefix}.description: missing or not a non-empty string`);
      }
      if (typeof obs.evidence !== "string") {
        errors.push(`${prefix}.evidence: missing or not a string`);
      }
      checkNullableNumber(obs, "confidence", `${prefix}.confidence`, errors, { min: 0, max: 1 });
    });
  }

  if (!isPlainObject(value.assessment)) {
    errors.push("assessment: missing or not an object");
  } else {
    const a = value.assessment;
    if (!isNonEmptyString(a.category)) {
      errors.push("assessment.category: missing or not a non-empty string");
    } else if (permittedCategories && !permittedCategories.has(a.category)) {
      errors.push(
        `assessment.category: "${a.category}" is not a permitted category for product "${productId}"`,
      );
    }
    if (typeof a.summary !== "string") {
      errors.push("assessment.summary: missing or not a string");
    }
    if (!Array.isArray(a.uncertainty)) {
      errors.push("assessment.uncertainty: missing or not an array");
    } else {
      a.uncertainty.forEach((item, i) => {
        if (typeof item !== "string") {
          errors.push(`assessment.uncertainty[${i}]: not a string`);
        }
      });
    }
    if (typeof a.requires_human_review !== "boolean") {
      errors.push("assessment.requires_human_review: missing or not a boolean");
    } else if (productId === "medicus" && a.requires_human_review !== true) {
      errors.push(
        "assessment.requires_human_review: must be true for medicus — every Medicus assessment requires human verification",
      );
    }
  }

  if (!isPlainObject(value.processing)) {
    errors.push("processing: missing or not an object");
  } else {
    const p = value.processing;
    if (!isNonEmptyString(p.model)) {
      errors.push("processing.model: missing or not a non-empty string");
    }
    checkNullableNumber(p, "latency_ms", "processing.latency_ms", errors, { min: 0 });
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }
  return { ok: true, value, errors: [] };
}
