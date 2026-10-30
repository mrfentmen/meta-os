"""OS-083: workspace/artifact store (minimal), first light.

A git-backed versioned shared filesystem where dispatched jobs
deposit work products and reference them by path in the job
record, instead of pasting work products through chat. Layout
under a store root (default /var/lib/metaos/artifacts on the
image, baked by os/build-image.sh, os/build-live.sh, and the
Packer template as an empty directory plus a marker file):

    <root>/jobs/<job_id>/<artifact name>
    <root>/jobs/<job_id>/manifest.json

Every deposit is one git commit in the store repo: the artifact
file plus the job manifest, so the version history of a work
product is the git history of its path. Version numbers count
from 1 per artifact name. A redeposit of byte-identical content
is a no-op that returns the current version with no new commit:
git cannot commit an unchanged file, and inventing a version
for identical bytes would lie about the history.

Rules, all enforced here and pinned by tests:

- Names are relative paths below the job directory. Absolute
  paths, empty segments, "." and ".." segments, and NUL bytes
  are refused, so a deposit can never escape the store.
- Job ids are single path segments (letters, digits, dot,
  underscore, hyphen). A slash in a job id is refused.
- The store repo is created on first deposit with local-only
  git identity (config inside the repo, never global): the
  store identity commits, the depositing nick is recorded in
  the manifest and the commit message.
- Reading a version that does not exist raises, never guesses
  a neighboring version. Reading a job with no manifest
  returns an empty list, not an error: an empty store is a
  real state, not a failure.
- attach() never mutates its input record: it returns a copy
  whose "artifacts" list carries one entry per artifact, with
  the path a dashboard can link to and a reference of the
  form artifact:<job_id>/<name>@v<version>.

What this batch does NOT claim (stated plainly, as every
first-light batch in this repo does): no image build has run
from this tree in the sandbox, so deposits on a booted image
are unproven; no driver-executed job has deposited through
this module yet; jobs.py itself does not read or write the
store, so attaching artifact paths to a live job hash is
OS-094 work, not done here; and the dashboard links that
consume these paths are OS-084, also not done here. No bus
post, no live Redis, no network: deposits are local files
plus local git only.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

STORE_ROOT_DEFAULT = "/var/lib/metaos/artifacts"
MANIFEST_NAME = "manifest.json"


class ArtifactStoreError(ValueError):
    """Refused deposit, bad name, missing artifact, or git failure."""


def _git(root, args, input_text=None):
    """Run git inside the store root; git failures become errors."""
    if shutil.which("git") is None:
        raise ArtifactStoreError("git is not available on this machine")
    cmd = ["git", "-c", "safe.directory=*", "-C", root] + args
    try:
        proc = subprocess.run(
            cmd, input=input_text, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ArtifactStoreError("git failed: %s" % exc) from exc
    if proc.returncode != 0:
        raise ArtifactStoreError(
            "git %s failed: %s" % (args[0], proc.stderr.strip())
        )
    return proc.stdout


def _validate_job_id(job_id):
    if not isinstance(job_id, str) or not job_id:
        raise ArtifactStoreError("job id must be a non-empty string")
    bad = set("/\\") | {"\x00"}
    if any(ch in bad for ch in job_id) or job_id in (".", ".."):
        raise ArtifactStoreError("job id must be a single path segment")
    if not all(ch.isalnum() or ch in "._-" for ch in job_id):
        raise ArtifactStoreError("job id holds characters outside [A-Za-z0-9._-]")
    return job_id


def _validate_name(name):
    if not isinstance(name, str) or not name:
        raise ArtifactStoreError("artifact name must be a non-empty string")
    if name.startswith("/") or "\x00" in name or "\\" in name:
        raise ArtifactStoreError("artifact name must be a relative POSIX path")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ArtifactStoreError(
            "artifact name must not contain empty, . or .. segments"
        )
    return name


def _job_dir(root, job_id):
    return os.path.join(root, "jobs", _validate_job_id(job_id))


def _manifest_path(root, job_id):
    return os.path.join(_job_dir(root, job_id), MANIFEST_NAME)


def _read_manifest(root, job_id):
    path = _manifest_path(root, job_id)
    if not os.path.exists(path):
        return {"job_id": job_id, "artifacts": {}}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ArtifactStoreError("manifest unreadable: %s" % exc) from exc
    if not isinstance(data, dict) or not isinstance(data.get("artifacts"), dict):
        raise ArtifactStoreError("manifest has an unexpected shape")
    return data


def _write_manifest(root, job_id, manifest):
    path = _manifest_path(root, job_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def _ensure_repo(root):
    os.makedirs(root, exist_ok=True)
    if not os.path.isdir(os.path.join(root, ".git")):
        _git(root, ["init", "-q", "-b", "main"])
    return root


def _relpath(root, job_id, name):
    return os.path.join("jobs", job_id, name)


def deposit(root, job_id, name, data, author=""):
    """Deposit bytes (or str, encoded as UTF-8) as one version.

    Returns the manifest record for the artifact. A byte-identical
    redeposit returns the current record unchanged, with
    "new_commit" False; every other deposit commits and returns
    "new_commit" True.
    """
    job_id = _validate_job_id(job_id)
    name = _validate_name(name)
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not isinstance(data, (bytes, bytearray)):
        raise ArtifactStoreError("artifact data must be bytes or str")
    data = bytes(data)
    _ensure_repo(root)
    job_dir = _job_dir(root, job_id)
    os.makedirs(job_dir, exist_ok=True)
    manifest = _read_manifest(root, job_id)
    digest = hashlib.sha256(data).hexdigest()
    current = manifest["artifacts"].get(name)
    if current is not None and current.get("sha256") == digest:
        record = dict(current)
        record["new_commit"] = False
        return record
    target = os.path.join(job_dir, name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".tmp"
    with open(tmp, "wb") as handle:
        handle.write(data)
    os.replace(tmp, target)
    version = (current.get("version", 0) if current else 0) + 1
    record = {
        "name": name,
        "path": _relpath(root, job_id, name).replace(os.sep, "/"),
        "reference": "artifact:%s/%s@v%d" % (job_id, name, version),
        "version": version,
        "sha256": digest,
        "size": len(data),
        "author": author or "unknown",
        "deposited_at": int(time.time()),
    }
    manifest["job_id"] = job_id
    manifest["artifacts"][name] = record
    _write_manifest(root, job_id, manifest)
    rel_file = _relpath(root, job_id, name)
    rel_manifest = os.path.join("jobs", job_id, MANIFEST_NAME)
    _git(root, ["add", "--", rel_file, rel_manifest])
    _git(
        root,
        [
            "-c", "user.name=metaos-artifact-store",
            "-c", "user.email=artifact-store@metaos.local",
            "commit", "-q", "-m",
            "job %s: deposit %s v%d by %s"
            % (job_id, name, version, record["author"]),
        ],
    )
    record = dict(record)
    record["new_commit"] = True
    return record


def list_artifacts(root, job_id):
    """Manifest records for one job, sorted by artifact name."""
    job_id = _validate_job_id(job_id)
    manifest = _read_manifest(root, job_id)
    return [dict(manifest["artifacts"][k]) for k in sorted(manifest["artifacts"])]


def _version_commits(root, job_id, name):
    out = _git(root, ["log", "--format=%H", "--", _relpath(root, job_id, name)])
    return [line for line in out.splitlines() if line]


def read(root, job_id, name, version=None):
    """Artifact bytes: latest version, or one numbered version.

    A numbered version maps to its git commit, so a version read
    never depends on the current file on disk.
    """
    job_id = _validate_job_id(job_id)
    name = _validate_name(name)
    manifest = _read_manifest(root, job_id)
    current = manifest["artifacts"].get(name)
    if current is None:
        raise ArtifactStoreError(
            "no artifact %r for job %r" % (name, job_id)
        )
    if version is None:
        with open(os.path.join(_job_dir(root, job_id), name), "rb") as handle:
            return handle.read()
    if not isinstance(version, int) or version < 1:
        raise ArtifactStoreError("version must be a positive integer")
    commits = _version_commits(root, job_id, name)
    if version > len(commits):
        raise ArtifactStoreError(
            "artifact %r for job %r has %d versions, no v%d"
            % (name, job_id, len(commits), version)
        )
    commit = commits[len(commits) - version]
    # Binary-safe call (the text wrapper in _git would decode bytes).
    if shutil.which("git") is None:
        raise ArtifactStoreError("git is not available on this machine")
    try:
        proc = subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", root, "show",
             "%s:%s" % (commit, _relpath(root, job_id, name))],
            capture_output=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ArtifactStoreError("git show failed: %s" % exc) from exc
    if proc.returncode != 0:
        raise ArtifactStoreError("git show failed for version %d" % version)
    return proc.stdout


def history(root, job_id, name):
    """Version records, oldest first, from the artifact git log."""
    job_id = _validate_job_id(job_id)
    name = _validate_name(name)
    commits = _version_commits(root, job_id, name)
    return [
        {"version": idx + 1, "commit": commit}
        for idx, commit in enumerate(reversed(commits))
    ]


def attach(root, job_id, record):
    """Return a copy of a job record carrying its artifact paths.

    The input dict is never mutated. Each entry carries the path
    a dashboard can link to, the artifact reference, the version,
    and the sha256, so a reader can tell which version of the
    work product the job means.
    """
    job_id = _validate_job_id(job_id)
    if not isinstance(record, dict):
        raise ArtifactStoreError("job record must be a dict")
    out = dict(record)
    existing = list(record.get("artifacts", [])) if isinstance(
        record.get("artifacts"), list) else []
    for item in list_artifacts(root, job_id):
        existing.append(
            {
                "path": item["path"],
                "reference": item["reference"],
                "version": item["version"],
                "sha256": item["sha256"],
            }
        )
    out["artifacts"] = existing
    return out


def main(argv=None):
    """Minimal CLI: deposit, list, read, show. Errors exit 2."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(
            "usage: artifact_store deposit|list|read|show ROOT JOB [ARGS]",
            file=sys.stderr,
        )
        return 2
    cmd = argv[0]
    try:
        if cmd == "deposit" and len(argv) >= 5:
            root, job_id, name, path = argv[1], argv[2], argv[3], argv[4]
            author = ""
            if "--author" in argv[5:]:
                author = argv[argv.index("--author") + 1]
            with open(path, "rb") as handle:
                data = handle.read()
            record = deposit(root, job_id, name, data, author=author)
            print(json.dumps(record, sort_keys=True))
            return 0
        if cmd == "list" and len(argv) == 3:
            for item in list_artifacts(argv[1], argv[2]):
                print(json.dumps(item, sort_keys=True))
            return 0
        if cmd == "read" and len(argv) >= 4:
            version = None
            if "--version" in argv[4:]:
                version = int(argv[argv.index("--version") + 1])
            sys.stdout.buffer.write(read(argv[1], argv[2], argv[3], version))
            return 0
        if cmd == "show" and len(argv) == 4:
            for entry in history(argv[1], argv[2], argv[3]):
                print("v%(version)d %(commit)s" % entry)
            return 0
    except ArtifactStoreError as exc:
        print("ARTIFACT_STORE_ERROR: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print("ARTIFACT_STORE_ERROR: %s" % exc, file=sys.stderr)
        return 2
    print("usage: artifact_store deposit|list|read|show ROOT JOB [ARGS]",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
