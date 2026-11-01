#!/usr/bin/env python3
"""worlds/custos/runtime/patrol.py: the Custos patrol loop.

The night watch for machines. One patrol:

  1. Fetches the CISA known-exploited-vulnerabilities (KEV) feed and
     matches its entries against the installation's configured
     software inventory. A match is recorded as
     "known-exploited vulnerability present" (red). Presence means the
     inventory names the product; it is never a claim that an exploit
     was observed.
  1b. Polls Certificate Transparency logs (crt.sh) for the
     configured watched domains. A newly issued cert for a watched
     domain becomes a "certificate issued" record (yellow). Cert ids
     already in the seen-state were recorded on an earlier patrol
     and are never re-recorded; ct_since bounds a first patrol so
     a domain with years of history does not flood the record.
  2. For every watched host: probes the service port (liveness),
     reads the TLS certificate the host actually presents (expiry),
     and probes a small set of sensitive ports the installation did
     not declare expected (anomalous exposure).
  3. Classifies every observation into the pack's six categories:
     baseline normal, certificate expiring, certificate expired,
     known-exploited vulnerability present, service down,
     anomalous exposure.
  4. Appends one record per observation to the patrol record (JSONL),
     plus one patrol-summary record per patrol.

Tiers (the Imperium rule, pointed at machines): a WARNING observation
is yellow — record + flag only, ZERO escalation calls. A CRITICAL
observation is red — it runs the escalation chain, and in stage 1
that chain ends at a labelled SIMULATED endpoint only: the escalation
is recorded with endpoint "SIMULATED", and no real responder, vendor,
or service is ever contacted.

The loop only observes. It never patches, restarts, reconfigures, or
scans a host it was not given. It never invents an observation: a
signal that cannot be fetched or probed is recorded as an error in
the patrol summary, never as data.

Pure classification core plus a thin CLI, no model calls. The signal
functions (feed fetch, certificate probe, port probe) are injectable
so the pinning tests run on recorded signal shapes with no network.

CLI:
    patrol.py run --config hosts.json --records patrol.jsonl \
        [--state patrol-state.json] [--kev-file kev.json]

Config (JSON):
    {
      "hosts": [{"host": "example.org", "port": 443,
                 "expected_ports": [443]}],
      "inventory": ["openssl", "openssh"],
      "cert_warn_days": 21,
      "kev_url": "https://www.cisa.gov/.../known_exploited_vulnerabilities.json",
      "sensitive_ports": [22, 3306, 5432, 6379, 9200, 27017]
    }
"""

import argparse
import json
import os
import socket
import ssl
import sys
import urllib.request
from datetime import datetime, timezone

DEFAULT_KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/"
    "known_exploited_vulnerabilities.json"
)
DEFAULT_CT_URL_TEMPLATE = "https://crt.sh/?q=%25.{domain}&output=json"
DEFAULT_CERT_WARN_DAYS = 21
DEFAULT_SENSITIVE_PORTS = [22, 3306, 5432, 6379, 9200, 27017]
PROBE_TIMEOUT = 5.0
KEV_TIMEOUT = 30.0
CT_TIMEOUT = 30.0

CATEGORIES = (
    "baseline normal",
    "certificate expiring",
    "certificate expired",
    "known-exploited vulnerability present",
    "service down",
    "anomalous exposure",
    "certificate issued",
)

# Category -> tier. Yellow stops at record + flag (zero escalation
# calls); red runs the escalation chain (SIMULATED endpoint only in
# stage 1); baseline normal never escalates.
TIER_BY_CATEGORY = {
    "baseline normal": "none",
    "certificate expiring": "yellow",
    "anomalous exposure": "yellow",
    "certificate issued": "yellow",
    "certificate expired": "red",
    "known-exploited vulnerability present": "red",
    "service down": "red",
}

ESCALATION_ENDPOINT = "SIMULATED"
ESCALATION_STEPS = ("record", "notify", "page", "ticket")


def tier_for(category):
    return TIER_BY_CATEGORY[category]


def classify_certificate(days_left, warn_days):
    """Certificate expiry state from whole days remaining."""
    if days_left < 0:
        return "certificate expired"
    if days_left <= warn_days:
        return "certificate expiring"
    return "baseline normal"


def _norm(text):
    return " ".join(str(text).lower().split())


def match_kev(entries, inventory):
    """KEV entries whose vendor+product the inventory names.

    Matching is a normalized substring test of each inventory string
    against the entry's "vendorProject product" text: predictable,
    and the record keeps the entry text it matched, so a human can
    check every match by eye.
    """
    wanted = [_norm(item) for item in inventory if _norm(item)]
    matched = []
    for entry in entries:
        text = _norm("%s %s" % (entry.get("vendorProject", ""),
                                 entry.get("product", "")))
        for item in wanted:
            if item and item in text:
                matched.append((entry, item))
                break
    return matched


