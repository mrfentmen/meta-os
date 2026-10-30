"""intel/skills_loader.py -- OS-065 (Pax): the skills loader.

Dale's skills collections become installable OS applications: the
loader mounts skill folders into an agent process's launch
environment the way an OS loads apps for a user session. A
process started from a mounted launch directory begins with its
skills already present, not pasted in by hand mid-session.

A skills collection is a directory whose immediate subdirectories
are skill apps. A skill app mounts only when it carries a SKILL.md
at its root: a folder without one is not a mountable app and is
never mounted. Listing reports mountable skills only; mounting
by name refuses an unmountable folder loudly instead of skipping
it quietly, so a misspelled or half-written skill can never look
like a successful mount.

Mount rules, all enforced by mount_skills() and mount_skill_dirs():

- Names are plain basenames. A name with a separator, a dotdot,
  or an empty name is refused: no mount can address a path
  outside the collection or the launch directory.
- Mount names must be unique: two skills with the same folder
  name cannot share one launch directory.
- A skill folder, and every symlink inside it, must resolve
  inside its own root. An escape is refused before anything is
  copied.
- Only the named skills mount. Folders the caller did not name
  are never copied, and verify_mount() reports any extra skill
  directory found under skills/ as an error.
- A mount is a verbatim copy: every file under the skill folder
  lands byte-identical, and skills.json records the sha256 of
  every mounted file so a launched process, or a later check,
  can prove which skills are active and that they are intact.
- Mounting over an existing mount is refused: one launch never
  silently mixes with another.

Pure filesystem functions. No bus posts, no network, no model
calls, no process spawning: this module builds the environment
a process starts from, it does not start the process. A driver
process showing a mounted skill active in its first action, and
the unmounted control run that does not, are OS-055 integration
proof, not something claimed here. The OS-102 mind loader mounts
its bundle skills through mount_skill_dirs(), so the bundle path
and the collection path share this one rule instead of two.
"""

import hashlib
import json
import os
import shutil
import sys

MANIFEST_NAME = "skills.json"
MANIFEST_FORMAT = "metaos-skills-mount"
SKILL_DOC = "SKILL.md"


class SkillsLoaderError(ValueError):
    """A skills load failed; the message names the fault."""


def _fail(msg):
    raise SkillsLoaderError(msg)


def _sha256_file(path):
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
            hashes[rel] = _sha256_file(full)
    return hashes


def _validate_name(name):
    if not isinstance(name, str) or not name:
        _fail("skill: name must be a non-empty string")
    if name in (".", ".."):
        _fail(f"skill: invalid mount name: {name!r}")
    if os.path.basename(name) != name or os.path.sep in name:
        _fail(f"skill: mount name must be a plain basename: {name!r}")
    return name


def _inside(real_root, real_path):
    return real_path == real_root or real_path.startswith(real_root + os.sep)


def _check_no_escape(skill_dir):
    """Refuse any symlink inside skill_dir resolving outside it."""
    real_skill = os.path.realpath(skill_dir)
    for dirpath, dirnames, filenames in os.walk(skill_dir):
        for entry in dirnames + filenames:
            full = os.path.join(dirpath, entry)
            if os.path.islink(full):
                target = os.path.realpath(full)
                if not _inside(real_skill, target):
                    _fail(f"skill: symlink {full!r} escapes its skill "
                          "folder, mount refused")


def _collection_root(collection_root):
    root = os.path.abspath(collection_root)
    if not os.path.isdir(root):
        _fail(f"skills: collection root is not a directory: {root}")
    return root


def resolve_skill(collection_root, name):
    """Resolve one named skill inside a collection, or refuse.

    Returns the skill directory. Refuses an invalid name, a
    missing folder, a folder without SKILL.md, and a folder (or
    symlink to one) resolving outside the collection root.
    """
    root = _collection_root(collection_root)
    _validate_name(name)
    path = os.path.join(root, name)
    if not os.path.isdir(path):
        _fail(f"skill: no such skill in collection: {name!r}")
    real_root = os.path.realpath(root)
    real_path = os.path.realpath(path)
    if not _inside(real_root, real_path):
        _fail(f"skill: {name!r} resolves outside the collection root, "
              "mount refused")
    if not os.path.isfile(os.path.join(path, SKILL_DOC)):
        _fail(f"skill: {name!r} has no {SKILL_DOC}, not a mountable "
              "skill app")
    _check_no_escape(path)
    return path


def list_skills(collection_root):
    """Sorted names of the mountable skills in a collection.

    A folder counts only when it is a directory carrying SKILL.md
    and resolving inside the collection. Anything else is not
    listed: listing reports what can mount, nothing else.
    """
    root = _collection_root(collection_root)
    names = []
    for entry in sorted(os.listdir(root)):
        path = os.path.join(root, entry)
        if not os.path.isdir(path):
            continue
        if not os.path.isfile(os.path.join(path, SKILL_DOC)):
            continue
        if not _inside(os.path.realpath(root), os.path.realpath(path)):
            continue
        names.append(entry)
    return names


