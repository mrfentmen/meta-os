// services/fs/paths.goose
//
// Path parsing and resolution for MOSFS01 (B-L1-83).
//
// Status: WRITTEN (not COMPILED, not RUN). Rules and reasoning: `DESIGN.md` §4.
//
// WHY RESOLUTION TAKES A STARTING DIRECTORY
// -----------------------------------------
// There is no process-wide current directory, because a process-wide anything is one more
// thing the supervisor has to reconstruct after a restart and one more way two services can
// disagree. `fs_resolve(cwd, path)` takes the caller's idea of "here" as an argument. The
// shell keeps a cwd in its session (B-L1-114), the agent host keeps one per agent, and
// neither can accidentally change the other's.
//
// `..` IS PATH SYNTAX, NOT A STORED ENTRY
// --------------------------------------
// Directories do not store `.` or `..` (DESIGN.md §4), so `..` is resolved against the
// chain of directories this walk actually descended through. That chain is a fixed 16-entry
// array: 16 components deep is the limit, and going deeper returns E_NOROOM rather than
// silently resolving to something else.
//
// EVERY HOSTILE CASE, AND WHAT IT DOES
// ------------------------------------
// | path                     | result                                        |
// |--------------------------|-----------------------------------------------|
// | `""`                     | E_INVAL                                       |
// | `"/"`                    | root                                          |
// | `"//a///b/"`             | same as `/a/b`; repeated slashes collapse     |
// | `"/.."`                  | root -- `..` at the root stays at the root    |
// | `"/../../etc"`           | `/etc` or E_NOTFOUND; never escapes the root  |
// | `"/a/"`                  | `a` must be a directory (trailing slash)      |
// | `"/a/.hidden"`           | an ordinary name (leading dots are not special)|
// | `"/abcdefghijklm"`       | E_INVAL -- 13 bytes, max name is 12            |
// | `"/a/b/c/...` 17 deep    | E_INVAL -- depth limit is 16                   |
// | `"rel/path"`             | resolved from the caller's starting directory  |

import common.err.err;
import fs.fs;

// The two spans of a path split at its last component: (parent span, name span).
// `/a/b/c` -> parent `/a/b`, name `c`. `/c` -> parent `/`, name `c`.
// `/a/b/`  -> parent `/a`, name `b` (a trailing slash is not a component).
fn path_split_last(p: const u8[:]) -> i64, i64, i64, i64 {
    var end = p.len;
    while end > 0 && p[end - 1] == '/' { end = end - 1; }         // drop trailing slashes
    var cut = end;
    while cut > 0 && p[cut - 1] != '/' { cut = cut - 1; }         // back to the last slash
    return 0, cut, cut, end;
}

// Is this component exactly ".."? Length first, so "..." is an ordinary name.
fn is_dotdot(c: const u8[:]) -> bool {
    return c.len == 2 && c[0] == '.' && c[1] == '.';
}

fn is_dot(c: const u8[:]) -> bool {
    return c.len == 1 && c[0] == '.';
}

