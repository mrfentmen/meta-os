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
  1c. Snapshots DNS records (A/AAAA/MX/TXT) for the watched
     domains. A first sighting only establishes the baseline and
     records nothing; any later change becomes a "dns drift"
     record (yellow) carrying the diff: what was added, what was
     removed, per record type.
  2. For every watched host: probes the service port (liveness),
     reads the TLS certificate the host actually presents (expiry),
     and probes a small set of sensitive ports the installation did
     not declare expected (anomalous exposure).
  2b. For every live host: fetches the security headers the host
     actually serves (HSTS, CSP, X-Frame-Options, X-Content-Type-
     Options, Referrer-Policy) and scores them. A host missing any
     of them becomes a "security headers missing" record (yellow)
     carrying the missing list; a host serving all five is
     baseline normal. This is an audit only: the patrol never
     auto-fixes a header, never rewrites a config, never touches
     the watched host beyond reading its response headers.
  3. Classifies every observation into the pack's categories:
     baseline normal, certificate expiring, certificate expired,
     known-exploited vulnerability present, service down,
     anomalous exposure, certificate issued, security headers
     missing, dns drift.
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
functions (feed fetch, certificate probe, port probe, headers
fetch) are injectable so the pinning tests run on recorded signal
shapes with no network.

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
      "sensitive_ports": [22, 3306, 5432, 6379, 9200, 27017],
      "ct_domains": ["example.org"],
      "dns_domains": ["example.org"]
    }

dns_domains defaults to ct_domains when absent: the watched-domain
list is the DNS watch list unless the config says otherwise. A
snapshot is {"A": [...], "AAAA": [...], "MX": [...], "TXT": [...]}.
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
HEADER_TIMEOUT = 10.0
KEV_TIMEOUT = 30.0
CT_TIMEOUT = 30.0
DNS_TIMEOUT = 10.0
DNS_TYPES = ("A", "AAAA", "MX", "TXT")
SECURITY_HEADERS = (
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
)

CATEGORIES = (
    "baseline normal",
    "certificate expiring",
    "certificate expired",
    "known-exploited vulnerability present",
    "service down",
    "anomalous exposure",
    "certificate issued",
    "security headers missing",
    "dns drift",
)

