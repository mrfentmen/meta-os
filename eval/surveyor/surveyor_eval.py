#!/usr/bin/env python3
"""Meta Surveyor eval upgrade — tests the AGENTIC WIRING from the spec,
not the demo mockups, and not real-world truth.

Spec under test: docs/META_SURVEYOR_SPEC.md (branch rowan/surveyor-spec).
Roles: S sensor, V verifier, H human-confirm. Rules encoded here:

1. Only a real sensor reading or a real photo publishes. Second-hand
   data (weather-station feed, satellite imagery) is labelled second-hand
   and NEVER counts toward the two-agent confirmation.
2. Publish needs two-agent confirmation: an S reading plus an
   independent V check — a second nearby reading, same time window,
   from a DIFFERENT device (ideally a different device class), that
   agrees within tolerance, with a sane sensor.
3. Disagreement -> unpublished + flagged for human check (role H).
4. Sensor-less devices never originate a sensor reading. A sensor
   dongle promotes an ordinary computer to role S; without one it
   stays role V (verification, atlas, clusters only).
5. Clusters, not single readings, trigger action: >= CLUSTER_MIN
   confirmed readings in one place/window make a cluster; dispatch
   happens ONLY on a confirmed cluster, never on one unverified blip.
6. Noise readings carry a decibel level ONLY — no audio is stored.
   A reading carrying audio is rejected outright.
7. No person data: a reading naming or identifying a person is
   rejected outright. Surveyor measures the environment, not people.

Honest caps, stated plainly:
- Every reading here is a FIXTURE. This harness proves the wiring
  rules hold on known inputs; it proves nothing about any real street,
  sensor, cure, or compound.
- NO live model calls, NO live sensors, NO network. Model cost for
  this harness is $0; any future model-backed verifier runs Mac-side
  under del's under-a-dollar cap, never from this harness.
- A 100% fixture pass is a wiring pass, not a science result.

Run: python3 surveyor_eval.py  (prints a scenario table, exit 0 on
all-pass, exit 1 otherwise). Unit tests live in test_surveyor_eval.py.
Python 3 stdlib only.
"""

import json
import sys

CLUSTER_MIN = 3
TIME_WINDOW_MIN = 60
# Plausible ranges per field (sanity, not science): value outside the
# range means the sensor is not sane and the reading cannot confirm.
FIELD_RANGE = {
    "heat": (-50.0, 60.0),        # Celsius
    "air": (0.0, 1000.0),         # PM2.5 ug/m3, generous ceiling
    "flood": (0.0, 20.0),         # water metres above datum
    "noise": (0.0, 140.0),        # decibels
}
# Agreement tolerance per field for the second-agent check.
FIELD_TOLERANCE = {"heat": 2.0, "air": 25.0, "flood": 0.25, "noise": 5.0}


class Rejected(Exception):
    """A reading that must never enter the pipeline at all."""


def check_reading_shape(reading):
    """Reject readings that break the spec's hard rules outright."""
    if reading.get("audio") is not None:
        raise Rejected("noise reading carries audio; decibel level only")
    if reading.get("person") is not None:
        raise Rejected("reading carries person data; environment only")
    if reading.get("source") not in ("sensor", "photo", "second-hand"):
        raise Rejected("unknown source %r" % (reading.get("source"),))
    if reading.get("field") not in FIELD_RANGE:
        raise Rejected("unknown field %r" % (reading.get("field"),))
    if reading.get("role") not in ("S", "V", "H"):
        raise Rejected("unknown role %r" % (reading.get("role"),))
    # A sensor-less device cannot originate a sensor reading. A dongle
    # promotes it (has_sensors True after promotion); without one it
    # is role V and may only verify, never sense.
    if reading.get("source") == "sensor" and not reading.get("has_sensors"):
        raise Rejected("sensor-less device cannot originate a sensor reading")
    return True


def sensor_sane(reading, history):
    """Sanity: in range, and not a stuck sensor repeating one value."""
    lo, hi = FIELD_RANGE[reading["field"]]
    value = reading["value"]
    if not (lo <= value <= hi):
        return False
    same_device = [h for h in history
                   if h["device_id"] == reading["device_id"]
                   and h["field"] == reading["field"]]
    if len(same_device) >= 2 and all(h["value"] == value
                                     for h in same_device[-2:]):
        return False  # stuck sensor: same value three times running
    return True


def agrees(a, b):
    """Second-agent agreement: different device, same place/window,
    values within tolerance."""
    if a["device_id"] == b["device_id"]:
        return False
    if a["place"] != b["place"]:
        return False
    if abs(a["time_min"] - b["time_min"]) > TIME_WINDOW_MIN:
        return False
    return abs(a["value"] - b["value"]) <= FIELD_TOLERANCE[a["field"]]