def classify_exposure(open_ports, expected_ports, service_port):
    """Sensitive ports that answered without being declared expected."""
    expected = set(expected_ports or ()) | {service_port}
    return [p for p in open_ports if p not in expected]


def make_record(now, source, host, category, detail):
    return {
        "record_type": "observation",
        "ts": now,
        "source": source,
        "host": host,
        "category": category,
        "tier": tier_for(category),
        "detail": detail,
    }


def escalate(record, now):
    """The escalation chain for a red record.

    Stage 1: the chain is real bookkeeping ending at a labelled
    SIMULATED endpoint. Every step is recorded; nothing external is
    contacted. The endpoint label travels with the record so no one
    can mistake it for a real page.
    """
    return {
        "record_type": "escalation",
        "ts": now,
        "endpoint": ESCALATION_ENDPOINT,
        "steps": list(ESCALATION_STEPS),
        "for_category": record["category"],
        "host": record["host"],
    }


# ---------------------------------------------------------------------
# Real signals (injectable; the CLI wires these, tests wire fakes).

def fetch_kev(url):
    req = urllib.request.Request(url, headers={"User-Agent": "meta-custos/0.1"})
    with urllib.request.urlopen(req, timeout=KEV_TIMEOUT) as resp:
        data = json.load(resp)
    return data.get("vulnerabilities", [])


def fetch_ct(domain, url_template=DEFAULT_CT_URL_TEMPLATE):
    """Certificate Transparency entries for a domain (crt.sh).

    Returns the raw entry list. Matching and filtering live in the
    patrol core, so the record keeps exactly what the log returned.
    """
    url = url_template.format(domain=domain)
    req = urllib.request.Request(url, headers={"User-Agent": "meta-custos/0.1"})
    with urllib.request.urlopen(req, timeout=CT_TIMEOUT) as resp:
        return json.load(resp)


def probe_port(host, port, timeout=PROBE_TIMEOUT):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def parse_cert_expiry(not_after):
    """UTC expiry datetime for a getpeercert notAfter string, or None.

    getpeercert dates are space-padded for single-digit days
    ("Nov  1 ..."), which strptime accepts. Anything unparseable is
    None, never an exception: an unparseable date is a failed probe,
    recorded as an error, never a crash of the patrol.
    """
    try:
        expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
    except (ValueError, TypeError):
        return None
    return expires.replace(tzinfo=timezone.utc)


