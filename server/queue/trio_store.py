"""trio_store.py — OS jobs-store semantics for the Trio queue service.

Mirrors meta-os jobs.py on top of the same transport jobs.py uses:
Upstash Redis REST (GET command paths for small values, POST bodies
for big ones), reached through the dynamic-credential surrogate for
connector custom.upstash — the credential value is never read,
printed, or logged here. The store host is deployment configuration,
resolved at runtime (the TRIO_UPSTASH_HOST env var, or the REST URL
carried on the credential record when it has one) — it is never
hardcoded in this repo.

Key layout (namespace overridable via TRIO_JOB_NS, default "trio"):
  <NS>:<jid>        hash: status/product/claim/claimed_at/lease_until/…
  <NS>:<jid>:job    string: the full trio-assessment v1 envelope JSON
                    (POST body channel, like jobs.py's spec key — the
                    envelope carries a base64 JPEG and is far too big
                    for a URL path segment)
  <NS>:<jid>:claim  claim mutex: SET NX EX <lease> (first claim wins)
  <NS>index         zset jid -> created_at
  trio:<jid>:result the ruled result envelope (Pax's bus-424 ruling):
                    written once by the resident agent, read by the
                    queue service. The result prefix is always "trio",
                    independent of the job namespace.

If the Upstash path is unreachable, LocalSqliteStore provides the same
command surface over a local SQLite file. It is a FALLBACK and is
always labelled as such by callers (/health, agent logs): with it,
service and agent share a file on this machine only — no cross-machine
queue semantics are claimed.
"""
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.parse
import urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import (  # noqa: E402
    add_surrogate_to_request, dynamic_credential_entry, read_json_response)

NS = os.environ.get("TRIO_JOB_NS", "trio")
RESULT_PREFIX = "trio"  # result keys are trio:<jid>:result (bus 424)
AGENT_CREDENTIAL = "custom.upstash"


class TrioStoreConfigError(RuntimeError):
    """The Upstash store host could not be resolved from configuration.

    Raised when neither TRIO_UPSTASH_HOST nor the custom.upstash
    credential record supplies the store host. The host is deployment
    configuration and is never hardcoded in this repo.
    """


_HOST_ENTRY_FIELDS = ("rest_url", "url", "base_url", "host", "hostname")


def _host_from_credential():
    """Best-effort: derive the store host from the credential record.

    The custom.upstash credential is resolved through the same
    dynamic-credential entry the REST token comes from. If that record
    carries a REST URL (or a host) in its metadata, parse the host out
    of it. The token surrogate itself is never inspected — only
    URL-shaped metadata fields are read. Returns None when the record
    carries no URL (its current shape: token only).
    """
    try:
        entry = dynamic_credential_entry(AGENT_CREDENTIAL,
                                         entry_name="access_token")
    except Exception:
        return None
    for field in _HOST_ENTRY_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        candidate = value.strip()
        host = urllib.parse.urlparse(
            candidate if "://" in candidate else f"https://{candidate}"
        ).hostname
        if host:
            return host
    return None


def resolve_upstash_host():
    """Resolve the Upstash store host at runtime; never hardcoded.

    Order: (1) the TRIO_UPSTASH_HOST env var (a bare host, or a full
    REST URL whose host is taken); (2) the custom.upstash credential
    record, when it carries a REST URL. Raises TrioStoreConfigError
    naming the missing configuration when neither source supplies a
    host — there is deliberately no hardcoded fallback.
    """
    env = os.environ.get("TRIO_UPSTASH_HOST", "").strip()
    if env:
        host = urllib.parse.urlparse(
            env if "://" in env else f"https://{env}").hostname
        if host:
            return host
    host = _host_from_credential()
    if host:
        return host
    raise TrioStoreConfigError(
        "Upstash store host is not configured: set TRIO_UPSTASH_HOST "
        "to the store host (or its full REST URL), or store the REST "
        "URL on the custom.upstash credential record. The host is "
        "deployment configuration and is never hardcoded.")


def job_key(jid):
    return f"{NS}:{jid}"


def envelope_key(jid):
    return f"{NS}:{jid}:job"


def claim_key(jid):
    return f"{NS}:{jid}:claim"


def index_key():
    return f"{NS}index"


def result_key(jid):
    return f"{RESULT_PREFIX}:{jid}:result"


def _q(s):
    return urllib.parse.quote(str(s), safe="")


# ---------------------------------------------------------------------------
# Backends: one small Redis-command surface, two implementations.
# ---------------------------------------------------------------------------