// Resolve `path` from `start`. Returns (ino, code).
//
// `want_dir` is not advisory: a trailing slash sets it, and a resolved non-directory with
// `want_dir` set is E_INVAL. A caller that gets an inode back and then finds it is the wrong
// kind has already made the mistake this argument prevents.
fn fs_resolve(start: i64, path: const u8[:], want_dir: bool) -> i64, i64 {
    if !fs_is_mounted() { return 0, E_STATE; }
    if path.len == 0 { return 0, E_INVAL; }
    if path.len > 255 { return 0, E_INVAL; }

    var chain: i64[..16] = [0; 16];
    var depth: i64 = 0;
    var cur = start;

    if path[0] == '/' {
        cur = fs_root();
        chain[depth] = cur;
        depth = 1;
    } else {
        if !ino_is_dir(cur) { return 0, E_INVAL; }
        chain[depth] = cur;
        depth = 1;
    }

    let trailing_slash = path[path.len - 1] == '/';
    var i: i64 = 0;
    var last_was_name = false;
    while i < path.len {
        while i < path.len && path[i] == '/' { i = i + 1; }     // collapse runs of slashes
        if i >= path.len { break; }
        var j = i;
        while j < path.len && path[j] != '/' { j = j + 1; }
        let comp = path[i..j];

        if is_dot(comp) {
            last_was_name = false;
        } else if is_dotdot(comp) {
            // Pop. At the root the chain has one entry, and popping it must NOT escape:
            // `cur` stays the root, which is what makes `/../../x` equal `/x`.
            if depth > 1 {
                depth = depth - 1;
                cur = chain[depth - 1];
            } else {
                cur = fs_root();
                chain[0] = cur;
                depth = 1;
            }
            last_was_name = false;
        } else {
            if comp.len > 12 { return 0, E_INVAL; }        // max name, refused not truncated
            if !ino_is_dir(cur) { return 0, E_INVAL; }     // walk through a file: no
            let next, lc = fs_lookup(cur, comp);
            if lc != CODE_OK { return 0, lc; }
            if next == 0 { return 0, E_NOTFOUND; }
            if depth >= 16 { return 0, E_NOROOM; }         // one more than the chain holds
            chain[depth] = next;
            depth = depth + 1;
            cur = next;
            last_was_name = true;
        }
        i = j;
    }

    if !last_was_name {
        // The path ended on a slash, or was all dots: the answer must be a directory, and
        // `cur` is the last directory we were in.
        if !ino_is_dir(cur) { return 0, E_INVAL; }
        return cur, CODE_OK;
    }
    if want_dir || trailing_slash {
        if !ino_is_dir(cur) { return 0, E_INVAL; }
    }
    return cur, CODE_OK;
}

// Create an entry at `path`, relative to `start`. The parent must exist; the name must not.
fn fs_create_path(start: i64, path: const u8[:], kind: i64) -> i64, i64 {
    if path.len == 0 { return 0, E_INVAL; }
    let ps, pe, ns, ne = path_split_last(path);
    let name = path[ns..ne];
    if name.len == 0 { return 0, E_INVAL; }
    if name.len > 12 { return 0, E_INVAL; }
    let parent_path = path[ps..pe];
    // "/" as a parent path means the root. An empty parent path means the same when the
    // original path was absolute; when it was relative, the caller's own directory is used.
    var parent = start;
    if parent_path.len > 0 {
        let p, pc = fs_resolve(start, parent_path, true);
        if pc != CODE_OK { return 0, pc; }
        parent = p;
    } else if path[0] == '/' {
        parent = fs_root();
    }
    return fs_create(parent, name, kind);
}

// Remove the entry at `path` (a file, or an empty directory). Refuses `/` and refuses to
// unlink a non-empty directory, through `fs_unlink`.
fn fs_unlink_path(start: i64, path: const u8[:]) -> i64 {
    if path.len == 0 { return E_INVAL; }
    let ps, pe, ns, ne = path_split_last(path);
    let name = path[ns..ne];
    if name.len == 0 { return E_INVAL; }
    let parent_path = path[ps..pe];
    var parent = start;
    if parent_path.len > 0 {
        let p, pc = fs_resolve(start, parent_path, true);
        if pc != CODE_OK { return pc; }
        parent = p;
    } else if path[0] == '/' {
        parent = fs_root();
    }
    return fs_unlink(parent, name);
}

fn path_split_name(p: const u8[:]) -> const u8[:] {
    let _ps, _pe, ns, ne = path_split_last(p);
    return p[ns..ne];
}

// The last component as a span, for error messages and for `mkdir` to echo back.
fn path_basename(p: const u8[:]) -> const u8[:] {
    return path_split_name(p);
}

// ---------------------------------------------------------------------------
// What this module deliberately does NOT do
// ---------------------------------------------------------------------------
//
// - **No wildcard or glob expansion.** The shell (B-L1-87) owns that, over its argument
//   parser, because globs are a shell syntax and not a filesystem property.
// - **No symlinks.** A symlink is a resolution loop and a resolution loop in a fixed-stack
//   resolver is a hang. If they are ever wanted, they arrive with a hop counter and their
//   own test.
// - **No `~`, no environment variables, no `:` separators.** Every one of those is a
//   feature that makes "/a/b" mean different things in two callers.
// - **No relative-to-parent `..` after a rename.** The chain is the walk, not the tree:
//   `fs_resolve(root, "/a/../b")` follows the walk the caller asked for, which is the only
//   definition that does not require storing parent pointers.