# Category -> tier. Yellow stops at record + flag (zero escalation
# calls); red runs the escalation chain (SIMULATED endpoint only in
# stage 1); baseline normal never escalates.
TIER_BY_CATEGORY = {
    "baseline normal": "none",
    "certificate expiring": "yellow",
    "anomalous exposure": "yellow",
    "certificate issued": "yellow",
    "security headers missing": "yellow",
    "dns drift": "yellow",
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


def header_audit(headers):
    """(present, missing) security headers, in SECURITY_HEADERS order.

    Header names are matched case-insensitively; values are never
    judged here — presence is the audit, the value is the operator's
    call. A header present with an empty value counts as present:
    the patrol records what the host serves, it does not grade
    policy strength.
    """
    served = {str(k).strip().lower() for k in (headers or {})}
    present = [h for h in SECURITY_HEADERS if h in served]
    missing = [h for h in SECURITY_HEADERS if h not in served]
    return present, missing


def classify_headers(missing):
    """Header-audit category: clean is baseline, any gap is yellow."""
    if missing:
        return "security headers missing"
    return "baseline normal"


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


def normalize_snapshot(raw):
    """A DNS snapshot in canonical form: sorted, deduped values.

    TXT values lose one pair of surrounding double quotes (the dig
    +short form); MX values lose a trailing root dot. Anything
    outside the four watched types is dropped, so a resolver that
    returns extra types cannot smuggle noise into the diff.
    """
    snapshot = {}
    for rtype in DNS_TYPES:
        values = []
        for value in (raw or {}).get(rtype, []) or []:
            text = " ".join(str(value).split())
            if rtype == "TXT" and len(text) >= 2 and text.startswith('"') \
                    and text.endswith('"'):
                text = text[1:-1]
            if rtype == "MX":
                text = text.rstrip(".")
            if text:
                values.append(text)
        snapshot[rtype] = sorted(set(values))
    return snapshot


def diff_snapshots(old, new):
    """(added, removed) per record type, changed types only.

    Both sides are normalized first, so quote style, trailing dots,
    order, and duplicates never read as drift.
    """
    old = normalize_snapshot(old)
    new = normalize_snapshot(new)
    added, removed = {}, {}
    for rtype in DNS_TYPES:
        add = sorted(set(new[rtype]) - set(old[rtype]))
        rem = sorted(set(old[rtype]) - set(new[rtype]))
        if add:
            added[rtype] = add
        if rem:
            removed[rtype] = rem
    return added, removed


def resolve_dns(domain):
    """The live DNS snapshot for a domain (A/AAAA/MX/TXT).

    A/AAAA come from getaddrinfo (stdlib, no new dependency);
    MX/TXT come from dig +short, because the stdlib has no DNS
    record resolver. No dig, a dig failure, or a timeout is an
    exception: the patrol records it as a summary error, never as
    an empty snapshot (an empty snapshot would read as every
    record vanishing at once).
    """
    import shutil
    import subprocess

    addresses = {"A": [], "AAAA": []}
    try:
        infos = socket.getaddrinfo(domain, None)
    except socket.gaierror as exc:
        raise RuntimeError("dns lookup failed for %s: %s" % (domain, exc))
    for info in infos:
        family, _socktype, _proto, _canon, sockaddr = info
        if family == socket.AF_INET:
            addresses["A"].append(sockaddr[0])
        elif family == socket.AF_INET6:
            addresses["AAAA"].append(sockaddr[0])
    dig = shutil.which("dig")
    if dig is None:
        raise RuntimeError("dig not found: MX/TXT unavailable for %s"
                           % domain)
    snapshot = {"A": addresses["A"], "AAAA": addresses["AAAA"]}
    for rtype in ("MX", "TXT"):
        try:
            proc = subprocess.run(
                [dig, "+short", rtype, domain],
                capture_output=True, text=True, timeout=DNS_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise RuntimeError("dig %s timed out for %s" % (rtype, domain))
        if proc.returncode != 0:
            raise RuntimeError("dig %s failed for %s: %s"
                               % (rtype, domain, proc.stderr.strip()))
        snapshot[rtype] = [line for line in
                           (proc.stdout.splitlines() or []) if line.strip()]
    return normalize_snapshot(snapshot)


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


def fetch_headers(host, port, timeout=HEADER_TIMEOUT):
    """Response headers the host actually serves, keys lowercased.

    A HEAD request, https on 443 and http elsewhere. An HTTP error
    still carries headers, so it is read, not raised: a 405 on HEAD
    is a served response, not a failed probe. Anything else that
    fails (no route, timeout, TLS error) raises, and the patrol
    records it as a summary error, never as data.
    """
    scheme = "https" if int(port) == 443 else "http"
    url = "%s://%s:%d/" % (scheme, host, int(port))
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": "meta-custos/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.headers
    except urllib.error.HTTPError as exc:
        raw = exc.headers
    return {str(k).lower(): str(v) for k, v in raw.items()}


# ---------------------------------------------------------------------
# The patrol.

def run_patrol(config, now, fetch_kev_fn, probe_cert_fn, probe_port_fn,
               seen_cve=None, fetch_ct_fn=None, seen_ct=None,
               fetch_headers_fn=None, fetch_dns_fn=None, seen_dns=None):
    """One patrol. Returns (records, seen_cve, seen_ct).

    Every observation is classified and recorded. Yellow records are
    never escalated (zero escalation calls — the escalation list is
    built only from red records, here, in one place). A signal that
    fails is noted in the summary, never turned into data.

    seen_dns is the DNS baseline map {domain: snapshot}, updated
    IN PLACE (dicts, unlike the seen sets, are not copied): the
    caller reads it back after the call and persists it. A domain
    missing from it is a first sighting: the snapshot is stored
    and no record is written.
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

    # 1c. DNS drift: snapshot watched domains, compare with the
    # baseline. First sighting stores silently; a change is a
    # yellow record carrying the diff; a failed fetch is a summary
    # error, never an empty snapshot.
    dns_domains = config.get("dns_domains") or config.get("ct_domains", [])
    dns_fetch = fetch_dns_fn or resolve_dns
    dns_state = seen_dns if seen_dns is not None else {}
    for domain in dns_domains:
        try:
            snapshot = normalize_snapshot(dns_fetch(domain))
        except Exception as exc:  # resolver down: noted, never invented
            errors.append("dns fetch failed for %s: %s" % (domain, exc))
            continue
        previous = dns_state.get(domain)
        dns_state[domain] = snapshot
        if previous is None:
            continue
        added, removed = diff_snapshots(previous, snapshot)
        if added or removed:
            records.append(make_record(now, "dns", domain, "dns drift",
                                       {"added": added,
                                        "removed": removed}))

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
        # 2b. Security-headers audit, live hosts only: a failed
        # fetch is a summary error, never data, never a fix.
        headers_fetch = fetch_headers_fn or fetch_headers
        try:
            served = headers_fetch(host, port)
        except Exception as exc:
            errors.append("headers fetch failed for %s:%d: %s"
                          % (host, port, exc))
        else:
            present, missing = header_audit(served)
            records.append(make_record(
                now, "headers", host, classify_headers(missing),
                {"port": port, "score": len(present),
                 "max_score": len(SECURITY_HEADERS),
                 "present": present, "missing": missing}))
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
        "dns_domains_checked": len(dns_domains),
        "observations": counts,
        "escalations": len(escalations),
        "errors": errors,
    })
    return records, seen, seen_ids


# ---------------------------------------------------------------------
# CLI.

def load_state(path):
    """(seen_cve, seen_ct, seen_dns) from a state file.

    State files written before the DNS watcher lack seen_dns;
    they load as an empty baseline, so the next patrol stores
    first sightings silently instead of reporting phantom drift.
    """
    if path and os.path.isfile(path):
        with open(path) as f:
            data = json.load(f)
        return (set(data.get("seen_cve", [])),
                set(data.get("seen_ct", [])),
                dict(data.get("seen_dns", {})))
    return set(), set(), {}


def save_state(path, seen_cve, seen_ct, seen_dns=None):
    if path:
        with open(path, "w") as f:
            json.dump({"seen_cve": sorted(seen_cve),
                       "seen_ct": sorted(seen_ct),
                       "seen_dns": seen_dns or {}}, f, indent=1)


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
    run.add_argument("--dns-file", help="read DNS snapshots from a local "
                                        "JSON file {domain: snapshot} "
                                        "instead of resolving them")
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

    if args.dns_file:
        with open(args.dns_file) as f:
            dns_feed = json.load(f)

        def fetch_dns_fn(domain, _feed=dns_feed):
            if domain not in _feed:
                raise ValueError("no dns fixture for %s" % domain)
            return _feed[domain]
    else:
        fetch_dns_fn = None

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen, seen_ct, seen_dns = load_state(args.state)
    records, seen, seen_ct = run_patrol(config, now, fetch_fn, probe_cert,
                                        probe_port, seen, fetch_ct_fn,
                                        seen_ct, fetch_dns_fn=fetch_dns_fn,
                                        seen_dns=seen_dns)
    save_state(args.state, seen, seen_ct, seen_dns)

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
