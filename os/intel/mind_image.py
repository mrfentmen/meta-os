"""intel/mind_image.py -- OS-101 (Pax): mind-image bundle format.

A mind image is to an agent what a disk image is to a machine: the
complete, versioned bundle the OS assembles at launch, from which
the agent boots (plan/META_OS.md, "Mind images"). This module is
the format's first light: it parses and resolves a bundle, nothing
more. It does not assemble a launch (that is the OS-102 loader),
it does not mount anything, and it never talks to a gateway, a
memory service, or the bus.

A bundle is one JSON manifest plus the files it names, all inside
one bundle directory, so the whole artifact is inspectable:

    manifest.json       the bundle: format, version, agent, layers
    constitution.md     layer 1: standing instructions + identity
    skills/<name>/     layer 2: one skill folder per selected skill
    memory/own/         layer 3: the agent's own memory mount point
    memory/shared/      layer 3: the shared crew memory mount point
    grants.json         layer 4: capability grant (identity + actions)
    gateway-catalog.json  layer 5 source: gateway servers that exist
    brief.json          layer 6: environment brief, or the slot
                        naming OS-103 generation at launch
    changelog.md        the version's changelog pointer (OS-104)

Manifest shape (strict: unknown fields are rejected everywhere):

    {"format": "metaos-mind-image", "version": "1",
     "agent": {"nick": str, "identity": str},
     "constitution": "<relative file path>",
     "skills": ["<relative dir path>", ...],
     "memory_mount": {"own": "<relative dir path>",
                      "shared": "<relative dir path>" or null},
     "capability_grant": "<relative file path>",
     "tool_grants": ["<gateway server name>", ...],
     "environment_brief": {"file": "<relative file path>"}
                          or {"slot": "generated-at-launch"},
     "changelog": "<relative file path>"}

Resolution rules, all enforced by resolve_bundle():

- Every layer path is relative to the bundle directory and must
  stay inside it. Absolute paths and ".." escapes are refused.
- Constitution, changelog, capability grant, and brief file must
  be real files; skill and memory mount paths must be real
  directories. A missing layer is an error, never a guess.
- The capability grant file must parse as JSON with a non-empty
  identity string and a non-empty list of action strings.
- Tool grants resolve against a gateway catalog the caller
  supplies (a list of server names, or a mapping). With no
  catalog supplied the tool layer reports unresolved instead of
  claiming resolution: until the OS-058/059 gateway lands a real
  catalog, the example bundle ships its own declared catalog and
  the tests resolve against that. A grant naming a server the
  catalog does not list is an error.
- Secrets never enter an image (OS-012/OS-108): a layer file
  whose name carries "secret", "keyring", or a ".pem" suffix is
  refused outright.

Pure functions on text, dicts, and the local filesystem. No bus
posts, no network, no model calls.
"""

import json
import os
import re

FORMAT = "metaos-mind-image"
BRIEF_SLOT = "generated-at-launch"

_VERSION_RE = re.compile(r"^\d+(\.\d+)*$")
_SECRET_NAME_RE = re.compile(r"secret|keyring|\.pem$", re.IGNORECASE)

_TOP_FIELDS = {
    "format", "version", "agent", "constitution", "skills",
    "memory_mount", "capability_grant", "tool_grants",
    "environment_brief", "changelog",
}
_AGENT_FIELDS = {"nick", "identity"}
_MEMORY_FIELDS = {"own", "shared"}
_GRANT_FIELDS = {"identity", "actions", "notes"}


class BundleError(ValueError):
    """A bundle failed parsing or resolution; message names the fault."""


def _fail(msg):
    raise BundleError(msg)


def _require_str(obj, field, where):
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        _fail(f"{where}: {field!r} must be a non-empty string")
    return value


def _unknown_fields(obj, allowed, where):
    extra = sorted(set(obj) - allowed)
    if extra:
        _fail(f"{where}: unknown field(s): {', '.join(extra)}")


def _require_dict(obj, field, where):
    value = obj.get(field)
    if not isinstance(value, dict):
        _fail(f"{where}: {field!r} must be an object")
    return value