class UpstashStore:
    """Redis commands over Upstash REST via the credential surrogate."""

    name = "upstash-redis"

    def __init__(self):
        # Host resolution is lazy (construction time, never import
        # time): RELAY_URL, when set, is a full base-URL override and
        # wins; otherwise the host comes from resolve_upstash_host()
        # (TRIO_UPSTASH_HOST env, then the credential record's REST
        # URL) and the base URL is built from it.
        base = os.environ.get("RELAY_URL", "").strip()
        if base:
            self.base_url = base.rstrip("/")
            self.host = urllib.parse.urlparse(self.base_url).hostname
            if not self.host:
                raise TrioStoreConfigError(
                    "RELAY_URL is set but has no parseable host; set it "
                    "to the full store base URL, or unset it and set "
                    "TRIO_UPSTASH_HOST instead.")
        else:
            self.host = resolve_upstash_host()
            self.base_url = f"https://{self.host}"

    def _call(self, path, data=None, method="GET"):
        req = urllib.request.Request(self.base_url + "/" + path, data=data,
                                     method=method)
        req.add_header("User-Agent", "trio-queue")
        add_surrogate_to_request(req, AGENT_CREDENTIAL,
                                 entry_name="access_token",
                                 allowed_hosts=[self.host])
        last = "no attempts"
        for _ in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return read_json_response(resp)["result"]
            except Exception as e:  # transport retry, like relay_common
                last = str(e)[:160]
                time.sleep(1)
                req = urllib.request.Request(self.base_url + "/" + path,
                                             data=data, method=method)
                req.add_header("User-Agent", "trio-queue")
                add_surrogate_to_request(req, AGENT_CREDENTIAL,
                                         entry_name="access_token",
                                         allowed_hosts=[self.host])
        raise RuntimeError(f"upstash call failed ({path.split('/')[0]}): {last}")

    def ping(self):
        return self._call("ping") == "PONG"

    def get(self, key):
        return self._call(f"get/{key}")

    def set_body(self, key, body):
        data = body.encode("utf-8") if isinstance(body, str) else body
        return self._call(f"set/{key}", data=data, method="POST")

    def delete(self, *keys):
        return self._call("del/" + "/".join(keys))

    def set_nx_ex(self, key, value, lease):
        return self._call(f"set/{key}/{_q(value)}/NX/EX/{int(lease)}") == "OK"

    def set_xx_ex(self, key, value, lease):
        return self._call(f"set/{key}/{_q(value)}/XX/EX/{int(lease)}") == "OK"

    def hset(self, key, mapping):
        pairs = []
        for f, v in mapping.items():
            if v is None or v == "":
                continue  # empty path segments 400 on Upstash REST
            pairs.append(f"{_q(f)}/{_q(v)}")
        if pairs:
            return self._call(f"hset/{key}/{'/'.join(pairs)}")
        return 0

    def hgetall(self, key):
        raw = self._call(f"hgetall/{key}") or []
        it = iter(raw)
        return dict(zip(it, it))

    def zadd(self, key, score, member):
        return self._call(f"zadd/{key}/{int(score)}/{_q(member)}")

    def zrange(self, key):
        return self._call(f"zrange/{key}/0/-1") or []


class LocalSqliteStore:
    """FALLBACK ONLY: same command surface over a local SQLite file."""

    name = "local-sqlite-FALLBACK"

    def __init__(self, path):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS kv"
            " (key TEXT PRIMARY KEY, value TEXT, expires REAL);"
            "CREATE TABLE IF NOT EXISTS hashes"
            " (key TEXT, field TEXT, value TEXT,"
            "  PRIMARY KEY (key, field));"
            "CREATE TABLE IF NOT EXISTS zsets"
            " (key TEXT, member TEXT, score REAL,"
            "  PRIMARY KEY (key, member));")
        self._db.commit()

    def ping(self):
        return True

    def _live(self, key):
        row = self._db.execute(
            "SELECT value, expires FROM kv WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        if row[1] is not None and time.time() > row[1]:
            self._db.execute("DELETE FROM kv WHERE key=?", (key,))
            self._db.commit()
            return None
        return row[0]

    def get(self, key):
        with self._lock:
            return self._live(key)

    def set_body(self, key, body):
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO kv VALUES (?,?,NULL)",
                (key, body if isinstance(body, str) else body.decode()))
            self._db.commit()
        return "OK"

    def delete(self, *keys):
        with self._lock:
            n = 0
            for key in keys:
                n += self._db.execute(
                    "DELETE FROM kv WHERE key=?", (key,)).rowcount
                self._db.execute("DELETE FROM hashes WHERE key=?", (key,))
                self._db.execute("DELETE FROM zsets WHERE key=?", (key,))
            self._db.commit()
            return n

    def set_nx_ex(self, key, value, lease):
        with self._lock:
            if self._live(key) is not None:
                return False
            self._db.execute("INSERT INTO kv VALUES (?,?,?)",
                             (key, value, time.time() + lease))
            self._db.commit()
            return True

    def set_xx_ex(self, key, value, lease):
        with self._lock:
            if self._live(key) is None:
                return False
            self._db.execute("UPDATE kv SET value=?, expires=? WHERE key=?",
                             (value, time.time() + lease, key))
            self._db.commit()
            return True

    def hset(self, key, mapping):
        with self._lock:
            n = 0
            for f, v in mapping.items():
                if v is None or v == "":
                    continue
                self._db.execute(
                    "INSERT OR REPLACE INTO hashes VALUES (?,?,?)",
                    (key, str(f), str(v)))
                n += 1
            self._db.commit()
            return n

    def hgetall(self, key):
        with self._lock:
            rows = self._db.execute(
                "SELECT field, value FROM hashes WHERE key=?",
                (key,)).fetchall()
            return {f: v for f, v in rows}

    def zadd(self, key, score, member):
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO zsets VALUES (?,?,?)",
                             (key, str(member), float(score)))
            self._db.commit()
            return 1

    def zrange(self, key):
        with self._lock:
            rows = self._db.execute(
                "SELECT member FROM zsets WHERE key=? ORDER BY score",
                (key,)).fetchall()
            return [r[0] for r in rows]


