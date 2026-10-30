#!/usr/bin/env python3
"""meta join (OS-110): one command joins a Meta OS machine to a room.

The join flow, per plan/META_OS.md ("Federation: many machines, one
crew"):

1. The machine records the room address + room key in chmod-600 files
   under a config dir (default /etc/metaos on the image). The key
   lives in its own file, never in the image, never in the room
   announcement, never in any log line this module prints.
2. The machine announces itself on the room: machine name, its crew
   nicks, each agent's mind-image version and capability badge (the
   OS-080 identity layer). The announcement is built here; it is
   posted through a caller-supplied poster, so this module itself
   never touches the network and no test ever posts to a live room.
3. Claiming after the join follows the local trust settings: the
   join writes an explicit trust list (plan/META_OS.md default
   posture is closed), so a fresh machine trusts no foreign crew
   until its owner adds one. The trust file shape matches
   intel/trust.py claim_decision: {"trusted_kids": [...]}.

Usage (on the image, after firstboot collected the secrets):

  python3 intel/join.py --machine dales-laptop --post

With no flags, address/key/machine resolve from the config dir:
address from <config>/secrets.env (MUSE_RELAY_URL, written by
firstboot), key from <config>/token (written by firstboot), machine
from <config>/machine (written by firstboot's room step). Each can
be overridden: --room-address, --room-key-file, --machine.

Without --post the command writes the config, prints the
announcement, and posts nothing; --announce-out writes the
announcement JSON to a file for the operator's poster. With --post
the CLI posts the announcement through relay_common (the same bus
path send.py uses) to the room given by --room. --post is an
operator action on the image, never something build code runs:
no test in this repo posts to a live room.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from intel import capability_files  # noqa: E402


class JoinError(ValueError):
    """A join input or config problem. Never carries the room key."""


_MACHINE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_BADGE_FIELDS = ("bus_post", "spend", "network", "write_paths")

# Config file names inside the config dir. The key file holds the
# room key alone; the env file holds the address + machine name.
ENV_FILE = "room.env"
KEY_FILE = "room.key"
TRUST_FILE = "trust.json"
TOKEN_FILE = "token"
SECRETS_FILE = "secrets.env"
MACHINE_FILE = "machine"


def validate_machine(machine):
    """Return the machine name, or raise JoinError.

    Machine names go on the room announcement, so they must be one
    clean token: no whitespace, no slashes, no control characters.
    """
    if not isinstance(machine, str) or not machine:
        raise JoinError("machine: a machine name is required")
    if not _MACHINE_RE.match(machine):
        raise JoinError(
            "machine: %r is not a machine name "
            "(letters, digits, dot, underscore, hyphen only)" % machine)
    return machine


def validate_room_address(address):
    """Return the room address, or raise JoinError.

    The address is the Upstash REST endpoint firstboot collects: an
    https URL with no userinfo. Credentials in the address itself
    are refused, because the address is printed and stored beside
    non-secret config.
    """
    if not isinstance(address, str) or not address.strip():
        raise JoinError("room address: an address is required")
    if any(ch.isspace() for ch in address):
        raise JoinError("room address: whitespace is not allowed")
    parts = urllib.parse.urlsplit(address)
    if parts.scheme != "https" or not parts.netloc:
        raise JoinError(
            "room address: expected an https URL, got %r" % address)
    if parts.username is not None or parts.password is not None:
        raise JoinError(
            "room address: userinfo is not allowed in the address; "
            "the key goes in the key file")
    return address


def validate_room_key(key):
    """Return the room key, or raise JoinError.

    One trailing newline is stripped (key files written by printf
    carry none, but a text editor may add one); any other newline
    or an empty key is refused.
    """
    if not isinstance(key, str):
        raise JoinError("room key: a key is required")
    if key.endswith("\n"):
        key = key[:-1]
    if not key or "\n" in key or "\r" in key:
        raise JoinError("room key: empty or multi-line keys are refused")
    return key


def validate_trusted_kids(trusted):
    """Return the trusted-kid list, or raise JoinError.

    An empty list is valid and is the default-closed posture: a
    fresh machine trusts no foreign crew. Duplicates are refused
    rather than silently deduped, because a duplicated kid is a
    caller mistake worth surfacing.
    """
    if trusted is None:
        return []
    if isinstance(trusted, str) or not hasattr(trusted, "__iter__"):
        raise JoinError("trusted kids: expected a list of kid names")
    kids = list(trusted)
    for kid in kids:
        if not isinstance(kid, str) or not kid:
            raise JoinError("trusted kids: kid names must be non-empty")
    if len(set(kids)) != len(kids):
        raise JoinError("trusted kids: duplicate kid names refused")
    return kids


def crew_from_grants(grants, versions=None):
    """Build the announcement crew list from OS-080 grants.

    grants maps identity to a validated grant dict (see
    intel/capability_files.load_crew_grants). versions maps nick to
    mind-image version; a nick with no recorded version is announced
    as "unrecorded", never with an invented version. A version entry
    for a nick with no grant is ignored: grants are the authority
    on who the crew is. The badge carries only the four grant
    fields, copied, so later grant edits cannot leak into an
    announcement built earlier.
    """
    if not isinstance(grants, dict) or not grants:
        raise JoinError("crew: no capability grants supplied")
    versions = versions or {}
    if not isinstance(versions, dict):
        raise JoinError("versions: expected a nick-to-version mapping")
    crew = []
    for nick in sorted(grants):
        grant = grants[nick]
        if not isinstance(grant, dict):
            raise JoinError("crew: grant for %r is not a mapping" % nick)
        version = versions.get(nick, "unrecorded")
        if not isinstance(version, str) or not version:
            raise JoinError(
                "crew: mind-image version for %r must be a non-empty "
                "string" % nick)
        badge = {}
        for field in _BADGE_FIELDS:
            value = grant.get(field)
            if isinstance(value, list):
                value = list(value)
            badge[field] = value
        crew.append({"nick": nick,
                     "mind_image_version": version,
                     "badge": badge})
    return crew


def build_announcement(machine, crew, joined_at=None):
    """Build the machine-join announcement record.

    crew is the list crew_from_grants returns. The record carries no
    key material of any kind: it is safe to print, store, and post.
    Duplicate nicks are refused; the crew is sorted by nick so the
    record is deterministic for a given crew.
    """
    machine = validate_machine(machine)
    if not isinstance(crew, list) or not crew:
        raise JoinError("announcement: the crew list is empty")
    seen = set()
    for member in crew:
        if not isinstance(member, dict):
            raise JoinError("announcement: crew members must be mappings")
        nick = member.get("nick")
        if not isinstance(nick, str) or not nick:
            raise JoinError("announcement: crew members need a nick")
        if nick in seen:
            raise JoinError("announcement: duplicate crew nick %r" % nick)
        seen.add(nick)
        if not isinstance(member.get("mind_image_version"), str) \
                or not member.get("mind_image_version"):
            raise JoinError(
                "announcement: %r needs a mind-image version" % nick)
        if not isinstance(member.get("badge"), dict):
            raise JoinError("announcement: %r needs a badge mapping" % nick)
    if joined_at is None:
        joined_at = int(time.time())
    if not isinstance(joined_at, int) or joined_at < 0:
        raise JoinError("announcement: joined_at must be a unix time")
    ordered = sorted(crew, key=lambda m: m["nick"])
    return {"kind": "machine-join",
            "machine": machine,
            "crew": ordered,
            "joined_at": joined_at}


def announcement_text(announcement):
    """Render an announcement as plain lines for the room/operator."""
    lines = ["JOIN %s" % announcement["machine"]]
    for member in announcement["crew"]:
        badge = member["badge"]
        lines.append(
            "  %s mind-image %s badge bus_post=%s spend=%s network=%s "
            "write=%s" % (
                member["nick"], member["mind_image_version"],
                badge.get("bus_post"), badge.get("spend"),
                badge.get("network"),
                ",".join(badge.get("write_paths") or []) or "-"))
    return "\n".join(lines) + "\n"


def post_announcement(announcement, post_fn):
    """Deliver an announcement through a caller-supplied poster.

    post_fn takes the announcement JSON string and returns whatever
    the transport returns. This module performs no I/O itself, so
    tests post into a fake room and no build code ever touches a
    live room.
    """
    if not callable(post_fn):
        raise JoinError("post: a callable poster is required")
    body = json.dumps(announcement, sort_keys=True)
    return post_fn(body)


def _write_0600(path, content):
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, 0o600)


def write_room_config(config_dir, room_address, room_key, machine,
                      trusted_kids=(), force=False):
    """Write the join config files. Returns the paths written.

    Files: room.env (address + machine), room.key (key alone),
    trust.json ({"trusted_kids": [...]}, empty by default: closed).
    Existing files are refused unless force is given, so a second
    join never silently overwrites a machine's room. The key is
    verified absent from room.env and trust.json after the write.
    """
    address = validate_room_address(room_address)
    key = validate_room_key(room_key)
    machine = validate_machine(machine)
    kids = validate_trusted_kids(trusted_kids)
    os.makedirs(config_dir, exist_ok=True)
    os.chmod(config_dir, 0o700)
    paths = {name: os.path.join(config_dir, name)
             for name in (ENV_FILE, KEY_FILE, TRUST_FILE)}
    if not force:
        for name, path in paths.items():
            if os.path.exists(path):
                raise JoinError(
                    "config: %s already exists; re-run with --force "
                    "to overwrite it" % path)
    _write_0600(paths[ENV_FILE],
                "MUSE_RELAY_URL=%s\nMETAOS_MACHINE=%s\n" % (address,
                                                            machine))
    _write_0600(paths[TRUST_FILE],
                json.dumps({"trusted_kids": kids}, sort_keys=True) + "\n")
    _write_0600(paths[KEY_FILE], key)
    with open(paths[ENV_FILE]) as f:
        env_text = f.read()
    if key in env_text:
        raise JoinError("config: room key leaked into %s" % ENV_FILE)
    with open(paths[TRUST_FILE]) as f:
        trust_back = json.load(f)
    if trust_back != {"trusted_kids": kids}:
        raise JoinError("config: trust file did not round-trip")
    return paths


def _read_single_line_file(path):
    with open(path) as f:
        text = f.read()
    return text[:-1] if text.endswith("\n") else text


def _read_env_file(path):
    values = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip()
    return values


def resolve_join_inputs(config_dir, room_address=None, room_key_file=None,
                        machine=None):
    """Resolve address/key/machine from flags or config-dir files.

    Flag wins; otherwise address comes from <config>/secrets.env
    (MUSE_RELAY_URL, written by firstboot), the key from
    <config>/token (written by firstboot), and the machine name from
    <config>/machine (written by firstboot's room step). Anything
    still missing is a JoinError naming what to supply.
    """
    address = room_address
    if address is None:
        secrets = os.path.join(config_dir, SECRETS_FILE)
        if os.path.isfile(secrets):
            address = _read_env_file(secrets).get("MUSE_RELAY_URL")
    key = None
    key_path = room_key_file or os.path.join(config_dir, TOKEN_FILE)
    if os.path.isfile(key_path):
        key = _read_single_line_file(key_path)
    name = machine
    if name is None:
        machine_path = os.path.join(config_dir, MACHINE_FILE)
        if os.path.isfile(machine_path):
            name = _read_single_line_file(machine_path)
    if address is None:
        raise JoinError(
            "join: no room address; pass --room-address or run "
            "firstboot so %s exists" % SECRETS_FILE)
    if key is None:
        raise JoinError(
            "join: no room key; pass --room-key-file or run "
            "firstboot so %s exists" % TOKEN_FILE)
    if name is None:
        raise JoinError(
            "join: no machine name; pass --machine or set it at "
            "firstboot so %s exists" % MACHINE_FILE)
    return (validate_room_address(address), validate_room_key(key),
            validate_machine(name))


def _load_versions(path):
    if path is None:
        return {}
    with open(path) as f:
        versions = json.load(f)
    if not isinstance(versions, dict):
        raise JoinError("mind-images: expected a nick-to-version mapping")
    return versions


def _post_via_relay(body, room, config_dir):
    """Post an announcement through relay_common (operator action).

    The import is lazy and the env is set from the just-written
    config, so importing this module never touches the network or
    the operator's environment.
    """
    os.environ["MUSE_RELAY_URL"] = _read_env_file(
        os.path.join(config_dir, ENV_FILE))["MUSE_RELAY_URL"]
    os.environ["MUSE_RELAY_TOKEN_FILE"] = os.path.join(config_dir,
                                                       KEY_FILE)
    import relay_common as rc
    return rc.bus_push(body, key=rc.bus_key(room))


def main(argv=None):
    """CLI entry point. Returns a process exit code, never raises."""
    parser = argparse.ArgumentParser(
        description="Join this machine to a Meta OS room (OS-110).")
    parser.add_argument("--config-dir", default="/etc/metaos")
    parser.add_argument("--room-address")
    parser.add_argument("--room-key-file")
    parser.add_argument("--machine")
    parser.add_argument("--room", default="",
                        help="room name for --post (default: main bus)")
    parser.add_argument("--capabilities-dir",
                        default=capability_files.shipped_directory())
    parser.add_argument("--mind-images",
                        help="JSON file mapping nick to mind-image "
                        "version; nicks without one announce unrecorded")
    parser.add_argument("--trust", action="append", default=[],
                        help="trusted signing kid (repeatable; default: "
                        "none, the closed posture)")
    parser.add_argument("--announce-out",
                        help="write the announcement JSON to this file")
    parser.add_argument("--post", action="store_true",
                        help="post the announcement to the room now "
                        "(operator action on the image only)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing config files")
    args = parser.parse_args(argv)
    try:
        address, key, machine = resolve_join_inputs(
            args.config_dir, args.room_address, args.room_key_file,
            args.machine)
        grants, errors = capability_files.load_crew_grants(
            args.capabilities_dir)
        if errors:
            raise JoinError("crew grants: %s" % "; ".join(
                "%s: %s" % (e["file"], e["reason"]) for e in errors))
        crew = crew_from_grants(grants, _load_versions(args.mind_images))
        announcement = build_announcement(machine, crew)
        write_room_config(args.config_dir, address, key, machine,
                          trusted_kids=args.trust, force=args.force)
        text = announcement_text(announcement)
        sys.stdout.write(text)
        if args.announce_out:
            with open(args.announce_out, "w") as f:
                f.write(json.dumps(announcement, sort_keys=True) + "\n")
        if args.post:
            body = json.dumps(announcement, sort_keys=True)
            resp = _post_via_relay(body, args.room, args.config_dir)
            sys.stdout.write("POSTED %s: %s\n" % (
                args.room or "main", (resp or "").strip()))
    except (JoinError, ValueError, OSError) as exc:
        sys.stderr.write("join: %s\n" % exc)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