def parse_bundle(text):
    """Parse and strictly validate a bundle manifest JSON string.

    Returns the normalized bundle dict in manifest order. Raises
    BundleError on malformed JSON, wrong format, bad version, or
    any schema violation. Parsing alone checks shape, not files:
    use resolve_bundle() to prove every layer resolves.
    """
    try:
        bundle = json.loads(text)
    except (ValueError, TypeError) as exc:
        _fail(f"bundle: malformed JSON: {exc}")
    if not isinstance(bundle, dict):
        _fail("bundle: top level must be an object")
    _unknown_fields(bundle, _TOP_FIELDS, "bundle")
    for field in sorted(_TOP_FIELDS):
        if field not in bundle:
            _fail(f"bundle: missing field {field!r}")
    if bundle["format"] != FORMAT:
        _fail(f"bundle: format must be {FORMAT!r}")
    version = _require_str(bundle, "version", "bundle")
    if not _VERSION_RE.match(version):
        _fail("bundle: version must look like '1' or '1.2'")
    agent = _require_dict(bundle, "agent", "bundle")
    _unknown_fields(agent, _AGENT_FIELDS, "agent")
    _require_str(agent, "nick", "agent")
    _require_str(agent, "identity", "agent")
    _require_str(bundle, "constitution", "bundle")
    skills = bundle["skills"]
    if not isinstance(skills, list):
        _fail("bundle: 'skills' must be a list")
    for skill in skills:
        if not isinstance(skill, str) or not skill.strip():
            _fail("bundle: every skill path must be a non-empty string")
    if len(set(skills)) != len(skills):
        _fail("bundle: duplicate skill path")
    memory = _require_dict(bundle, "memory_mount", "bundle")
    _unknown_fields(memory, _MEMORY_FIELDS, "memory_mount")
    _require_str(memory, "own", "memory_mount")
    shared = memory.get("shared")
    if shared is not None and (not isinstance(shared, str)
                               or not shared.strip()):
        _fail("memory_mount: 'shared' must be a path string or null")
    _require_str(bundle, "capability_grant", "bundle")
    tools = bundle["tool_grants"]
    if not isinstance(tools, list):
        _fail("bundle: 'tool_grants' must be a list")
    for tool in tools:
        if not isinstance(tool, str) or not tool.strip():
            _fail("bundle: every tool grant must be a non-empty string")
    if len(set(tools)) != len(tools):
        _fail("bundle: duplicate tool grant")
    brief = _require_dict(bundle, "environment_brief", "bundle")
    if set(brief) not in ({"file"}, {"slot"}):
        _fail("environment_brief: exactly one of 'file' or 'slot'")
    if "file" in brief:
        _require_str(brief, "file", "environment_brief")
    elif brief["slot"] != BRIEF_SLOT:
        _fail(f"environment_brief: slot must be {BRIEF_SLOT!r}")
    _require_str(bundle, "changelog", "bundle")
    return bundle


def load_bundle(path):
    """Parse the manifest at path; returns (bundle, bundle_dir)."""
    with open(path, "r", encoding="utf-8") as handle:
        return parse_bundle(handle.read()), os.path.dirname(
            os.path.abspath(path))


def _inside(bundle_dir, relpath, where):
    """Resolve relpath inside bundle_dir, or return None with a reason.

    Returns (abspath, None) on success, (None, reason) when the path
    is absolute, escapes the bundle, or names a secret-bearing file.
    """
    if os.path.isabs(relpath):
        return None, f"{where}: absolute path refused: {relpath!r}"
    target = os.path.normpath(os.path.join(bundle_dir, relpath))
    if target != bundle_dir and not target.startswith(bundle_dir + os.sep):
        return None, f"{where}: path escapes the bundle: {relpath!r}"
    if _SECRET_NAME_RE.search(os.path.basename(target)):
        return None, (f"{where}: secrets never enter an image: "
                      f"{relpath!r}")
    return target, None


def _check_exists(target, want_dir, where, errors):
    if want_dir:
        if not os.path.isdir(target):
            errors.append(f"{where}: not a directory: {target}")
            return False
    elif not os.path.isfile(target):
        errors.append(f"{where}: not a file: {target}")
        return False
    return True


