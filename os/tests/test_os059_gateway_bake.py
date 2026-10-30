"""tests/test_os059_gateway_bake.py -- OS-059: the gateway bake.

OS-059 bakes Dale's MCP gateway beside /opt/relay so the OS-058
daemon unit has something to run: gateway.py plus backends.json
(the catalog), a bake stamp recording the date, the source dir,
and the sha256 of both baked files, and the unit enabled under
relay.target on all three image routes. The pin is by hash,
not by commit, because the gateway source is a workspace
checkout, not a git repo.

What is pinned here is file content, not a built image: no
image build has run from this tree in the sandbox, so a
booted gateway serving its catalog stays owed to a build
host run, as do the two standing gaps the docs state plainly:
the gateway Python deps (mcp, starlette, uvicorn) have no
venv or pip step in this bake, and the downstream server
runtimes are not baked, so only the backends whose runtimes
the image carries will come up (the gateway skips a dead
backend with a log line and keeps serving).

- relay.target Wants relay-mcp-gateway.service.
- build-image.sh: the enablement loop names the unit, and
  the bake block copies exactly gateway.py plus backends.json
  (never the working estate: no .venv, no servers/ runtimes,
  no debug/ logs), refuses a build when either source file
  is missing, and writes the .metaos-gateway-bake stamp with
  a sha256sum step. Bash syntax clean.
- build-live.sh stages the same two files plus the stamp
  under includes.chroot/opt/relay/mcp-gateway, with the same
  missing-source refusal. The live hook enables the unit.
- The Packer template carries file provisioners for the two
  files only, installs them plus the stamp plus a relay chown
  in its shell provisioner, and enables the unit.
- The OS-012 sweep gains the bake allowlist: a fixture
  rootfs with exactly gateway.py, backends.json, and the
  stamp sweeps clean, while a planted .env file, a venv
  file, or a servers/ file under the baked gateway dir is
  a finding with exit 1.
- The unit header no longer defers the enablement, and
  os/README.md plus plan/META_OS.md carry the OS-059 record
  with the gaps stated and no em dash in the new section.

No bus post, no live Redis, no network: pure file reads
plus the sweep run against temporary fixture rootfs dirs.
"""

import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")
TARGET = os.path.join(OS_DIR, "services", "relay.target")
UNIT = os.path.join(OS_DIR, "services", "relay-mcp-gateway.service")
BUILD_IMAGE = os.path.join(OS_DIR, "build-image.sh")
BUILD_LIVE = os.path.join(OS_DIR, "build-live.sh")
HOOK = os.path.join(
    OS_DIR, "live-build", "config", "hooks", "live",
    "0900-metaos-services.hook.chroot")
PACKER = os.path.join(OS_DIR, "packer", "metaos.pkr.hcl")
SWEEP = os.path.join(OS_DIR, "bin", "metaos-secrets-sweep")
README = os.path.join(OS_DIR, "README.md")
SPEC = os.path.join(ROOT, "plan", "META_OS.md")

GATEWAY_UNIT = "relay-mcp-gateway.service"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def enablement_loop(text):
    for line in text.splitlines():
        if "for u in" in line:
            return line
    return ""


def bake_section(text):
    start = text.find("2b. OS-059")
    end = text.find("# metaos-update expects", start)
    if start < 0 or end < 0:
        return ""
    return text[start:end]


def run_sweep(rootfs):
    return subprocess.run(
        ["sh", SWEEP, rootfs],
        capture_output=True, text=True, timeout=60)


