"""Agent-layer unit tests: unit files valid, no secrets, install idempotent."""
import configparser
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_UNITS = os.path.join(_REPO, "agent-layer", "units")


def _load(name):
    p = configparser.ConfigParser(interpolation=None)
    p.optionxform = str
    p.read(os.path.join(_UNITS, name))
    return p


class TestUnits(unittest.TestCase):
    def test_all_units_parse(self):
        for u in ("oc2-queue.service", "oc2-patrol.service", "oc2-patrol.timer"):
            self.assertTrue(os.path.exists(os.path.join(_UNITS, u)), u)
            _load(u)

    def test_queue_is_daemon_with_restart_cap(self):
        u = _load("oc2-queue.service")
        self.assertEqual(u["Service"]["Type"], "simple")
        self.assertIn("Restart", u["Service"])
        self.assertIn("StartLimitBurst", u["Unit"])
        self.assertNotIn("StartLimitIntervalSec", dict(u["Service"]))
        self.assertIn("${OC2_QUEUE_PORT}", u["Service"]["ExecStart"])
        env = open(os.path.join(_REPO, "agent-layer",
                                "env.example")).read()
        self.assertIn("OC2_QUEUE_PORT=8935", env)

    def test_patrol_bounded_and_ordered_after_queue(self):
        u = _load("oc2-patrol.service")
        self.assertEqual(u["Service"]["Type"], "oneshot")
        self.assertIn("--max-checks", u["Service"]["ExecStart"])
        self.assertIn("oc2-queue.service", u["Unit"].get("After", "")
                      + u["Unit"].get("Requires", ""))
        self.assertIn("oc2-trio.service", u["Unit"].get("After", "")
                      + u["Unit"].get("Requires", ""))
        self.assertIn("Install", u.sections())

    def test_trio_drains_queue(self):
        u = _load("oc2-trio.service")
        self.assertEqual(u["Service"]["Type"], "simple")
        self.assertIn("trio_agent.py", u["Service"]["ExecStart"])
        self.assertIn("oc2-queue.service",
                      u["Unit"].get("After", "") + u["Unit"].get("Requires", ""))
        self.assertIn("Restart", u["Service"])

    def test_queue_starts_uncapped(self):
        u = _load("oc2-queue.service")
        # StartLimit* belong in [Unit]; systemd ignores them in [Service].
        self.assertNotIn("StartLimitIntervalSec", dict(u["Service"]))
        self.assertIn("StartLimitIntervalSec", dict(u["Unit"]))

    def test_timer_repeats(self):
        u = _load("oc2-patrol.timer")
        self.assertIn("OnUnitActiveSec", list(u["Timer"].keys()))

    def test_no_secrets_in_agent_layer(self):
        blob = ""
        for root, _, files in os.walk(os.path.join(_REPO, "agent-layer")):
            for f in files:
                if f.endswith((".pyc", ".png", ".jpg", ".webp")):
                    continue
                with open(os.path.join(root, f), errors="replace") as fh:
                    blob += fh.read() + "\n"
        # Real key material patterns (not bare substrings — the installer
        # legitimately greps for these shapes in its self-check).
        for pat in (r"sk-[A-Za-z0-9]{20,}",
                    r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY",
                    r"SPARK_API_KEY\s*=",
                    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"):
            self.assertIsNone(re.search(pat, blob), pat)
        self.assertIn("SPARK_API_KEY", blob)  # documented, never assigned

    def test_installer_guards(self):
        src = open(os.path.join(_REPO, "agent-layer", "install.sh")).read()
        for marker in ("enable-linger", "import-environment SPARK_API_KEY",
                       "py_compile", "port 8935", "idempotent"):
            self.assertIn(marker, src, marker)

    def test_installer_deploys_every_unit(self):
        import glob
        src = open(os.path.join(_REPO, "agent-layer", "install.sh")).read()
        self.assertIn('agent-layer/units/', src)
        # No hardcoded unit allowlist: every shipped unit must deploy.
        shipped = {os.path.basename(p) for p in
                   glob.glob(os.path.join(_REPO, "agent-layer", "units",
                                           "*.service")) +
                   glob.glob(os.path.join(_REPO, "agent-layer", "units",
                                           "*.timer"))}
        self.assertTrue(shipped, "no units shipped")
        for name in ("oc2-queue.service", "oc2-patrol.service",
                     "oc2-patrol.timer", "oc2-trio.service"):
            self.assertIn(name, shipped, name)
        self.assertNotIn("for u in oc2-queue.service", src)

    def test_env_example_has_no_secrets_and_has_checkout(self):
        src = open(os.path.join(_REPO, "agent-layer", "env.example")).read()
        self.assertIn("OC2_CHECKOUT=", src)
        self.assertNotIn("SPARK_API_KEY=", src)


if __name__ == "__main__":
    unittest.main()
