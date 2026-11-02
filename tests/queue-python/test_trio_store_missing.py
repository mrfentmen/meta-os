"""Missing-case tests for the Python trio store (B226).

Cases the existing queue suite does not cover: key layout, host
resolution refusals, the SQLite fallback's lease/expiry edges, and
JobStore's malformed-record behaviour.

Offline only: the local SQLite fallback in a temp file; no Upstash
call is ever attempted (the transport path is refused before any
request when the helper is absent).
"""
import os
import sys
import tempfile
import time
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")

_TMP = tempfile.mkdtemp(prefix="trio-store-missing-")
os.environ["TRIO_STORE"] = "local"
os.environ["TRIO_LOCAL_DB"] = os.path.join(_TMP, "store.db")
os.environ.pop("TRIO_UPSTASH_HOST", None)
os.environ.pop("RELAY_URL", None)

sys.path.insert(0, QUEUE_DIR)

import trio_store  # noqa: E402


def envelope(jid="trio-abc", **kw):
    env = {"id": jid, "kind": "trio-assessment", "version": 1,
           "product": "vigiles",
           "timestamp": "2026-11-02T00:00:00.000Z"}
    env.update(kw)
    return env


def local_store():
    path = tempfile.mktemp(prefix="trio-store-", suffix=".db", dir=_TMP)
    return trio_store.LocalSqliteStore(path)


class KeyLayoutTests(unittest.TestCase):
    def test_job_keys_use_the_module_namespace(self):
        self.assertEqual(trio_store.job_key("j1"),
                         f"{trio_store.NS}:j1")
        self.assertEqual(trio_store.envelope_key("j1"),
                         f"{trio_store.NS}:j1:job")
        self.assertEqual(trio_store.claim_key("j1"),
                         f"{trio_store.NS}:j1:claim")
        self.assertEqual(trio_store.index_key(),
                         f"{trio_store.NS}index")

    def test_result_key_is_always_the_trio_prefix(self):
        # The result prefix is fixed (bus-424 ruling); it does not
        # follow TRIO_JOB_NS.
        self.assertEqual(trio_store.result_key("j1"),
                         "trio:j1:result")

    def test_quote_encodes_path_separators(self):
        self.assertEqual(trio_store._q("a/b c"), "a%2Fb%20c")


class HostResolutionTests(unittest.TestCase):
    def test_env_full_url_yields_its_host(self):
        with unittest.mock.patch.dict(
                os.environ, {"TRIO_UPSTASH_HOST":
                             "https://store.example:443"}):
            self.assertEqual(trio_store.resolve_upstash_host(),
                             "store.example")

    def test_unconfigured_raises_the_typed_error(self):
        with unittest.mock.patch.dict(
                os.environ, {"TRIO_UPSTASH_HOST": "",
                             "RELAY_URL": ""}), \
                unittest.mock.patch.object(
                    trio_store, "_host_from_credential",
                    return_value=None):
            with self.assertRaises(trio_store.TrioStoreConfigError):
                trio_store.resolve_upstash_host()

    def test_relay_url_without_a_host_is_refused(self):
        with unittest.mock.patch.dict(
                os.environ, {"RELAY_URL": "https://"}):
            with self.assertRaises(trio_store.TrioStoreConfigError):
                trio_store.UpstashStore()

    @unittest.skipUnless(
        trio_store.add_surrogate_to_request is None,
        "dynamic-credential helper is installed on this machine")
    def test_upstash_call_without_the_helper_is_refused(self):
        with unittest.mock.patch.dict(
                os.environ, {"RELAY_URL": "http://127.0.0.1:9"}):
            store = trio_store.UpstashStore()
            self.assertEqual(store.host, "127.0.0.1")
            with self.assertRaises(trio_store.TrioStoreConfigError):
                store._call("ping")


