// Meta Aegis — direct OSV API client (R12-001, Pax's written exception).
//
// The spec normally forbids calling api.osv.dev directly: Aegis contacts OSV only through the
// boss's own MCP server. Pax's round-12 ruling grants a narrow exception — this sweep, this
// repo's manifests only, with the route named in the record. This file is that route and
// nothing else: no fallback, no scraping, no second source.
//
// The interface is deliberately the same callTool shape the MCP client exposes, so the sweep
// logic is unchanged. Responses are rendered in the same text shape osv-mcp produces, because
// the parser in sweep.mjs was written against that shape and a second parser would be a second
// place to be wrong.
const API = "https://api.osv.dev/v1";

export class OsvDirectError extends Error {}

export function openOsvDirect({ fetchImpl = fetch, timeoutMs = 30000 } = {}) {
  const call = async (url, init) => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetchImpl(url, { ...init, signal: ctrl.signal });
      if (!res.ok) throw new OsvDirectError("HTTP " + res.status + " from " + url);
      return await res.json();
    } finally { clearTimeout(timer); }
  };

  return {
    async callTool(name, args = {}) {
      if (name === "scan_packages") {
        const packages = args.packages || [];
        const doc = await call(API + "/querybatch", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            queries: packages.map((p) => ({ package: { name: p.name, ecosystem: p.ecosystem }, version: p.version })),
          }),
        });
        const lines = [];
        let total = 0;
        (doc.results || []).forEach((r, i) => {
          const vulns = r.vulns || [];
          if (!vulns.length) return;
          const p = packages[i];
          total += vulns.length;
          lines.push(p.ecosystem + "/" + p.name + "@" + p.version + ": " + vulns.length + " record(s)");
          for (const v of vulns) lines.push(v.id + ": query osv for detail");
        });
        return {
          text: total
            ? lines.join("\n")
            : "No known vulnerabilities found across " + packages.length + " package(s).",
        };
      }
      if (name === "get_vulnerability") {
        const v = await call(API + "/vulns/" + encodeURIComponent(args.id));
        return {
          text: [
            v.id + ": " + String(v.summary || "No summary").replace(/\n/g, " "),
            "Aliases: " + ((v.aliases || []).join(", ") || "(none)"),
            "Details: " + String(v.details || "No details").replace(/\s+/g, " "),
          ].join("\n"),
        };
      }
      throw new OsvDirectError("osv-direct: unknown tool " + name);
    },
    close() {},
  };
}
