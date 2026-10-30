"""crew_records.py — the crew's durable records (the audit trail).

Everything the agent crew does lands here, append-only:

  incidents.json    one record per incident, keyed by incident id.
                    A record is created once and afterwards only
                    GROWS: its `timeline` list accepts appends and
                    nothing else — no step is ever edited or removed,
                    and the step-writing API below exposes append as
                    the only mutation. Status fields move forward
                    (flagged -> reported -> dispatched-simulated, or
                    -> cleared-by-review) alongside the timeline step
                    that records the same transition.
  events.jsonl      the crew event feed the status endpoint serves:
                    one JSON object per line, appended, never
                    rewritten (patrol checks, flags, review verdicts,
                    incident reports, investigation runs, dispatch
                    receipts, patrol pause/resume notices).
  dispatches.jsonl  the SIMULATED dispatch log: one line per package
                    the simulated dispatch endpoint accepted.
  crew-status.json  the patrol heartbeat snapshot (rewritten each
                    cycle — a status, not a record).

Data directory: TRIO_CREW_DATA_DIR when set, else `crew-data/`
beside this module. The app server's read-only status endpoint
(server/crew-status.mjs) reads the same directory.
"""
import json
import os
import threading

QUEUE_DIR = os.path.dirname(os.path.abspath(__file__))


def data_dir():
    return os.environ.get("TRIO_CREW_DATA_DIR") or os.path.join(
        QUEUE_DIR, "crew-data")


class CrewRecords:
    def __init__(self, directory=None):
        self.dir = directory or data_dir()
        os.makedirs(self.dir, exist_ok=True)
        self._lock = threading.Lock()
        self._incidents_path = os.path.join(self.dir, "incidents.json")
        self._events_path = os.path.join(self.dir, "events.jsonl")
        self._dispatches_path = os.path.join(self.dir, "dispatches.jsonl")
        self._status_path = os.path.join(self.dir, "crew-status.json")

    # -- incidents -----------------------------------------------------

    def _load_incidents(self):
        if os.path.exists(self._incidents_path):
            with open(self._incidents_path) as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        return {}

    def _save_incidents(self, incidents):
        tmp = self._incidents_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(incidents, f, indent=1)
        os.replace(tmp, self._incidents_path)

    def create_incident(self, record):
        """File a new incident record. Refuses to overwrite an
        existing id — a second create for the same incident is a
        bug, not an update."""
        with self._lock:
            incidents = self._load_incidents()
            if record["id"] in incidents:
                raise ValueError(
                    f"incident {record['id']} already recorded")
            record = dict(record)
            record.setdefault("timeline", [])
            incidents[record["id"]] = record
            self._save_incidents(incidents)
            return record

    def append_timeline(self, incident_id, step):
        """THE mutation for incident records: append one step to the
        timeline. Steps are never edited or removed. A status carried
        on the step (step["status"]) also advances the record's
        status field — recorded in the same append, so the status
        history IS the timeline."""
        with self._lock:
            incidents = self._load_incidents()
            record = incidents.get(incident_id)
            if record is None:
                raise KeyError(f"no incident {incident_id}")
            record["timeline"].append(step)
            if step.get("status"):
                record["status"] = step["status"]
            self._save_incidents(incidents)
            return record

    def get_incident(self, incident_id):
        with self._lock:
            return self._load_incidents().get(incident_id)

    def list_incidents(self):
        with self._lock:
            incidents = self._load_incidents()
        return sorted(incidents.values(),
                      key=lambda r: r.get("created_at", ""), reverse=True)

    def open_incidents(self):
        """Incidents still live for patrol prioritization: anything
        not closed by review or by a simulated dispatch."""
        return [r for r in self.list_incidents()
                if r.get("status") in ("flagged", "reported",
                                       "investigating")]

    # -- event feed ------------------------------------------------------

    def append_event(self, event):
        with self._lock:
            with open(self._events_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        return event

    def recent_events(self, limit=60):
        return _tail_jsonl(self._events_path, limit)

    # -- simulated dispatch log ------------------------------------------

    def append_dispatch(self, package):
        with self._lock:
            with open(self._dispatches_path, "a") as f:
                f.write(json.dumps(package) + "\n")
        return package

    def recent_dispatches(self, limit=20):
        return _tail_jsonl(self._dispatches_path, limit)

    # -- patrol heartbeat ---------------------------------------------------

    def write_status(self, status):
        with self._lock:
            tmp = self._status_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(status, f, indent=1)
            os.replace(tmp, self._status_path)
        return status

    def read_status(self):
        if os.path.exists(self._status_path):
            with open(self._status_path) as f:
                return json.load(f)
        return None


def _tail_jsonl(path, limit):
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue  # a torn final line is skipped, never fatal
    return out[-limit:]
