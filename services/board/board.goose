// services/board/board.goose
//
// Layer 5, face service 6: the board client.
//
// WHAT THIS IS
// ------------
// Rooms and an append-only post log, with ids that only go up. Three choices carry it:
//
//   1. **Posts are immutable.** There is no edit and no delete. A board whose history
//      can change is a board where a fetch is not a record of what was said.
//   2. **A full log refuses; it does not drop.** A ring that silently overwrote the
//      oldest post would make `fetch since 1` return a different answer at different
//      times. `E_NO_SPACE` is the honest answer.
//   3. **Ids are the cursor.** `fetch(room, since_id)` returns everything newer than
//      the id the client already has, so a reader that lost its place catches up
//      without timestamps or a server-side mark.
//
// PERSISTENCE
// -----------
// `bd_export` writes comma-separated lines and `bd_import` parses them atomically
// (a bad line applies nothing). Commas and newlines are refused in room names and
// post text at write time, so the format cannot be made ambiguous by content.
//
// Status: RUNS — reached by tests/t91_board (exit 0). Measured 2026-11-02 by audit_status.py.

import common.err.err;

let BD_MAX_ROOMS: i64 = 4;
let BD_MAX_POSTS: i64 = 24;
let BD_ROOM_NAME_MAX: i64 = 16;
let BD_POST_MAX: i64 = 96;

struct Room {
    id: i64,
    name: u8[..16] = [0; 16],
    name_len: i64,
    used: bool,
}

struct Post {
    id: i64,
    room: i64,
    text: u8[..96] = [0; 96],
    text_len: i64,
    created_ms: i64,
    used: bool,
}

var rooms: Room[..4] = [Room { .. }; 4];
var room_count: i64 = 0;
var posts: Post[..24] = [Post { .. }; 24];
var post_count: i64 = 0;
var next_post: i64 = 1;
var refused_posts: i64 = 0;

fn bd_init() {
    var i: i64 = 0;
    while i < BD_MAX_ROOMS {
        rooms[i].id = 0;
        rooms[i].name_len = 0;
        rooms[i].used = false;
        var j: i64 = 0;
        while j < BD_ROOM_NAME_MAX { rooms[i].name[j] = 0; j = j + 1; }
        i = i + 1;
    }
    room_count = 0;
    i = 0;
    while i < BD_MAX_POSTS {
        posts[i].id = 0;
        posts[i].room = 0;
        posts[i].text_len = 0;
        posts[i].created_ms = 0;
        posts[i].used = false;
        var k: i64 = 0;
        while k < BD_POST_MAX { posts[i].text[k] = 0; k = k + 1; }
        i = i + 1;
    }
    post_count = 0;
    next_post = 1;
    refused_posts = 0;
}

fn bd_clean(s: const u8[:]) -> bool {
    var i: i64 = 0;
    while i < s.len {
        if s[i] < 32 || s[i] > 126 { return false; }
        if s[i] == 44 || s[i] == 10 { return false; }   // ',' and '\n' are the format
        i = i + 1;
    }
    return true;
}

fn bd_room_find(id: i64) -> i64 {
    var i: i64 = 0;
    while i < room_count {
        if rooms[i].used && rooms[i].id == id { return i; }
        i = i + 1;
    }
    return -1;
}

fn bd_room_find_name(s: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < room_count {
        if rooms[i].used && rooms[i].name_len == s.len && bd_name_eq(i, s) { return i; }
        i = i + 1;
    }
    return -1;
}

fn bd_name_eq(i: i64, s: const u8[:]) -> bool {
    var k: i64 = 0;
    while k < s.len {
        if rooms[i].name[k] != s[k] { return false; }
        k = k + 1;
    }
    return true;
}

fn bd_room_add(name: const u8[:]) -> i64, i64 {
    if name.len == 0 || !bd_clean(name) { return -1, E_INVAL; }
    if name.len >= BD_ROOM_NAME_MAX { return -1, E_NOROOM; }
    if bd_room_find_name(name) >= 0 { return -1, E_STATE; }
    if room_count >= BD_MAX_ROOMS { return -1, E_NO_SPACE; }
    let n = room_count;
    rooms[n].id = n + 1;
    rooms[n].used = true;
    rooms[n].name_len = name.len;
    var i: i64 = 0;
    while i < name.len {
        rooms[n].name[i] = name[i];
        i = i + 1;
    }
    room_count = room_count + 1;
    return rooms[n].id, CODE_OK;
}

fn bd_room_count() -> i64 { return room_count; }

fn bd_room_name_at(i: i64) -> const u8[:] {
    if i < 0 || i >= room_count { return ""; }
    return rooms[i].name[..rooms[i].name_len];
}

fn bd_room_id_at(i: i64) -> i64 {
    if i < 0 || i >= room_count { return 0; }
    return rooms[i].id;
}