def open_store(local_path):
    """Return (store, fell_back). Upstash first; honest fallback second.

    TRIO_STORE=local forces the fallback (used to prove it works).
    """
    if os.environ.get("TRIO_STORE", "").lower() != "local":
        try:
            store = UpstashStore()
            if store.ping():
                return store, False
        except Exception as e:
            print(f"trio_store: Upstash unreachable ({e}); "
                  f"falling back to local SQLite", file=sys.stderr)
    return LocalSqliteStore(local_path), True


# ---------------------------------------------------------------------------
# Job semantics on top of the command surface (jobs.py-shaped).
# ---------------------------------------------------------------------------

class JobStore:
    def __init__(self, backend):
        self.b = backend

    # -- submission ------------------------------------------------------

    def submit(self, envelope):
        """File a trio-assessment envelope. Returns (jid, created)."""
        jid = envelope["id"]
        if self.b.hgetall(job_key(jid)):
            return jid, False  # idempotent: same deterministic id
        now = int(time.time())
        self.b.set_body(envelope_key(jid), json.dumps(envelope))
        self.b.hset(job_key(jid), {
            "status": "open",
            "kind": envelope.get("kind", ""),
            "version": envelope.get("version", ""),
            "product": envelope.get("product", ""),
            "timestamp": envelope.get("timestamp", ""),
            "created_at": now,
        })
        self.b.zadd(index_key(), now, jid)
        return jid, True

    # -- reads -----------------------------------------------------------

    def job_fields(self, jid):
        return self.b.hgetall(job_key(jid))

    def job_envelope(self, jid):
        raw = self.b.get(envelope_key(jid))
        if raw is None:
            return None
        try:
            env = json.loads(raw)
        except ValueError:
            return None
        return env if isinstance(env, dict) else None

    def open_job_ids(self):
        out = []
        for jid in self.b.zrange(index_key()):
            h = self.b.hgetall(job_key(jid))
            if h and h.get("status") == "open":
                out.append(jid)
        return out

    def get_result(self, jid):
        raw = self.b.get(result_key(jid))
        if raw is None:
            return None
        try:
            env = json.loads(raw)
        except ValueError:
            return None
        return env if isinstance(env, dict) else None

    # -- claiming (SET NX mutex + lease, exactly like jobs.py) -----------

    def claim(self, jid, who, lease):
        if not self.b.set_nx_ex(claim_key(jid), who, lease):
            return False
        now = int(time.time())
        self.b.hset(job_key(jid), {
            "status": "claimed", "claim": who, "claimed_at": now,
            "lease_until": now + int(lease), "lease": int(lease),
        })
        return True

    def renew_claim(self, jid, who, lease):
        return self.b.set_xx_ex(claim_key(jid), who, lease)

    def release_claim(self, jid):
        try:
            self.b.delete(claim_key(jid))
        except Exception:
            pass

    # -- completion --------------------------------------------------------

    def put_result(self, result_env):
        self.b.set_body(result_key(result_env["job_id"]),
                        json.dumps(result_env))

    def finish(self, jid, status, note=""):
        self.b.hset(job_key(jid), {
            "status": status, "note": note,
            "done_at": int(time.time()),
        })
        self.release_claim(jid)
