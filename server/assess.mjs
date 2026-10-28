// Core of POST /api/assess (Rowan's lane): strict request validation,
// one model-adapter call, and strict validation of whatever comes back
// against the frozen v2 contract (js/schema.js) before it is sent.
//
// Request (from js/client.js): JSON object
//   { product: "vigiles"|"ignis"|"sanitas",
//     timestamp: ISO-8601 string,
//     image: "data:image/jpeg;base64,..." }
//
// Success: HTTP 200 with the v2 assessment object, unchanged from the
// model after validation. Failure: HTTP status + {"error": "..."} — the
// contract's error shape, which both clients already surface honestly.
// This module never invents an assessment: no model, no assessment.

import { validateAssessment } from "../js/schema.js";
import { isProductId } from "../js/products.js";
import { assessWithModel, ModelError } from "./model.mjs";

export const MAX_IMAGE_BYTES = 8 * 1024 * 1024; // decoded JPEG cap

const ISO_8601_RE =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$/;

function daysInMonth(year, month) {
  if (month === 2) {
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    return leap ? 29 : 28;
  }
  return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
}

// Same strictness bar as js/schema.js: real calendar dates only.
export function isValidIso8601(value) {
  if (typeof value !== "string") return false;
  const m = ISO_8601_RE.exec(value);
  if (!m) return false;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const da = Number(m[3]);
  const h = Number(m[4]);
  const mi = Number(m[5]);
  const s = m[6] === undefined ? 0 : Number(m[6]);
  if (mo < 1 || mo > 12) return false;
  if (da < 1 || da > daysInMonth(y, mo)) return false;
  if (h > 23 || mi > 59 || s > 59) return false;
  return !Number.isNaN(new Date(value).getTime());
}

const JPEG_DATA_URL_RE = /^data:image\/jpeg;base64,([A-Za-z0-9+/=\s]+)$/;

// Returns { bytes, mediaType } or { error }.
export function parseImageDataUrl(image) {
  if (typeof image !== "string" || image.length === 0) {
    return { error: "image: missing or not a string (expected a JPEG data URL)" };
  }
  const m = JPEG_DATA_URL_RE.exec(image);
  if (!m) {
    return { error: "image: must be a data:image/jpeg;base64 URL, as both clients send" };
  }
  const bytes = Buffer.from(m[1], "base64");
  if (bytes.length === 0) {
    return { error: "image: data URL decodes to zero bytes" };
  }
  if (bytes.length > MAX_IMAGE_BYTES) {
    return { error: `image: ${bytes.length} bytes exceeds the ${MAX_IMAGE_BYTES}-byte cap` };
  }
  if (!(bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff)) {
    return { error: "image: decoded bytes do not start with the JPEG magic bytes" };
  }
  return { bytes, mediaType: "image/jpeg" };
}

// Returns { ok: true, value } or { ok: false, errors }.
export function validateAssessRequest(payload) {
  const errors = [];
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    return { ok: false, errors: ["request body is not a JSON object"] };
  }
  if (!isProductId(payload.product)) {
    errors.push('product: must be one of "vigiles", "ignis", "sanitas"');
  }
  if (!isValidIso8601(payload.timestamp)) {
    errors.push("timestamp: must be a valid ISO-8601 timestamp with timezone");
  }
  const image = parseImageDataUrl(payload.image);
  if (image.error) errors.push(image.error);
  if (errors.length > 0) return { ok: false, errors };
  return {
    ok: true,
    value: {
      product: payload.product,
      timestamp: payload.timestamp,
      imageBytes: image.bytes,
      mediaType: image.mediaType,
    },
  };
}

// deps.assessModel is injectable for tests; production uses the real
// adapter from model.mjs. Returns { status, body } ready to serialize.
export async function handleAssess(payload, deps = {}) {
  const assessModel = deps.assessModel ?? assessWithModel;
  const env = deps.env ?? process.env;

  const req = validateAssessRequest(payload);
  if (!req.ok) {
    return { status: 400, body: { error: req.errors.join("; ") } };
  }

  let output;
  try {
    output = await assessModel(req.value, env);
  } catch (err) {
    if (err instanceof ModelError) {
      const status = err.code === "model_call_failed" ? 502 : 503;
      return { status, body: { error: err.message } };
    }
    return {
      status: 502,
      body: { error: `Model call failed: ${err && err.message ? err.message : String(err)}` },
    };
  }

  const check = validateAssessment(output, req.value.product);
  if (!check.ok) {
    return {
      status: 502,
      body: { error: `Model response failed contract validation: ${check.errors.join("; ")}` },
    };
  }
  return { status: 200, body: check.value };
}
