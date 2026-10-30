"""intel/mind_loader.py -- OS-102 (Pax): mind-image loader integration.

Process launch assembles and mounts a mind image (OS-101 bundle)
into a launch environment directory. This EXTENDS the OS-065
skills loader into the full assembly instead of duplicating it:
skills are one layer of the image, mounted here through
intel/skills_loader.py (a skill folder mounts only when it
carries a SKILL.md; a folder without one is not a mountable app
and assembly is refused, never silently skipped).

A launch environment is a plain directory a process starts from:

    launch.json       the launch manifest: bundle, kind, layer hashes
    instructions.md   constitution, copied verbatim
    skills/<name>/    each bundle skill, copied verbatim (OS-065 mount)
    memory/own        symlink to the bundle's own-memory mount point
    memory/shared     symlink to the shared mount point, or absent
                      when the bundle names no shared mount
    grants.json       capability grant, copied verbatim
    tool_grants.json  resolved tool grants, as a JSON list
    brief.json        environment brief file, copied verbatim, or
    brief.pending     when the bundle names the generated-at-launch
                      slot: a marker, never a fabricated brief
    changelog.md      bundle changelog, copied verbatim

Assembly rules, all enforced by assemble_launch():

- The bundle must resolve fully (OS-101 resolve_bundle, via
  validate_bundle). An unresolved layer is refused, never guessed.
- process_kind is exactly "worker" or "driver". Both kinds go
  through the identical layer assembly; only the manifest's kind
  differs, so a worker and a driver launched from one bundle
  carry identical layers. That is the OS-102 acceptance in code:
  no hand-assembled launches, no kind-specific layer shortcuts.
- A skill basename collision (two bundle skills with the same
  folder name) is refused: mount names must be unique.
- The launch directory must not already exist non-empty, so one
  launch can never silently mix with another.
- Memory is mounted, not copied: the launch memory points are
  symlinks to the bundle's resolved memory dirs. The OS-078
  memory service is not behind those points yet, so the manifest
  records them as bundle mounts, not as a service mount, and a
  launch against a live gateway catalog or a booted image is
  still owed (see the manifest's "not_proven" list).

verify_launch() re-reads a launch directory and checks it
against its bundle: every copied file's hash must still match
the manifest, every skill's files must still match, memory
symlinks must still point at the bundle's resolved mounts, the
grant's identity must still match the assembled grant, and the
tool grants must still match. Any mismatch is an error naming
the layer, never a silent pass.

Pure functions on the local filesystem. No bus posts, no
network, no model calls, no process spawning: this module
builds the environment a process starts from, it does not
start the process. Starting one is intel/launch_run.py
(OS-102 follow-up): it verifies the launch, then runs the
child with cwd set to the launch directory.
"""

import hashlib
import json
import os
import shutil

from intel import mind_image
from intel import skills_loader

LAUNCH_FORMAT = "metaos-mind-launch"
PROCESS_KINDS = ("worker", "driver")
BRIEF_SLOT = mind_image.BRIEF_SLOT

NOT_PROVEN = [
    "a driver or worker process started from a launch directory "
    "is covered by intel/launch_run.py for a probe process; a "
    "Muse Code driver run from a launch is still owed (OS-055)",
    "the OS-078 memory service behind the memory mount points "
    "(launches record bundle mounts, not a service mount)",
    "a launch against a live gateway catalog (catalogs supplied "
    "here are caller-supplied, as in OS-101)",
    "a launch on a booted test image",
]


class LaunchError(ValueError):
    """A launch failed assembly or verification; message names the fault."""


def _fail(msg):
    raise LaunchError(msg)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_tree(root):
    """Map relative file path to sha256 for every file under root."""
    hashes = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            hashes[rel] = _sha256(full)
    return hashes


def _copy_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    return _sha256(dst)


def _read_grant_identity(grant_path):
    with open(grant_path, "r", encoding="utf-8") as handle:
        grant = json.load(handle)
    if not isinstance(grant, dict):
        _fail("capability_grant: top level must be an object")
    identity = grant.get("identity")
    if not isinstance(identity, str) or not identity.strip():
        _fail("capability_grant: 'identity' must be a non-empty string")
    return identity


