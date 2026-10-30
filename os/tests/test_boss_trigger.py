#!/usr/bin/env python3
"""Interop + wiring + verifier tests for the signed boss trigger.

The relay chat (bus.html) got an HMAC-signed boss trigger: the boss's
browser signs a trigger envelope with a secret only the boss holds, and
Pax's watcher (trigger_check.py) verifies the signature before treating
anything as a genuine boss trigger. Bus nicks alone are spoofable, so
they are NOT trusted for this.

Part 1 (interop): extracts the pure trigger block from bus.html
(delimited by /*__TRIGGER_START__*/ / /*__TRIGGER_END__*/), runs it in
Node with fixed vectors, and checks the canonical payload construction
and HMAC-SHA256 against Python's hmac.

Part 2 (wiring): static assertions that the boss-trigger feature is
present in bus.html — secret panel, trigger button, SubtleCrypto
signing, the trigger-list write — and that no raw secret is embedded.

Part 3 (verifier): trigger_check.verify_envelope accepts a valid signed
envelope (mode "signed"), accepts an unsigned test envelope (mode
"unsigned"), and rejects tampered sigs, stale timestamps, replays,
wrong versions, and malformed fields. No network, no mocks.

No mocks: real Node JS vs real Python for the crypto.
"""
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "bus.html")
sys.path.insert(0, os.path.expanduser("~/workspace/relay-trigger/bin"))
import trigger_check  # noqa: E402 — the verifier under test

SECRET_HEX = ("0123456789abcdef" * 4)  # fixed test vector, 64 hex chars
SECRET = bytes.fromhex(SECRET_HEX)
NOW = 1726874100

NODE_DRIVER = """\
const crypto = require("crypto");
const SECRET = "%s";
const out = {};
out.canonical = triggerCanonical("mrfentmen", "who is alice", 1726874100);
out.sig = crypto.createHmac("sha256", Buffer.from(SECRET, "hex"))
  .update(triggerCanonical("mrfentmen", "who is alice", 1726874100), "utf8")
  .digest("hex");
out.roundtrip = triggerBytesToHex(triggerHexToBytes(SECRET)) === SECRET;
out.canonicalEmpty = triggerCanonical("a", "", 0);
out.canonicalUnicode = triggerCanonical("mrfentmen", "caf\\u00e9 \\u{1F600}", 1);
out.sigUnicode = crypto.createHmac("sha256", Buffer.from(SECRET, "hex"))
  .update(triggerCanonical("mrfentmen", "caf\\u00e9 \\u{1F600}", 1), "utf8")
  .digest("hex");
try { triggerHexToBytes("tooshort"); out.badHexOk = false; }
catch (e) { out.badHexOk = true; }
console.log(JSON.stringify(out));
""" % SECRET_HEX


def _trigger_block():
    with open(HTML, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"/\*__TRIGGER_START__\*/(.*?)/\*__TRIGGER_END__\*/",
                  html, re.S)
    assert m, "trigger block markers missing from bus.html"
    return m.group(1)


def _run_node(block):
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        f.write(block + "\n" + NODE_DRIVER)
        path = f.name
    try:
        r = subprocess.run(["node", path], capture_output=True, text=True,
                           timeout=30)
        assert r.returncode == 0, f"node failed: {r.stderr}"
        return json.loads(r.stdout)
    finally:
        os.unlink(path)


def _py_sig(nick, text, ts):
    payload = f"pax-trigger-v1\n{nick}\n{text}\n{ts}".encode("utf-8")
    return hmac.new(SECRET, payload, hashlib.sha256).hexdigest()


class Interop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = _run_node(_trigger_block())

    def test_canonical_matches(self):
        self.assertEqual(
            self.js["canonical"],
            "pax-trigger-v1\nmrfentmen\nwho is alice\n1726874100")

    def test_hmac_agrees(self):
        # Node's HMAC over the JS-built canonical payload must equal
        # Python's HMAC over the Python-built payload.
        self.assertEqual(self.js["sig"], _py_sig(
            "mrfentmen", "who is alice", 1726874100))

    def test_hex_roundtrip(self):
        self.assertTrue(self.js["roundtrip"])

    def test_unicode_payload_agrees(self):
        self.assertEqual(self.js["canonicalUnicode"],
                         "pax-trigger-v1\nmrfentmen\ncaf\u00e9 \U0001f600\n1")
        self.assertEqual(self.js["sigUnicode"],
                         _py_sig("mrfentmen", "caf\u00e9 \U0001f600", 1))

    def test_empty_text_canonical(self):
        self.assertEqual(self.js["canonicalEmpty"], "pax-trigger-v1\na\n\n0")

    def test_bad_hex_rejected(self):
        self.assertTrue(self.js["badHexOk"])


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(HTML, encoding="utf-8") as f:
            cls.html = f.read()

    def test_block_markers(self):
        self.assertIn("/*__TRIGGER_START__*/", self.html)
        self.assertIn("/*__TRIGGER_END__*/", self.html)

    def test_trigger_key(self):
        self.assertIn("muse-bus:pax-trigger", self.html)

    def test_secret_ui(self):
        self.assertIn("bosstrig-secret", self.html)
        self.assertIn('type="password"', self.html)

    def test_secret_is_optional_test_mode(self):
        # The hex secret is no longer a blocker: with no secret saved the
        # button posts an unsigned test envelope instead of refusing.
        self.assertIn("env.unsigned = true", self.html)
        self.assertIn("sig = null", self.html)
        self.assertIn("No secret", self.html)

    def test_trigger_button(self):
        self.assertIn("trigBtn", self.html)
        self.assertIn("Trigger", self.html)

    def test_subtle_crypto_signing(self):
        self.assertIn("crypto.subtle", self.html)
        self.assertIn('"HMAC"', self.html)

    def test_protocol_version(self):
        self.assertIn("pax-trigger-v1", self.html)

    def test_no_embedded_secret(self):
        # No 64-hex literal anywhere in the page: the secret is never
        # baked into the shipped HTML.
        self.assertIsNone(re.search(r"[0-9a-fA-F]{64}", self.html))

    def test_test_hook_exposed(self):
        self.assertIn("__busTest.bossTrigger", self.html)


