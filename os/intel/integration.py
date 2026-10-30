"""Integration environment for Relay Intelligence (INT-001).

A second crew member reproduces this environment from the
intel/README.md section alone: one room, one job namespace, one
capability namespace, all disjoint from the production bus and the
default namespaces. Nothing here touches the live bus, posts a job,
or holds a secret: the values are key prefixes and a room name.

Import-order rule (load-bearing): jobs.py reads MUSE_RELAY_JOBNS
into jobs.NS at import time, and mos/capabilities.py reads
MUSE_RELAY_CAPNS into capabilities.CAPNS at import time. Setting the
variables after those modules are imported does nothing to the
already-read prefixes. Set them first (apply_env, or the export
block in the README), then import. The subprocess test in
tests/test_intel_integration.py pins this: with the variables set
before import, jobs.NS and capabilities.CAPNS carry the integration
prefixes; without them, they carry the production defaults.

Importing this module has no side effects: no network, no Redis,
no env writes. apply_env is the only function that touches
os.environ, and it is called explicitly.
"""

import os
import shlex

# The integration room: announcements for integration jobs land on
# muse-bus:room:build-int (relay_common.bus_key), never on muse-bus.
INT_ROOM = "build-int"

# Integration key prefixes. Deliberately disjoint from the defaults
# (muse-bus:job, muse-bus:cap) and from the test-suite prefixes
# (muse-bus:tjob, muse-bus:tcap), so an integration run, a unit-test
# run, and a production run can never read each other's state.
INT_JOBNS = "muse-bus:int-job"
INT_CAPNS = "muse-bus:int-cap"

INT_ENV_VARS = ("MUSE_RELAY_JOBNS", "MUSE_RELAY_CAPNS",
                "MUSE_RELAY_INTEL_ROOM")


def env_for(room=INT_ROOM, jobns=INT_JOBNS, capns=INT_CAPNS):
    """Return the integration environment mapping for the given values.

    Defaults are the INT_* constants above. Callers that need a
    second parallel environment pass explicit values; nothing here
    guesses a namespace from the caller's environment.
    """
    return {
        "MUSE_RELAY_JOBNS": jobns,
        "MUSE_RELAY_CAPNS": capns,
        "MUSE_RELAY_INTEL_ROOM": room,
    }


def export_lines(env=None):
    """Return shell `export KEY='value'` lines for the environment.

    Values are shlex-quoted, so pasting the block into a shell sets
    exactly these values. The README section reproduces this block
    verbatim for the defaults; the test pins the two to each other.
    """
    mapping = env_for() if env is None else dict(env)
    return ["export %s=%s" % (key, shlex.quote(mapping[key]))
            for key in INT_ENV_VARS]


def apply_env(env=None):
    """Set the integration variables in this process and return them.

    Call before importing jobs or mos.capabilities (see the module
    docstring). Returns the mapping that was applied.
    """
    mapping = env_for() if env is None else dict(env)
    os.environ.update(mapping)
    return mapping


def room_bus_key(room=INT_ROOM):
    """Return the Redis bus key for the integration room.

    Delegates to relay_common.bus_key so the room mapping has exactly
    one definition; the import is lazy so importing this module
    stays side-effect free.
    """
    from relay_common import bus_key
    return bus_key(room)