def resolve_bundle(bundle, bundle_dir, gateway_catalog=None):
    """Resolve every layer of a parsed bundle against the filesystem.

    gateway_catalog is a list (or mapping) of gateway server names
    the tool grants must come from; with none supplied, tool grants
    are reported as errors naming the missing catalog rather than
    claimed resolved.

    Returns {"layers": {...}, "errors": [...]}. "layers" maps each
    layer name to its resolved absolute path (or, for tool_grants,
    the granted server names, and for a slot brief, the slot name).
    An empty errors list means every layer resolved to a real source.
    """
    bundle_dir = os.path.abspath(bundle_dir)
    layers = {}
    errors = []

    def resolve_file(relpath, where, want_dir=False):
        target, reason = _inside(bundle_dir, relpath, where)
        if reason:
            errors.append(reason)
            return None
        if _check_exists(target, want_dir, where, errors):
            return target
        return None

    layers["constitution"] = resolve_file(
        bundle["constitution"], "constitution")
    skill_paths = []
    for skill in bundle["skills"]:
        target = resolve_file(skill, "skills", want_dir=True)
        if target:
            skill_paths.append(target)
    layers["skills"] = skill_paths
    memory = bundle["memory_mount"]
    layers["memory_own"] = resolve_file(
        memory["own"], "memory_mount.own", want_dir=True)
    layers["memory_shared"] = None
    if memory.get("shared") is not None:
        layers["memory_shared"] = resolve_file(
            memory["shared"], "memory_mount.shared", want_dir=True)
    grant_path = resolve_file(bundle["capability_grant"],
                              "capability_grant")
    layers["capability_grant"] = grant_path
    if grant_path:
        try:
            with open(grant_path, "r", encoding="utf-8") as handle:
                grant = json.load(handle)
        except (ValueError, OSError) as exc:
            errors.append(f"capability_grant: unreadable JSON: {exc}")
            grant = None
        if grant is not None:
            if not isinstance(grant, dict):
                errors.append("capability_grant: top level must be an object")
            else:
                extra = sorted(set(grant) - _GRANT_FIELDS)
                if extra:
                    errors.append("capability_grant: unknown field(s): "
                                  + ", ".join(extra))
                identity = grant.get("identity")
                if not isinstance(identity, str) or not identity.strip():
                    errors.append("capability_grant: 'identity' must be a "
                                  "non-empty string")
                actions = grant.get("actions")
                if (not isinstance(actions, list) or not actions
                        or any(not isinstance(a, str) or not a.strip()
                               for a in actions)):
                    errors.append("capability_grant: 'actions' must be a "
                                  "non-empty list of strings")
    tools = bundle["tool_grants"]
    if gateway_catalog is None:
        if tools:
            errors.append("tool_grants: no gateway catalog supplied, "
                          "grants unresolved: " + ", ".join(tools))
        layers["tool_grants"] = []
    else:
        known = (set(gateway_catalog) if not isinstance(gateway_catalog, dict)
                 else set(gateway_catalog))
        unknown = [tool for tool in tools if tool not in known]
        if unknown:
            errors.append("tool_grants: not in the gateway catalog: "
                          + ", ".join(unknown))
        layers["tool_grants"] = [tool for tool in tools if tool in known]
    brief = bundle["environment_brief"]
    if "file" in brief:
        layers["environment_brief"] = resolve_file(
            brief["file"], "environment_brief")
    else:
        layers["environment_brief"] = BRIEF_SLOT
    layers["changelog"] = resolve_file(bundle["changelog"], "changelog")
    layers = {key: value for key, value in layers.items()
              if value is not None or key in ("memory_shared",)}
    return {"layers": layers, "errors": errors}


def validate_bundle(bundle, bundle_dir, gateway_catalog=None):
    """Resolve and raise BundleError unless every layer resolves."""
    report = resolve_bundle(bundle, bundle_dir, gateway_catalog)
    if report["errors"]:
        _fail("bundle: unresolved layer(s): " + "; ".join(report["errors"]))
    return report


def bundle_summary(bundle, report=None):
    """One plain line naming the agent, version, and layer counts."""
    agent = bundle["agent"]
    skills = len(bundle["skills"])
    tools = len(bundle["tool_grants"])
    brief = bundle["environment_brief"]
    brief_text = ("brief slot " + BRIEF_SLOT if "slot" in brief
                  else "brief file")
    status = ""
    if report is not None:
        status = (" (all layers resolved)" if not report["errors"]
                  else " (UNRESOLVED: " + "; ".join(report["errors"]) + ")")
    return (f"{agent['nick']} mind image v{bundle['version']}: "
            f"constitution + {skills} skill(s) + {tools} tool grant(s) + "
            f"{brief_text}{status}")