def probe_cert(host, port, timeout=PROBE_TIMEOUT):
    """Days left on the certificate the host presents, or None."""
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
    except (OSError, ssl.SSLError):
        return None
    expires = parse_cert_expiry(cert.get("notAfter"))
    if expires is None:
        return None
    delta = expires - datetime.now(timezone.utc)
    return int(delta.total_seconds() // 86400)


# ---------------------------------------------------------------------
# The patrol.

def run_patrol(config, now, fetch_kev_fn, probe_cert_fn, probe_port_fn,
               seen_cve=None, fetch_ct_fn=None, seen_ct=None):
    """One patrol. Returns (records, seen_cve, seen_ct).

    Every observation is classified and recorded. Yellow records are
    never escalated (zero escalation calls — the escalation list is
    built only from red records, here, in one place). A signal that
    fails is noted in the summary, never turned into data.
    """
    records = []
    seen = set(seen_cve or ())
    seen_ids = set(seen_ct or ())
    warn_days = int(config.get("cert_warn_days", DEFAULT_CERT_WARN_DAYS))
    sensitive = list(config.get("sensitive_ports", DEFAULT_SENSITIVE_PORTS))
    errors = []

    # 1. Known-exploited vulnerabilities vs the configured inventory.
    kev_seen_count = 0
    entries = []
    try:
        entries = fetch_kev_fn(config.get("kev_url", DEFAULT_KEV_URL))
    except Exception as exc:  # feed down: noted, never invented
        errors.append("kev fetch failed: %s" % exc)
    kev_seen_count = len(entries)
    for entry, item in match_kev(entries, config.get("inventory", [])):
        cve = entry.get("cveID", "")
        if cve in seen:
            continue
        seen.add(cve)
        records.append(make_record(now, "kev", None,
                                   "known-exploited vulnerability present",
                                   {"cve": cve,
                                    "matched_inventory": item,
                                    "vendor_product": "%s %s" % (
                                        entry.get("vendorProject", ""),
                                        entry.get("product", "")),
                                    "date_added": entry.get("dateAdded", "")}))

    # 1b. Certificate Transparency: newly issued certs for watched
    # domains. A cert id already in the seen-state was recorded on
    # an earlier patrol and is never re-recorded; ct_since (ISO
    # date) bounds the first patrol so a domain with years of
    # history does not flood the record.
    ct_seen_count = 0
    ct_since = config.get("ct_since", "")
    ct_fetch = fetch_ct_fn or fetch_ct
    for domain in config.get("ct_domains", []):
        try:
            entries = ct_fetch(domain, config.get(
                "ct_url_template", DEFAULT_CT_URL_TEMPLATE))
        except Exception as exc:  # log down: noted, never invented
            errors.append("ct fetch failed for %s: %s" % (domain, exc))
            continue
        ct_seen_count += len(entries)
        for entry in entries:
            ct_id = entry.get("id")
            if ct_id in seen_ids:
                continue
            if ct_since and entry.get("not_before", "")[:10] < ct_since:
                continue
            seen_ids.add(ct_id)
            records.append(make_record(now, "ct", domain,
                                       "certificate issued",
                                       {"ct_id": ct_id,
                                        "common_name": entry.get(
                                            "common_name", ""),
                                        "issuer_name": entry.get(
                                            "issuer_name", ""),
                                        "not_before": entry.get(
                                            "not_before", ""),
                                        "not_after": entry.get(
                                            "not_after", "")}))

    # 2. Per-host checks.
    for host_cfg in config.get("hosts", []):
        host = host_cfg["host"]
        port = int(host_cfg.get("port", 443))
        if not probe_port_fn(host, port):
            records.append(make_record(now, "service", host, "service down",
                                       {"port": port}))
            continue
        records.append(make_record(now, "service", host, "baseline normal",
                                   {"port": port, "check": "liveness"}))
        days = probe_cert_fn(host, port)
        if days is None:
            errors.append("cert probe failed for %s:%d" % (host, port))
        else:
            records.append(make_record(
                now, "cert", host, classify_certificate(days, warn_days),
                {"port": port, "days_left": days, "warn_days": warn_days}))
        open_sensitive = [p for p in sensitive
                          if p != port and probe_port_fn(host, p)]
        for p in classify_exposure(open_sensitive,
                                    host_cfg.get("expected_ports"), port):
            records.append(make_record(now, "exposure", host,
                                       "anomalous exposure",
                                       {"port": p}))

    # 3. Escalations: red only, built in exactly one place.
    escalations = [escalate(r, now) for r in records
                   if r["tier"] == "red"]
    records.extend(escalations)

    counts = {c: 0 for c in CATEGORIES}
    for r in records:
        if r["record_type"] == "observation":
            counts[r["category"]] += 1
    records.append({
        "record_type": "patrol-summary",
        "ts": now,
        "hosts_checked": len(config.get("hosts", [])),
        "kev_entries_seen": kev_seen_count,
        "ct_entries_seen": ct_seen_count,
        "observations": counts,
        "escalations": len(escalations),
        "errors": errors,
    })
    return records, seen, seen_ids


# ---------------------------------------------------------------------
# CLI.

def load_state(path):
    if path and os.path.isfile(path):
        with open(path) as f:
            data = json.load(f)
        return (set(data.get("seen_cve", [])),
                set(data.get("seen_ct", [])))
    return set(), set()


def save_state(path, seen_cve, seen_ct):
    if path:
        with open(path, "w") as f:
            json.dump({"seen_cve": sorted(seen_cve),
                       "seen_ct": sorted(seen_ct)}, f, indent=1)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="patrol.py")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run one patrol")
    run.add_argument("--config", required=True)
    run.add_argument("--records", help="JSONL file to append to "
                                       "(default: print to stdout)")
    run.add_argument("--state", help="seen-state JSON file for KEV dedupe")
    run.add_argument("--kev-file", help="read the KEV feed from a local "
                                        "file instead of fetching it")
    run.add_argument("--ct-file", help="read the CT entries from a local "
                                       "file instead of fetching them")
    args = parser.parse_args(argv)

    with open(args.config) as f:
        config = json.load(f)

    if args.kev_file:
        with open(args.kev_file) as f:
            feed = json.load(f)
        fetch_fn = lambda _url: feed.get("vulnerabilities", [])
    else:
        fetch_fn = fetch_kev

    if args.ct_file:
        with open(args.ct_file) as f:
            ct_feed = json.load(f)
        fetch_ct_fn = lambda _domain, _template: ct_feed
    else:
        fetch_ct_fn = None

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen, seen_ct = load_state(args.state)
    records, seen, seen_ct = run_patrol(config, now, fetch_fn, probe_cert,
                                        probe_port, seen, fetch_ct_fn,
                                        seen_ct)
    save_state(args.state, seen, seen_ct)

    lines = "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
    if args.records:
        with open(args.records, "a") as f:
            f.write(lines)
    else:
        sys.stdout.write(lines)
    summary = records[-1]
    print("patrol complete: %d hosts, %d escalations, %d errors"
          % (summary["hosts_checked"], summary["escalations"],
             len(summary["errors"])), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
