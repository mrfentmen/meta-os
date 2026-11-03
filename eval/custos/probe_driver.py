#!/usr/bin/env python3
"""eval/custos/probe_driver.py: injected-probe driver for the Custos eval.

Runs the REAL patrol classification core (os/worlds/custos/runtime/patrol.py
run_patrol) with every signal injected from a spec file, so the eval never
touches the network or a live host. This is exactly the method the
pinning tests in tests/custos/ use (fake feeds, fake probes); the driver
just lets the Node harness drive it per scenario.

Usage: python3 eval/custos/probe_driver.py <spec.json>
Prints one JSON object to stdout: {"runs": [[record, ...], ...]}.

Spec shape:
  {
    "config": { ... patrol config ... },
    "kev_feed": [ ... ] | null,        # KEV entries, or null for no fetch
    "ct_feed": [ ... ] | null,         # CT entries returned for any domain
    "dns_feed": { "domain": snapshot } | null,
    "runs": 1,                          # sequential run_patrol calls sharing state
    "probes": {
      "cert_days": { "host": days | null },
      "ports": { "host:port": true|false },
      "headers": { "host": [served header names] },
      "tls": { "host": {"version": "...", "cipher": "..."} },
      "subdomains": { "subdomain": ["address", ...] }
    }
  }
A missing probe answer is a signal failure by design (None / False /
raise), which the patrol records as a summary error, never as data.
The fixed "now" (2026-11-01) keeps runs deterministic; KEV ageing
against the real clock is pinned by the CLI scenarios instead, where
the flag, not an exact day count, is asserted.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "os", "worlds", "custos", "runtime"))

import patrol  # noqa: E402

NOW = "2026-11-01T03:00:00Z"


def main(argv):
    with open(argv[1]) as f:
        spec = json.load(f)
    config = spec.get("config", {})
    probes = spec.get("probes", {})
    cert_days = probes.get("cert_days", {})
    ports = probes.get("ports", {})
    headers = probes.get("headers", {})
    tls = probes.get("tls", {})
    subdomains = probes.get("subdomains", {})
    kev_feed = spec.get("kev_feed")
    ct_feed = spec.get("ct_feed")
    dns_feed = spec.get("dns_feed")

    def fetch_kev(_url):
        return list(kev_feed or [])

    def fetch_ct(_domain, _template):
        return list(ct_feed or [])

    def fetch_dns(domain):
        if dns_feed is None or domain not in dns_feed:
            raise ValueError("no dns fixture for %s" % domain)
        return dns_feed[domain]

    def probe_cert(host, _port):
        return cert_days.get(host)

    def probe_port(host, port):
        return bool(ports.get("%s:%d" % (host, port), False))

    def fetch_headers(host, _port):
        return {h: "present" for h in headers.get(host, [])}

    def probe_tls(host, _port):
        return tls.get(host)

    def resolve_subdomain(sub):
        if sub not in subdomains:
            raise ValueError("no subdomain fixture for %s" % sub)
        return list(subdomains[sub])

    seen_cve = set()
    seen_ct = set()
    seen_dns = {}
    seen_dedup = {}
    runs = []
    for _ in range(int(spec.get("runs", 1))):
        records, seen_cve, seen_ct = patrol.run_patrol(
            config, NOW, fetch_kev, probe_cert, probe_port,
            seen_cve=seen_cve, fetch_ct_fn=fetch_ct, seen_ct=seen_ct,
            fetch_headers_fn=fetch_headers, fetch_dns_fn=fetch_dns,
            seen_dns=seen_dns, resolve_subdomain_fn=resolve_subdomain,
            seen_dedup=seen_dedup, probe_tls_fn=probe_tls)
        runs.append(records)
    print(json.dumps({"runs": runs}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