def evaluate(readings):
    """Run the pipeline over a list of readings.

    Returns a dict: published, unpublished, flagged_for_human, clusters,
    dispatched. Second-hand readings never publish and never confirm.
    Rejected readings (audio payload, person data, sensor-less sensing)
    never enter the pipeline, never confirm anything else, and are
    flagged for review along with unconfirmed readings.
    """
    published, unpublished, flagged = [], [], []
    confirmed = []
    valid = []
    for reading in readings:
        try:
            check_reading_shape(reading)
        except Rejected as exc:
            unpublished.append((reading, "rejected: %s" % exc))
            flagged.append(reading)
            continue
        valid.append(reading)
    for reading in valid:
        if reading["source"] == "second-hand":
            unpublished.append((reading, "second-hand never publishes"))
            continue
        peers = [r for r in valid
                 if r is not reading
                 and r.get("source") in ("sensor", "photo")
                 and r.get("field") == reading["field"]
                 and agrees(reading, r)]
        if peers and sensor_sane(reading, valid):
            # The confirming peer must itself be sane too.
            if any(sensor_sane(p, valid) for p in peers):
                published.append(reading)
                confirmed.append(reading)
                continue
        unpublished.append((reading, "no independent agreement"))
        flagged.append(reading)
    # Clusters: >= CLUSTER_MIN confirmed readings, same field+place.
    clusters = []
    for field in FIELD_RANGE:
        for place in sorted({r["place"] for r in confirmed
                             if r["field"] == field}):
            group = [r for r in confirmed
                     if r["field"] == field and r["place"] == place]
            if len(group) >= CLUSTER_MIN:
                clusters.append({"field": field, "place": place,
                                 "count": len(group)})
    dispatched = [dict(c, action="dispatch-on-confirmed-cluster")
                  for c in clusters]
    return {"published": published, "unpublished": unpublished,
            "flagged_for_human": flagged, "clusters": clusters,
            "dispatched": dispatched}


def base_reading(**over):
    reading = {"field": "heat", "value": 34.0, "source": "sensor",
               "role": "S", "device_id": "phone-1", "device_class": "phone",
               "place": "block-A", "time_min": 100, "has_sensors": True}
    reading.update(over)
    return reading


SCENARIOS = [
    ("two-agent-confirm-publishes",
     [base_reading(), base_reading(device_id="node-2", device_class="node",
                                   value=34.8, time_min=110)],
     {"published": 2, "flagged": 0}),
    ("single-reading-never-publishes",
     [base_reading()],
     {"published": 0, "flagged": 1}),
    ("disagreement-flags-for-human",
     [base_reading(),
      base_reading(device_id="node-2", device_class="node",
                   value=41.0, time_min=110)],
     {"published": 0, "flagged": 2}),
    ("second-hand-never-counts",
     [base_reading(),
      base_reading(device_id="feed-1", device_class="feed",
                   source="second-hand", value=34.5, time_min=110)],
     # second-hand row itself is stored labelled, not flagged; the
     # sensor row is flagged awaiting independent confirmation.
     {"published": 0, "flagged": 1}),
    ("sensorless-device-cannot-sense",
     [base_reading(has_sensors=False),
      base_reading(device_id="node-2", device_class="node",
                   value=34.8, time_min=110)],
     {"published": 0, "flagged": 2}),
    ("dongle-promotes-to-sensor",
     [base_reading(has_sensors=True, device_class="desktop+dongle"),
      base_reading(device_id="node-2", device_class="node",
                   value=34.8, time_min=110)],
     {"published": 2, "flagged": 0}),
    ("same-device-does-not-confirm-itself",
     [base_reading(),
      base_reading(value=34.5, time_min=110)],
     {"published": 0, "flagged": 2}),
    ("out-of-range-sensor-not-sane",
     [base_reading(value=120.0),
      base_reading(device_id="node-2", device_class="node",
                   value=120.0, time_min=110)],
     {"published": 0, "flagged": 2}),
    ("audio-payload-rejected",
     [base_reading(field="noise", value=72.0, audio="clip-bytes"),
      base_reading(field="noise", device_id="node-2",
                   device_class="node", value=71.0, time_min=110)],
     {"published": 0, "flagged": 2}),
    ("person-data-rejected",
     [base_reading(person="named individual"),
      base_reading(device_id="node-2", device_class="node",
                   value=34.8, time_min=110)],
     {"published": 0, "flagged": 2}),
    ("cluster-dispatches-only-on-confirmed-cluster",
     [base_reading(device_id="d%d" % i, device_class="node",
                   value=34.0 + 0.3 * i, time_min=100 + 5 * i)
      for i in range(3)] +
     [base_reading(device_id="solo", device_class="node",
                   place="block-B", value=34.0, time_min=100)],
     {"published": 3, "flagged": 1, "clusters": 1, "dispatched": 1}),
]


def run_scenarios():
    rows = []
    for name, readings, want in SCENARIOS:
        result = evaluate(readings)
        got = {"published": len(result["published"]),
               "flagged": len(result["flagged_for_human"]),
               "clusters": len(result["clusters"]),
               "dispatched": len(result["dispatched"])}
        ok = all(got[k] == v for k, v in want.items())
        rows.append((name, ok, got, want))
    return rows


def main():
    rows = run_scenarios()
    passed = sum(1 for _, ok, _, _ in rows if ok)
    for name, ok, got, want in rows:
        print("%-46s %s got=%s want(subset)=%s"
              % (name, "PASS" if ok else "FAIL",
                 json.dumps(got, sort_keys=True),
                 json.dumps(want, sort_keys=True)))
    print("surveyor eval: %d/%d scenarios pass; model cost $0; "
          "fixtures only, no live sensors, no live model calls"
          % (passed, len(rows)))
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