def mount_skill_dir(src_dir, dst_dir):
    """Mount one skill folder verbatim at dst_dir; return its hashes.

    Refuses a missing SKILL.md, a symlink escaping the skill
    folder, and an existing destination. Nothing is copied on a
    refusal.
    """
    if not os.path.isdir(src_dir):
        _fail(f"skill: source is not a directory: {src_dir}")
    if not os.path.isfile(os.path.join(src_dir, SKILL_DOC)):
        _fail(f"skill: {src_dir!r} has no {SKILL_DOC}, not a "
              "mountable skill app")
    _check_no_escape(src_dir)
    if os.path.lexists(dst_dir):
        _fail(f"skill: mount target already exists: {dst_dir}")
    os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
    shutil.copytree(src_dir, dst_dir)
    return _hash_tree(dst_dir)


def mount_skill_dirs(pairs, skills_dir):
    """Mount (name, skill_dir) pairs into skills_dir; return hashes.

    Every pair is validated before anything is copied, so a
    refusal leaves no partial mount behind: names unique and
    plain basenames, every source a SKILL.md-carrying folder
    with no escaping symlink, every target absent.
    """
    names = [_validate_name(name) for name, _src in pairs]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        _fail("skill: duplicate mount name: " + ", ".join(dupes))
    for name, src in pairs:
        if not os.path.isdir(src):
            _fail(f"skill: no such skill folder: {name!r} ({src})")
        if not os.path.isfile(os.path.join(src, SKILL_DOC)):
            _fail(f"skill: {name!r} has no {SKILL_DOC}, not a "
                  "mountable skill app")
        _check_no_escape(src)
        if os.path.lexists(os.path.join(skills_dir, name)):
            _fail(f"skill: mount target already exists: "
                  f"{os.path.join(skills_dir, name)}")
    hashes = {}
    for name, src in pairs:
        hashes[name] = mount_skill_dir(src, os.path.join(skills_dir, name))
    return hashes


def mount_skills(collection_root, names, launch_dir):
    """Mount named collection skills into launch_dir; return manifest.

    Writes launch_dir/skills/<name>/ for each named skill plus
    launch_dir/skills.json recording every mounted file's hash.
    Unlisted collection folders are never mounted. An empty name
    list mounts nothing and still writes an empty manifest, so a
    skill-free launch verifies the same way a skilled one does.
    """
    root = _collection_root(collection_root)
    pairs = [(name, resolve_skill(root, name)) for name in names]
    launch_dir = os.path.abspath(launch_dir)
    skills_dir = os.path.join(launch_dir, "skills")
    hashes = mount_skill_dirs(pairs, skills_dir)
    manifest = {
        "format": MANIFEST_FORMAT,
        "collection": root,
        "skills": hashes,
    }
    os.makedirs(launch_dir, exist_ok=True)
    with open(os.path.join(launch_dir, MANIFEST_NAME), "w",
              encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


def verify_mount(launch_dir):
    """Verify a mounted launch directory; return a list of errors.

    An empty list is a pass. Checks the manifest exists and
    parses, every manifest skill directory exists with hashes
    still matching, and no extra skill directory sits under
    skills/ that the manifest never named.
    """
    errors = []
    launch_dir = os.path.abspath(launch_dir)
    manifest_path = os.path.join(launch_dir, MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        return [f"skills: no {MANIFEST_NAME} in {launch_dir}"]
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (ValueError, OSError) as exc:
        return [f"skills: unreadable {MANIFEST_NAME}: {exc}"]
    if not isinstance(manifest, dict) or \
            manifest.get("format") != MANIFEST_FORMAT:
        return ["skills: manifest is not a metaos-skills-mount manifest"]
    skills = manifest.get("skills")
    if not isinstance(skills, dict):
        return ["skills: manifest carries no skills map"]
    skills_dir = os.path.join(launch_dir, "skills")
    for name in sorted(skills):
        dst = os.path.join(skills_dir, name)
        if not os.path.isdir(dst):
            errors.append(f"skills: mounted skill missing: {name!r}")
            continue
        actual = _hash_tree(dst)
        if actual != skills[name]:
            errors.append(f"skills: mounted skill changed: {name!r}")
    if os.path.isdir(skills_dir):
        for entry in sorted(os.listdir(skills_dir)):
            if entry not in skills:
                errors.append(f"skills: unlisted skill directory mounted: "
                              f"{entry!r}")
    return errors


def main(argv=None):
    """CLI: list | mount <collection> <name>... --into <dir> | verify.

    Returns an exit code: 0 on success, 1 on a loader refusal,
    2 on a usage error. Prints loader errors on stderr, never
    as a successful mount.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="skills_loader",
        description="Mount skills-2 style skill folders into a launch "
                    "directory.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list", help="list mountable skills")
    p_list.add_argument("collection")
    p_mount = sub.add_parser("mount", help="mount named skills")
    p_mount.add_argument("collection")
    p_mount.add_argument("names", nargs="+")
    p_mount.add_argument("--into", required=True)
    p_verify = sub.add_parser("verify", help="verify a mounted directory")
    p_verify.add_argument("launch_dir")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    try:
        if args.command == "list":
            for name in list_skills(args.collection):
                print(name)
        elif args.command == "mount":
            manifest = mount_skills(args.collection, args.names,
                                    args.into)
            print(f"mounted {len(manifest['skills'])} skill(s) into "
                  f"{args.into}")
        elif args.command == "verify":
            errors = verify_mount(args.launch_dir)
            if errors:
                for err in errors:
                    print(err, file=sys.stderr)
                return 1
            print("skills mount ok")
    except SkillsLoaderError as exc:
        print(f"skills_loader: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