// Append a post. The id is assigned here and is the cursor readers use.
fn bd_post(room: i64, text: const u8[:], now_ms: i64) -> i64, i64 {
    if bd_room_find(room) < 0 { return 0, E_NOTFOUND; }
    if text.len == 0 || !bd_clean(text) { return 0, E_INVAL; }
    if text.len >= BD_POST_MAX { return 0, E_NOROOM; }
    if post_count >= BD_MAX_POSTS {
        // Refuse, never overwrite: an overwriting ring makes the same fetch return
        // different history depending on when it ran.
        refused_posts = refused_posts + 1;
        return 0, E_NO_SPACE;
    }
    let n = post_count;
    posts[n].id = next_post;
    posts[n].room = room;
    posts[n].text_len = text.len;
    posts[n].created_ms = now_ms;
    posts[n].used = true;
    var i: i64 = 0;
    while i < BD_POST_MAX { posts[n].text[i] = 0; i = i + 1; }
    i = 0;
    while i < text.len {
        posts[n].text[i] = text[i];
        i = i + 1;
    }
    next_post = next_post + 1;
    post_count = post_count + 1;
    return posts[n].id, CODE_OK;
}

fn bd_post_count(room: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < post_count {
        if posts[i].used && posts[i].room == room { n = n + 1; }
        i = i + 1;
    }
    return n;
}

fn bd_last_id(room: i64) -> i64 {
    var best: i64 = 0;
    var i: i64 = 0;
    while i < post_count {
        if posts[i].used && posts[i].room == room && posts[i].id > best { best = posts[i].id; }
        i = i + 1;
    }
    return best;
}

fn bd_unread(room: i64, since_id: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < post_count {
        if posts[i].used && posts[i].room == room && posts[i].id > since_id { n = n + 1; }
        i = i + 1;
    }
    return n;
}

// Fetch everything in a room newer than `since_id`, as "id:text" lines. Returns the
// number of posts written. The caller's buffer is appended to, never reset, so a
// caller can fetch two rooms into one buffer.
fn bd_fetch(room: i64, since_id: i64, out: u8[>..]&) -> i64, i64 {
    if bd_room_find(room) < 0 { return 0, E_NOTFOUND; }
    var n: i64 = 0;
    var i: i64 = 0;
    while i < post_count {
        if posts[i].used && posts[i].room == room && posts[i].id > since_id {
            bd_emit_int(out, posts[i].id);
            let _ = out.push(58);              // ':'
            var k: i64 = 0;
            while k < posts[i].text_len {
                let _ = out.push(posts[i].text[k]);
                k = k + 1;
            }
            let _ = out.push(10);
            n = n + 1;
        }
        i = i + 1;
    }
    return n, CODE_OK;
}

fn bd_refused_total() -> i64 { return refused_posts; }
fn bd_post_total() -> i64 { return post_count; }

fn bd_emit_int(out: u8[>..]&, v: i64) {
    if v == 0 {
        let _ = out.push(48);
        return;
    }
    var tmp: u8[..24] = [0; 24];
    var n: i64 = 0;
    var x = v;
    while x > 0 {
        tmp[n] = (48 + (x % 10)) as u8;
        x = x / 10;
        n = n + 1;
    }
    var i: i64 = 0;
    while i < n {
        let _ = out.push(tmp[n - 1 - i]);
        i = i + 1;
    }
}

// ---------------------------------------------------------------------------
// Persistence: "R,id,name" and "P,id,room,created,text", in that order.

fn bd_export(out: u8[..2048]&) -> i64 {
    var n: i64 = 0;
    var r: i64 = 0;
    while r < room_count {
        out[n] = 82; n = n + 1;                 // 'R'
        out[n] = 44; n = n + 1;
        n = n + bd_write_int(out, n, rooms[r].id);
        out[n] = 44; n = n + 1;
        var k: i64 = 0;
        while k < rooms[r].name_len {
            out[n] = rooms[r].name[k];
            n = n + 1;
            k = k + 1;
        }
        out[n] = 10; n = n + 1;
        r = r + 1;
    }
    var p: i64 = 0;
    while p < post_count {
        out[n] = 80; n = n + 1;                 // 'P'
        out[n] = 44; n = n + 1;
        n = n + bd_write_int(out, n, posts[p].id);
        out[n] = 44; n = n + 1;
        n = n + bd_write_int(out, n, posts[p].room);
        out[n] = 44; n = n + 1;
        n = n + bd_write_int(out, n, posts[p].created_ms);
        out[n] = 44; n = n + 1;
        var k: i64 = 0;
        while k < posts[p].text_len {
            out[n] = posts[p].text[k];
            n = n + 1;
            k = k + 1;
        }
        out[n] = 10; n = n + 1;
        p = p + 1;
    }
    return n;
}

fn bd_write_int(out: u8[..2048]&, n: i64, v: i64) -> i64 {
    var tmp: u8[..24] = [0; 24];
    var k: i64 = 0;
    var x = v;
    if x == 0 {
        out[n] = 48;
        return 1;
    }
    while x > 0 {
        tmp[k] = (48 + (x % 10)) as u8;
        x = x / 10;
        k = k + 1;
    }
    var i: i64 = 0;
    while i < k {
        out[n + i] = tmp[k - 1 - i];
        i = i + 1;
    }
    return k;
}