def assemble_launch(bundle_dir, launch_dir, gateway_catalog=None,
                    process_kind="worker"):
    """Assemble a resolved bundle into a launch environment.

    bundle_dir holds manifest.json (OS-101). launch_dir is created
    and must not already exist non-empty. Returns the launch
    manifest dict. Raises LaunchError on any refusal.
    """
    if process_kind not in PROCESS_KINDS:
        _fail(f"launch: process_kind must be one of {PROCESS_KINDS}, "
              f"got {process_kind!r}")
    bundle_dir = os.path.abspath(bundle_dir)
    launch_dir = os.path.abspath(launch_dir)
    if os.path.exists(launch_dir) and os.listdir(launch_dir):
        _fail(f"launch: launch directory already non-empty: {launch_dir}")
    manifest_path = os.path.join(bundle_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        _fail(f"launch: no manifest.json in bundle directory: {bundle_dir}")
    bundle, resolved_dir = mind_image.load_bundle(manifest_path)
    report = mind_image.validate_bundle(bundle, resolved_dir,
                                        gateway_catalog)
    layers = report["layers"]
    grant_identity = _read_grant_identity(layers["capability_grant"])

    skill_names = [os.path.basename(os.path.normpath(path))
                   for path in layers["skills"]]
    try:
        skills_hashes = skills_loader.mount_skill_dirs(
            list(zip(skill_names, layers["skills"])),
            os.path.join(launch_dir, "skills"))
    except skills_loader.SkillsLoaderError as exc:
        _fail(f"launch: {exc}")

    os.makedirs(launch_dir, exist_ok=True)
    layer_hashes = {}

    layer_hashes["constitution"] = _copy_file(
        layers["constitution"], os.path.join(launch_dir, "instructions.md"))
    layer_hashes["skills"] = skills_hashes

    memory = {}
    own_dst = os.path.join(launch_dir, "memory", "own")
    os.makedirs(os.path.dirname(own_dst), exist_ok=True)
    os.symlink(layers["memory_own"], own_dst)
    memory["own"] = layers["memory_own"]
    if layers.get("memory_shared") is not None:
        shared_dst = os.path.join(launch_dir, "memory", "shared")
        os.symlink(layers["memory_shared"], shared_dst)
        memory["shared"] = layers["memory_shared"]
    else:
        memory["shared"] = None

    layer_hashes["capability_grant"] = _copy_file(
        layers["capability_grant"], os.path.join(launch_dir, "grants.json"))
    layer_hashes["changelog"] = _copy_file(
        layers["changelog"], os.path.join(launch_dir, "changelog.md"))

    tool_grants = list(layers["tool_grants"])
    with open(os.path.join(launch_dir, "tool_grants.json"), "w",
              encoding="utf-8") as handle:
        json.dump(tool_grants, handle, sort_keys=True)
        handle.write("\n")

    brief = bundle["environment_brief"]
    if "file" in brief:
        layer_hashes["environment_brief"] = _copy_file(
            layers["environment_brief"],
            os.path.join(launch_dir, "brief.json"))
        brief_status = "file"
    else:
        with open(os.path.join(launch_dir, "brief.pending"), "w",
                  encoding="utf-8") as handle:
            handle.write("environment brief: " + BRIEF_SLOT + "\n")
            handle.write("generated at launch by OS-103; no brief "
                         "content is claimed here.\n")
        brief_status = "pending"

    manifest = {
        "format": LAUNCH_FORMAT,
        "bundle_format": mind_image.FORMAT,
        "bundle_version": bundle["version"],
        "agent": bundle["agent"],
        "process_kind": process_kind,
        "bundle_dir": bundle_dir,
        "layers": layer_hashes,
        "memory": memory,
        "grant_identity": grant_identity,
        "tool_grants": tool_grants,
        "brief_status": brief_status,
        "not_proven": list(NOT_PROVEN),
    }
    with open(os.path.join(launch_dir, "launch.json"), "w",
              encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


def assemble_worker_launch(bundle_dir, launch_dir, gateway_catalog=None):
    """Assemble a bundle into a crew-worker launch environment."""
    return assemble_launch(bundle_dir, launch_dir, gateway_catalog,
                           process_kind="worker")


def assemble_driver_launch(bundle_dir, launch_dir, gateway_catalog=None):
    """Assemble a bundle into a driver-process launch environment."""
    return assemble_launch(bundle_dir, launch_dir, gateway_catalog,
                           process_kind="driver")


def _load_launch_manifest(launch_dir):
    path = os.path.join(launch_dir, "launch.json")
    if not os.path.isfile(path):
        return None, [f"launch: no launch.json in {launch_dir}"]
    try:
        with open(path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (ValueError, OSError) as exc:
        return None, [f"launch: unreadable launch.json: {exc}"]
    if not isinstance(manifest, dict) or manifest.get("format") != LAUNCH_FORMAT:
        return None, ["launch: launch.json is not a metaos-mind-launch "
                      "manifest"]
    return manifest, []


def verify_launch(launch_dir, bundle_dir=None, gateway_catalog=None):
    """Verify a launch directory against its bundle.

    Returns {"ok": bool, "errors": [...]}. With bundle_dir given,
    the bundle is re-resolved and the launch is checked against
    that resolution; without it, the manifest's recorded bundle
    directory is used. A launch whose bundle directory no longer
    exists cannot be verified against its bundle and fails.
    """
    launch_dir = os.path.abspath(launch_dir)
    manifest, errors = _load_launch_manifest(launch_dir)
    if manifest is None:
        return {"ok": False, "errors": errors}
    bundle_path = bundle_dir or manifest.get("bundle_dir")
    if not bundle_path or not os.path.isdir(bundle_path):
        errors.append("launch: bundle directory missing, cannot verify "
                      "against its bundle")
        return {"ok": False, "errors": errors}
    manifest_path = os.path.join(bundle_path, "manifest.json")
    if not os.path.isfile(manifest_path):
        errors.append("launch: bundle has no manifest.json")
        return {"ok": False, "errors": errors}
    try:
        bundle, resolved_dir = mind_image.load_bundle(manifest_path)
        report = mind_image.validate_bundle(bundle, resolved_dir,
                                            gateway_catalog)
    except mind_image.BundleError as exc:
        return {"ok": False, "errors": [f"launch: bundle no longer "
                                        f"resolves: {exc}"]}
    layers = report["layers"]
    if bundle["agent"] != manifest.get("agent"):
        errors.append("launch: agent does not match the bundle")
    if bundle["version"] != manifest.get("bundle_version"):
        errors.append("launch: bundle version does not match the bundle")
    if manifest.get("process_kind") not in PROCESS_KINDS:
        errors.append("launch: unknown process_kind in manifest")
    recorded = manifest.get("layers", {})

    def check_file(layer, rel):
        path = os.path.join(launch_dir, rel)
        if not os.path.isfile(path):
            errors.append(f"launch: {layer} missing: {rel}")
        elif recorded.get(layer) != _sha256(path):
            errors.append(f"launch: {layer} changed since assembly: {rel}")

    check_file("constitution", "instructions.md")
    check_file("capability_grant", "grants.json")
    check_file("changelog", "changelog.md")
    try:
        grant_identity = _read_grant_identity(
            os.path.join(launch_dir, "grants.json"))
        if grant_identity != manifest.get("grant_identity"):
            errors.append("launch: capability grant identity changed "
                          "since assembly")
    except (LaunchError, ValueError, OSError) as exc:
        errors.append(f"launch: capability grant unreadable: {exc}")
    skill_hashes = recorded.get("skills", {})
    for name in sorted(skill_hashes):
        actual = _hash_tree(os.path.join(launch_dir, "skills", name)) \
            if os.path.isdir(os.path.join(launch_dir, "skills", name)) \
            else None
        if actual is None:
            errors.append(f"launch: skill missing: {name}")
        elif actual != skill_hashes[name]:
            errors.append(f"launch: skill changed since assembly: {name}")
    bundle_skill_names = [os.path.basename(os.path.normpath(path))
                          for path in layers["skills"]]
    if sorted(bundle_skill_names) != sorted(skill_hashes):
        errors.append("launch: mounted skills do not match the bundle")
    memory = manifest.get("memory", {})
    for slot in ("own", "shared"):
        link = os.path.join(launch_dir, "memory", slot)
        expected = layers.get("memory_" + slot)
        if expected is None:
            if os.path.lexists(link):
                errors.append(f"launch: unexpected memory mount: {slot}")
        elif not os.path.islink(link):
            errors.append(f"launch: memory mount is not a symlink: {slot}")
        elif os.path.realpath(link) != os.path.realpath(expected):
            errors.append(f"launch: memory mount points elsewhere: {slot}")
    if manifest.get("tool_grants") != list(layers["tool_grants"]):
        errors.append("launch: tool grants do not match the bundle")
    brief = bundle["environment_brief"]
    if "file" in brief:
        check_file("environment_brief", "brief.json")
        if manifest.get("brief_status") != "file":
            errors.append("launch: brief_status does not match the bundle")
    else:
        if manifest.get("brief_status") != "pending":
            errors.append("launch: brief_status does not match the bundle")
        if os.path.isfile(os.path.join(launch_dir, "brief.json")):
            errors.append("launch: slot brief must not carry a brief.json")
        if not os.path.isfile(os.path.join(launch_dir, "brief.pending")):
            errors.append("launch: slot brief missing brief.pending")
    return {"ok": not errors, "errors": errors}


def launch_summary(manifest):
    """One plain line naming the agent, bundle version, and kind."""
    agent = manifest["agent"]
    skills = len(manifest["layers"].get("skills", {}))
    tools = len(manifest.get("tool_grants", []))
    return (f"{agent['nick']} launch ({manifest['process_kind']}) from "
            f"mind image v{manifest['bundle_version']}: "
            f"constitution + {skills} skill(s) + {tools} tool grant(s), "
            f"brief {manifest['brief_status']}")