class Verifier(unittest.TestCase):
    def verify(self, env, now=NOW, seen=None):
        mode, rkey, reason = trigger_check.verify_envelope(
            SECRET, env, now, set() if seen is None else seen)
        return mode, rkey, reason

    def test_valid_envelope(self):
        env = trigger_check.sign_envelope(SECRET, "mrfentmen",
                                          "who is alice", NOW)
        mode, rkey, reason = self.verify(env)
        self.assertEqual(mode, "signed", reason)
        self.assertEqual(rkey, env["sig"].lower())

    def test_tampered_text_rejected(self):
        env = trigger_check.sign_envelope(SECRET, "mrfentmen",
                                          "who is alice", NOW)
        env["text"] = "who is alice!!"
        mode, _, reason = self.verify(env)
        self.assertIsNone(mode)
        self.assertEqual(reason, "bad signature")

    def test_wrong_secret_rejected(self):
        env = trigger_check.sign_envelope(bytes(32), "mrfentmen",
                                          "who is alice", NOW)
        mode, _, _ = self.verify(env)
        self.assertIsNone(mode)

    def test_stale_ts_rejected(self):
        env = trigger_check.sign_envelope(
            SECRET, "mrfentmen", "old", NOW - 601)
        mode, _, reason = self.verify(env)
        self.assertIsNone(mode)
        self.assertEqual(reason, "stale ts")

    def test_future_ts_within_skew_ok(self):
        env = trigger_check.sign_envelope(
            SECRET, "mrfentmen", "soon", NOW + 60)
        mode, _, reason = self.verify(env)
        self.assertEqual(mode, "signed", reason)

    def test_replay_rejected(self):
        env = trigger_check.sign_envelope(SECRET, "mrfentmen",
                                          "once", NOW)
        seen = {env["sig"].lower()}
        mode, _, reason = self.verify(env, seen=seen)
        self.assertIsNone(mode)
        self.assertEqual(reason, "replay")

    def test_uppercase_sig_accepted(self):
        env = trigger_check.sign_envelope(SECRET, "mrfentmen",
                                          "shout", NOW)
        env["sig"] = env["sig"].upper()
        mode, _, reason = self.verify(env)
        self.assertEqual(mode, "signed", reason)

    def test_bad_version_rejected(self):
        env = trigger_check.sign_envelope(SECRET, "mrfentmen",
                                          "v2", NOW)
        env["v"] = 2
        mode, _, _ = self.verify(env)
        self.assertIsNone(mode)

    def test_malformed_fields_rejected(self):
        for bad in ({"v": 1}, {"v": 1, "nick": "", "text": "x",
                               "ts": NOW, "sig": "0" * 64},
                    {"v": 1, "nick": "mrfentmen", "text": "",
                     "ts": NOW, "sig": "0" * 64},
                    {"v": 1, "nick": "mrfentmen", "text": "x",
                     "ts": "now", "sig": "0" * 64},
                    "not-an-object", None):
            mode, _, _ = self.verify(bad)
            self.assertIsNone(mode, f"accepted {bad!r}")

    def test_unsigned_test_envelope_accepted(self):
        env = {"v": 1, "nick": "mrfentmen", "text": "test ping",
               "ts": NOW, "sig": None, "unsigned": True}
        mode, rkey, reason = self.verify(env)
        self.assertEqual(mode, "unsigned", reason)
        self.assertTrue(rkey.startswith("u:"))

    def test_unsigned_replay_rejected(self):
        env = {"v": 1, "nick": "mrfentmen", "text": "test ping",
               "ts": NOW, "sig": None, "unsigned": True}
        mode, rkey, _ = self.verify(env)
        self.assertEqual(mode, "unsigned")
        mode2, _, reason2 = self.verify(env, seen={rkey})
        self.assertIsNone(mode2)
        self.assertEqual(reason2, "replay")

    def test_unsigned_stale_ts_rejected(self):
        env = {"v": 1, "nick": "mrfentmen", "text": "old ping",
               "ts": NOW - 601, "sig": None, "unsigned": True}
        mode, _, reason = self.verify(env)
        self.assertIsNone(mode)
        self.assertEqual(reason, "stale ts")

    def test_null_sig_without_flag_rejected(self):
        env = {"v": 1, "nick": "mrfentmen", "text": "sneaky",
               "ts": NOW, "sig": None}
        mode, _, reason = self.verify(env)
        self.assertIsNone(mode)
        self.assertEqual(reason, "bad sig")

    def test_canonical_payload_stable(self):
        self.assertEqual(
            trigger_check.canonical_payload("mrfentmen", "who is alice",
                                            1726874100),
            b"pax-trigger-v1\nmrfentmen\nwho is alice\n1726874100")

if __name__ == "__main__":
    unittest.main(verbosity=2)