fn bd_parse_int(s: const u8[:], from: i64, to: i64) -> i64, bool {
    if to <= from { return 0, false; }
    var v: i64 = 0;
    var i = from;
    while i < to {
        if s[i] < 48 || s[i] > 57 { return 0, false; }
        v = v * 10 + (s[i] - 48);
        i = i + 1;
    }
    return v, true;
}

fn bd_import(data: const u8[:]) -> i64 {
    // Stage the whole thing, commit only if every line is valid.
    var stage_rooms: Room[..4] = [Room { .. }; 4];
    var stage_posts: Post[..24] = [Post { .. }; 24];
    var sr: i64 = 0;
    var sp: i64 = 0;
    var highest: i64 = 0;
    var lines: i64 = 0;

    var pos: i64 = 0;
    while pos < data.len {
        var end = pos;
        while end < data.len && data[end] != 10 { end = end + 1; }
        if end - pos < 3 { return E_CORRUPT; }

        // "R,<id>,<name>" — three fields, so two commas after the kind letter.
        if data[pos] == 82 {                     // room
            if sr >= BD_MAX_ROOMS { return E_NO_SPACE; }
            let idFrom = pos + 2;
            let c1 = bd_find_ch(data, idFrom, end, 44);
            if c1 < 0 { return E_CORRUPT; }
            let idv, ok1 = bd_parse_int(data, idFrom, c1);
            if !ok1 || idv < 1 { return E_CORRUPT; }
            let nameFrom = c1 + 1;
            let name_len = end - nameFrom;
            if name_len <= 0 || name_len >= BD_ROOM_NAME_MAX { return E_CORRUPT; }
            stage_rooms[sr].id = idv;
            stage_rooms[sr].used = true;
            stage_rooms[sr].name_len = name_len;
            var k: i64 = 0;
            while k < name_len {
                if data[nameFrom + k] < 32 || data[nameFrom + k] > 126 { return E_CORRUPT; }
                stage_rooms[sr].name[k] = data[nameFrom + k];
                k = k + 1;
            }
            sr = sr + 1;
        // "P,<id>,<room>,<created>,<text>" — five fields, so four commas after the
        // kind letter; the text is the rest of the line and may contain spaces.
        } else if data[pos] == 80 {              // post
            if sp >= BD_MAX_POSTS { return E_NO_SPACE; }
            let idFrom = pos + 2;
            let c1 = bd_find_ch(data, idFrom, end, 44);
            if c1 < 0 { return E_CORRUPT; }
            let c2 = bd_find_ch(data, c1 + 1, end, 44);
            if c2 < 0 { return E_CORRUPT; }
            let c3 = bd_find_ch(data, c2 + 1, end, 44);
            if c3 < 0 { return E_CORRUPT; }
            let idv, ok1 = bd_parse_int(data, idFrom, c1);
            let roomv, ok2 = bd_parse_int(data, c1 + 1, c2);
            let created, ok3 = bd_parse_int(data, c2 + 1, c3);
            if !ok1 || !ok2 || !ok3 { return E_CORRUPT; }
            if idv < 1 || roomv < 1 { return E_CORRUPT; }
            let textFrom = c3 + 1;
            let text_len = end - textFrom;
            if text_len <= 0 || text_len >= BD_POST_MAX { return E_NOROOM; }
            stage_posts[sp].id = idv;
            stage_posts[sp].room = roomv;
            stage_posts[sp].created_ms = created;
            stage_posts[sp].text_len = text_len;
            stage_posts[sp].used = true;
            var k: i64 = 0;
            while k < text_len {
                if data[textFrom + k] < 32 || data[textFrom + k] > 126 { return E_CORRUPT; }
                stage_posts[sp].text[k] = data[textFrom + k];
                k = k + 1;
            }
            sp = sp + 1;
            if idv > highest { highest = idv; }
        } else {
            return E_CORRUPT;
        }
        lines = lines + 1;
        pos = end + 1;
    }
    if lines == 0 { return E_CORRUPT; }

    // A post in a room the file does not define is a corrupt file, not a post to
    // drop: the board would show a room that does not exist.
    var p: i64 = 0;
    while p < sp {
        var found = false;
        var r: i64 = 0;
        while r < sr {
            if stage_rooms[r].id == stage_posts[p].room { found = true; }
            r = r + 1;
        }
        if !found { return E_CORRUPT; }
        p = p + 1;
    }

    var i: i64 = 0;
    while i < sr { rooms[i] = stage_rooms[i]; i = i + 1; }
    room_count = sr;
    i = 0;
    while i < sp { posts[i] = stage_posts[i]; i = i + 1; }
    post_count = sp;
    next_post = highest + 1;
    return lines;
}

fn bd_find_ch(data: const u8[:], from: i64, to: i64, ch: u8) -> i64 {
    var i = from;
    while i < to {
        if data[i] == ch { return i; }
        i = i + 1;
    }
    return -1;
}