class LocalStoreTests(unittest.TestCase):
    def test_nx_then_xx_lease_semantics(self):
        store = local_store()
        self.assertTrue(store.set_nx_ex("k", "v1", 10))
        self.assertFalse(store.set_nx_ex("k", "v2", 10))
        self.assertEqual(store.get("k"), "v1")
        self.assertTrue(store.set_xx_ex("k", "v2", 10))
        self.assertEqual(store.get("k"), "v2")
        self.assertFalse(store.set_xx_ex("absent", "v", 10))

    def test_expired_key_reads_none_and_can_be_reclaimed(self):
        store = local_store()
        self.assertTrue(store.set_nx_ex("lease", "v", 0.01))
        time.sleep(0.05)
        self.assertIsNone(store.get("lease"))
        self.assertTrue(store.set_nx_ex("lease", "v2", 10))

    def test_hset_drops_empty_values(self):
        store = local_store()
        n = store.hset("h", {"a": "1", "b": "", "c": None})
        self.assertEqual(n, 1)
        self.assertEqual(store.hgetall("h"), {"a": "1"})

    def test_delete_counts_only_kv_rows(self):
        store = local_store()
        store.set_body("kv", "x")
        self.assertEqual(store.delete("kv"), 1)
        store.hset("hash-only", {"a": "1"})
        self.assertEqual(store.delete("hash-only"), 0)
        self.assertEqual(store.hgetall("hash-only"), {})

    def test_zrange_orders_by_score(self):
        store = local_store()
        store.zadd("z", 2, "b")
        store.zadd("z", 1, "a")
        store.zadd("z", 3, "c")
        self.assertEqual(store.zrange("z"), ["a", "b", "c"])


class JobStoreTests(unittest.TestCase):
    def test_submit_is_idempotent(self):
        store = local_store()
        jobs = trio_store.JobStore(store)
        jid, created = jobs.submit(envelope("job-1"))
        self.assertEqual((jid, created), ("job-1", True))
        jid, created = jobs.submit(envelope("job-1"))
        self.assertEqual((jid, created), ("job-1", False))
        self.assertEqual(store.zrange(trio_store.index_key()),
                         ["job-1"])

    def test_envelope_and_result_return_none_on_garbage(self):
        store = local_store()
        jobs = trio_store.JobStore(store)
        store.set_body(trio_store.envelope_key("j"), "not json")
        store.set_body(trio_store.result_key("j"), "[]")
        self.assertIsNone(jobs.job_envelope("j"))
        self.assertIsNone(jobs.get_result("j"))

    def test_claim_is_first_wins_and_finish_releases_it(self):
        store = local_store()
        jobs = trio_store.JobStore(store)
        jobs.submit(envelope("job-2"))
        self.assertTrue(jobs.claim("job-2", "agent-a", 30))
        self.assertFalse(jobs.claim("job-2", "agent-b", 30))
        fields = jobs.job_fields("job-2")
        self.assertEqual(fields["status"], "claimed")
        self.assertEqual(fields["claim"], "agent-a")
        jobs.finish("job-2", "done", "ok")
        self.assertEqual(jobs.job_fields("job-2")["status"], "done")
        self.assertIsNone(store.get(trio_store.claim_key("job-2")))

    def test_open_job_ids_filters_closed_jobs(self):
        store = local_store()
        jobs = trio_store.JobStore(store)
        jobs.submit(envelope("open-1"))
        jobs.submit(envelope("done-1"))
        jobs.finish("done-1", "done")
        self.assertEqual(jobs.open_job_ids(), ["open-1"])

    def test_claim_on_an_unknown_job_creates_a_partial_hash(self):
        # Pinned as the code behaves: claim does not verify that the
        # job was submitted (recorded as a finding in the behaviour
        # record).
        store = local_store()
        jobs = trio_store.JobStore(store)
        self.assertTrue(jobs.claim("ghost", "agent-a", 30))
        self.assertEqual(jobs.job_fields("ghost")["status"], "claimed")


if __name__ == "__main__":
    unittest.main()
