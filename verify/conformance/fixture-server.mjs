// Fixture /api/assess server for the conformance suite.
// NOT a model. NOT an assessment source. It returns one deterministic,
// contract-valid response so the shipped client and validator can be
// exercised end to end with zero network access, zero API key, and zero
// model calls (Spark stays OFF per Del's ruling).
//
// The response says what it is: processing.model names the fixture,
// observations are empty, the summary states no model was consulted, and
// latency_ms is null (the fixture reports no latency). Nothing here may
// be presented as a real assessment.
//
// Behavior (mirrors the contract's error shape, js/client.js):
// - POST /api/assess with {product, timestamp, image}
//     valid   -> 200 + v2 contract response (fixture-labeled)
//     invalid -> 200 + {"error": "..."} (the contract's error shape)
// - Unparseable JSON body -> 400 + {"error": "..."}
// - Anything else -> 404 + {"error": "..."}

import http from "node:http";

const PRODUCTS = new Set(["vigiles", "ignis", "sanitas"]);

export function fixtureResponse(product, timestamp) {
  return {
    product,
    timestamp,
    observations: [],
    assessment: {
      category: "indeterminate",
      summary:
        "Fixture server response: no model was consulted. This only proves the transport and the contract shape.",
      uncertainty: ["Fixture response - not a real assessment."],
      requires_human_review: true,
    },
    processing: { model: "fixture-server (not a model)", latency_ms: null },
  };
}

export function handleAssess(body) {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { error: "request body must be a JSON object" };
  }
  if (!PRODUCTS.has(body.product)) {
    return { error: `unknown product: ${String(body.product)}` };
  }
  if (typeof body.timestamp !== "string" || body.timestamp.length === 0) {
    return { error: "timestamp is required (ISO-8601 string)" };
  }
  if (typeof body.image !== "string" || body.image.length === 0) {
    return { error: "image is required (JPEG data URL string)" };
  }
  return fixtureResponse(body.product, body.timestamp);
}

export function createFixtureServer() {
  return http.createServer((req, res) => {
    const send = (status, obj) => {
      res.writeHead(status, { "Content-Type": "application/json" });
      res.end(JSON.stringify(obj));
    };
    if (req.method !== "POST" || req.url !== "/api/assess") {
      send(404, { error: "not found: POST /api/assess is the only route" });
      return;
    }
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
    });
    req.on("end", () => {
      let body;
      try {
        body = JSON.parse(raw);
      } catch {
        send(400, { error: "request body was not valid JSON" });
        return;
      }
      send(200, handleAssess(body));
    });
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const port = Number(process.env.PORT || 18080);
  createFixtureServer().listen(port, () => {
    console.log(`fixture-server listening on http://localhost:${port}/api/assess`);
  });
}