def gateway_rootfs(extra_files):
    tmp = tempfile.mkdtemp(prefix="metaos-gateway-sweep-")
    gw = os.path.join(tmp, "opt", "relay", "mcp-gateway")
    os.makedirs(gw)
    for name in ("gateway.py", "backends.json", ".metaos-gateway-bake"):
        with open(os.path.join(gw, name), "w", encoding="utf-8") as handle:
            handle.write("# fixture\n")
    for rel in extra_files:
        path = os.path.join(gw, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("# planted\n")
    return tmp


class TargetWiringTest(unittest.TestCase):
    def test_target_wants_gateway(self):
        self.assertIn(GATEWAY_UNIT, read(TARGET))

    def test_unit_header_no_longer_defers_enablement(self):
        text = read(UNIT)
        self.assertIn("OS-059", text)
        self.assertNotIn("waits on OS-059", text)
        self.assertNotIn("does not Want", text)


class BuildImageBakeTest(unittest.TestCase):
    def test_enablement_loop_names_gateway(self):
        self.assertIn(GATEWAY_UNIT, enablement_loop(read(BUILD_IMAGE)))

    def test_bake_block_copies_only_daemon_and_catalog(self):
        section = bake_section(read(BUILD_IMAGE))
        self.assertTrue(section, "OS-059 bake block missing")
        self.assertIn("gateway.py", section)
        self.assertIn("backends.json", section)
        self.assertIn(".metaos-gateway-bake", section)
        self.assertIn("sha256sum gateway.py backends.json", section)
        self.assertIn(".venv", section)
        self.assertIn("servers/", section)
        self.assertNotIn("rsync", section)

    def test_bake_block_refuses_missing_source(self):
        section = bake_section(read(BUILD_IMAGE))
        self.assertIn('no gateway.py in', section)
        self.assertIn('no backends.json in', section)
        self.assertIn("METAOS_GATEWAY_SRC", section)

    def test_build_image_bash_syntax(self):
        proc = subprocess.run(["bash", "-n", BUILD_IMAGE],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class LiveBuildBakeTest(unittest.TestCase):
    def test_hook_enables_gateway(self):
        self.assertIn(GATEWAY_UNIT, enablement_loop(read(HOOK)))

    def test_wrapper_stages_gateway_and_stamp(self):
        text = read(BUILD_LIVE)
        self.assertIn("opt/relay/mcp-gateway", text)
        self.assertIn('no gateway.py in', text)
        self.assertIn('no backends.json in', text)
        self.assertIn(".metaos-gateway-bake", text)
        self.assertIn("sha256sum gateway.py backends.json", text)

    def test_wrapper_bash_syntax(self):
        proc = subprocess.run(["bash", "-n", BUILD_LIVE],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_hook_shell_syntax(self):
        proc = subprocess.run(["sh", "-n", HOOK],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class PackerBakeTest(unittest.TestCase):
    def test_file_provisioners_carry_only_daemon_and_catalog(self):
        text = read(PACKER)
        self.assertIn("mcp-gateway/gateway.py", text)
        self.assertIn("mcp-gateway/backends.json", text)
        self.assertNotIn("mcp-gateway/servers", text)
        self.assertNotIn("mcp-gateway/.venv", text)

    def test_shell_installs_stamp_and_enables(self):
        text = read(PACKER)
        self.assertIn("/opt/relay/mcp-gateway/", text)
        self.assertIn(".metaos-gateway-bake", text)
        self.assertIn("sha256sum gateway.py backends.json", text)
        self.assertIn("chown -R relay:relay /opt/relay/mcp-gateway", text)
        self.assertIn(GATEWAY_UNIT, enablement_loop(text))


class SweepAllowlistTest(unittest.TestCase):
    def test_allowlisted_gateway_tree_sweeps_clean(self):
        tmp = gateway_rootfs(())
        try:
            result = run_sweep(tmp)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("clean", result.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_planted_env_file_is_finding(self):
        tmp = gateway_rootfs((".env",))
        try:
            result = run_sweep(tmp)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("FINDING", result.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_planted_venv_and_servers_files_are_findings(self):
        for rel in (".venv/bin/python", "servers/printify-mcp/launch.sh",
                    "gateway.db"):
            tmp = gateway_rootfs((rel,))
            try:
                result = run_sweep(tmp)
                self.assertEqual(result.returncode, 1,
                                 "%s: %s" % (rel, result.stdout))
                self.assertIn("FINDING", result.stdout)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    def test_sweep_script_shell_syntax(self):
        proc = subprocess.run(["sh", "-n", SWEEP],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class DocsTest(unittest.TestCase):
    def test_readme_carries_os059_section_without_em_dash(self):
        text = read(README)
        self.assertIn("OS-059", text)
        start = text.find("Gateway bake (OS-059")
        self.assertGreaterEqual(start, 0)
        section = text[start:]
        section = section[:section.find("\n## ", 1)] if "\n## " in section[1:] else section
        self.assertNotIn("\u2014", section)

    def test_spec_records_os059_bake(self):
        text = read(SPEC)
        self.assertIn("OS-059", text)
        self.assertIn("relay-mcp-gateway.service", text)


if __name__ == "__main__":
    unittest.main()
