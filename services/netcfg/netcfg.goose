// services/netcfg/netcfg.goose
//
// Layer 4, service 14: addresses and interface configuration as data.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs
// (reference#32), fixed arrays, `while`/`if`, slices, `T&` references (reference#46),
// `import` of a sibling module, `as` casts, multi-value returns.
//
// WHY ADDRESSES ARE A STRUCT AND NOT A STRING
// -------------------------------------------
// Every protocol layer needs to ask questions about an address: is this in my subnet,
// is this the broadcast address, is this a mask with a hole in it. Doing that on text
// means every layer re-implements parsing, and the ones that get it wrong differ in
// exactly the cases that matter (leading zeros, a mask of /31, the difference between
// 0.0.0.0 and "unset").
//
// Configuration is text, so there is one parser, and everything above it is bytes.
//
// WHAT "UNSET" MEANS
// ------------------
// 0.0.0.0 is a real address -- the DHCP client must send from it before it has one.
// Configuration therefore needs a separate "did the user say anything" bit, which is
// why every parse function returns a bool alongside the value. A zero address that
// means "not configured" and a zero address that means "0.0.0.0" are the same bytes
// and different facts.

import common.cfg.cfg;
import common.err.err;

// ---------------------------------------------------------------------------
// Addresses
// ---------------------------------------------------------------------------

struct Ipv4 {
    a: u8,
    b: u8,
    c: u8,
    d: u8,
}

fn ip4(a: u8, b: u8, c: u8, d: u8) -> Ipv4 {
    return Ipv4 { a: a, b: b, c: c, d: d };
}

fn ip4_any() -> Ipv4 {
    return Ipv4 { a: 0, b: 0, c: 0, d: 0 };
}

fn ip4_broadcast() -> Ipv4 {
    return Ipv4 { a: 255, b: 255, c: 255, d: 255 };
}

fn ip4_zero(a: Ipv4&) -> bool {
    return a.a == 0 && a.b == 0 && a.c == 0 && a.d == 0;
}

fn ip4_equal(x: Ipv4&, y: Ipv4&) -> bool {
    return x.a == y.a && x.b == y.b && x.c == y.c && x.d == y.d;
}

// Parse `a.b.c.d`. Strict on purpose: exactly four parts, 1-3 digits each, no leading
// zeroes (an octal-looking address is a configuration error, and every system that
// accepted it has produced a bug), each part 0-255.
//
// Returns (address, ok). A rejected string yields 0.0.0.0 and ok = false, so a caller
// that ignores the flag gets an obvious value rather than a plausible wrong one.
fn ip4_parse(s: const u8[:]) -> Ipv4, bool {
    var parts: u8[..4] = [];
    var part_count: i64 = 0;
    var i: i64 = 0;
    var digits_here: i64 = 0;
    var value: i64 = 0;
    var leading_zero = false;

    while i < s.len {
        let ch = s[i];
        if ch == 0x2E {                                  // .
            if digits_here == 0 { return ip4_any(), false; }
            if leading_zero && digits_here > 1 { return ip4_any(), false; }
            if part_count >= 4 { return ip4_any(), false; }
            parts[part_count] = value as u8;
            part_count = part_count + 1;
            value = 0;
            digits_here = 0;
            leading_zero = false;
        } else if ch >= 0x30 && ch <= 0x39 {
            if digits_here == 0 && ch == 0x30 && s.len > 1 { leading_zero = true; }
            if digits_here >= 3 { return ip4_any(), false; }
            value = value * 10 + ((ch - 0x30) as i64);
            if value > 255 { return ip4_any(), false; }
            digits_here = digits_here + 1;
        } else {
            return ip4_any(), false;                     // no spaces, no signs, no hex
        }
        i = i + 1;
    }
    if digits_here == 0 { return ip4_any(), false; }
    if leading_zero && digits_here > 1 { return ip4_any(), false; }
    if part_count != 3 { return ip4_any(), false; }      // exactly four parts total
    parts[3] = value as u8;
    return Ipv4 { a: parts[0], b: parts[1], c: parts[2], d: parts[3] }, true;
}

// Render into a caller buffer. Returns bytes written, or -1 if the buffer is too small.
fn ip4_render(addr: Ipv4&, out: u8[..16]&) -> i64 {
    var n: i64 = 0;
    n = ip4_put_octet(out, n, addr.a);
    if n < 0 { return -1; }
    out[n] = 0x2E; n = n + 1;
    n = ip4_put_octet(out, n, addr.b);
    if n < 0 { return -1; }
    out[n] = 0x2E; n = n + 1;
    n = ip4_put_octet(out, n, addr.c);
    if n < 0 { return -1; }
    out[n] = 0x2E; n = n + 1;
    n = ip4_put_octet(out, n, addr.d);
    if n < 0 { return -1; }
    return n;
}

fn ip4_put_octet(out: u8[..16]&, at_in: i64, v: u8) -> i64 {
    var at = at_in;
    if v >= 100 {
        if at + 3 > 16 { return -1; }
        out[at] = 0x30 + (v / 100); at = at + 1;
        out[at] = 0x30 + ((v % 100) / 10); at = at + 1;
        out[at] = 0x30 + (v % 10); at = at + 1;
        return at;
    }
    if v >= 10 {
        if at + 2 > 16 { return -1; }
        out[at] = 0x30 + (v / 10); at = at + 1;
        out[at] = 0x30 + (v % 10); at = at + 1;
        return at;
    }
    if at + 1 > 16 { return -1; }
    out[at] = 0x30 + v;
    return at + 1;
}

// ---------------------------------------------------------------------------
// Masks
// ---------------------------------------------------------------------------

// A prefix length as a mask. /0 and /32 are both legal.
fn ip4_mask(prefix: i64) -> Ipv4, bool {
    if prefix < 0 || prefix > 32 { return ip4_any(), false; }
    var bits = prefix;
    var m: u8[..4] = [];
    var i: i64 = 0;
    while i < 4 {
        if bits >= 8 { m[i] = 0xFF; bits = bits - 8; }
        else if bits <= 0 { m[i] = 0; }
        else {
            // One byte with the top `bits` set: 0xFF << (8 - bits), masked to a byte.
            m[i] = (0xFF << (8 - bits)) as u8;
            bits = 0;
        }
        i = i + 1;
    }
    return Ipv4 { a: m[0], b: m[1], c: m[2], d: m[3] }, true;
}

// Is the mask contiguous? 255.0.255.0 is not a netmask, and accepting it makes every
// subnet check below meaningless.
//
// Checked as: once a byte is not 0xFF, every byte after it must be 0, and each such
// byte must itself be a run of high bits.
fn ip4_mask_contiguous(mask: Ipv4&) -> bool {
    if !ip4_run_of_high_bits(mask.a) { return false; }
    if !ip4_run_of_high_bits(mask.b) { return false; }
    if !ip4_run_of_high_bits(mask.c) { return false; }
    if !ip4_run_of_high_bits(mask.d) { return false; }
    if mask.a != 0xFF && (mask.b != 0 || mask.c != 0 || mask.d != 0) { return false; }
    if mask.b != 0xFF && (mask.c != 0 || mask.d != 0) { return false; }
    if mask.c != 0xFF && mask.d != 0 { return false; }
    return true;
}

fn ip4_run_of_high_bits(b: u8) -> bool {
    if b == 0x00 || b == 0x80 || b == 0xC0 || b == 0xE0 { return true; }
    if b == 0xF0 || b == 0xF8 || b == 0xFC || b == 0xFE { return true; }
    return b == 0xFF;
}

// Are two addresses in the same subnet under this mask?
fn ip4_same_subnet(x: Ipv4&, y: Ipv4&, mask: Ipv4&) -> bool {
    return (x.a & mask.a) == (y.a & mask.a)
        && (x.b & mask.b) == (y.b & mask.b)
        && (x.c & mask.c) == (y.c & mask.c)
        && (x.d & mask.d) == (y.d & mask.d);
}

// The directed broadcast for an address under a mask (host bits all ones).
fn ip4_subnet_broadcast(addr: Ipv4&, mask: Ipv4&) -> Ipv4 {
    return Ipv4 {
        a: addr.a | (~mask.a),
        b: addr.b | (~mask.b),
        c: addr.c | (~mask.c),
        d: addr.d | (~mask.d),
    };
}

// ---------------------------------------------------------------------------
// Interface configuration
// ---------------------------------------------------------------------------

let IF_NAME_MAX: i64 = 8;

struct IfaceCfg {
    name: u8[..8],
    name_len: i64,
    configured: bool,       // did the config file say anything about this interface
    use_dhcp: bool,
    addr: Ipv4,
    mask: Ipv4,
    gw: Ipv4,
    dns1: Ipv4,
    dns2: Ipv4,
    mtu: i64,
}

fn iface_default(name: const u8[:]) -> IfaceCfg {
    var c: IfaceCfg = IfaceCfg {
        name: [],
        name_len: 0,
        configured: false,
        use_dhcp: false,
        addr: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        mask: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        gw: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        dns1: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        dns2: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        mtu: 0,
    };
    var i: i64 = 0;
    while i < name.len && i < IF_NAME_MAX - 1 {
        c.name[i] = name[i];
        i = i + 1;
    }
    c.name[i] = 0;
    c.name_len = i;
    c.configured = false;
    c.use_dhcp = false;
    c.addr = ip4_any();
    c.mask = ip4_any();
    c.gw = ip4_any();
    c.dns1 = ip4_any();
    c.dns2 = ip4_any();
    c.mtu = 1500;           // the value every network assumes; not the interface max
    return c;
}

// Read one interface's configuration from a `[net.<name>]` section.
//
// Order of decisions, and why:
// 1. `dhcp=yes` wins over static fields. A file with both is contradictory, and the
//    dynamic one is the safe reading: it cannot black-hole the machine with a stale
//    static address that no longer routes.
// 2. A static address without a mask is refused. There is no sensible default mask
//    for an address whose class means nothing today, and guessing /24 has put hosts on
//    the wrong network for decades.
// 3. An invalid address anywhere is an error for the whole interface, not a partial
//    configuration: half an interface configured is a machine that appears to work and
//    cannot reach anything.
fn iface_from_config(text: u8[:], name: const u8[:]) -> IfaceCfg, i64 {
    var c = iface_default(name);
    var cfg = cfg_init(text);

    // Section header is `net.<name>`. Built as a slice once, so the key lookups cannot
    // disagree about which section they asked for.
    var section: u8[>..] = [];
    let prefix = "net.";
    var p: i64 = 0;
    while p < prefix.len {
        section.push(prefix[p]);        // u8 in, u8 out: no literal-typing question
        p = p + 1;
    }
    var i: i64 = 0;
    while i < c.name_len {
        section.push(c.name[i]);
        i = i + 1;
    }
    let sec = section[..];

    let said_dhcp, dhcp_ok = cfg_bool(cfg, sec, "dhcp", false);
    if dhcp_ok && said_dhcp { c.use_dhcp = true; }

    // cfg_get pushes into a growable buffer and returns false when the key is absent or
    // the value is larger than the cap. One buffer per read, cleared by construction:
    // reusing a buffer without clearing it would parse `1.2.3.4` + `5.6.7.8` as one
    // string and produce an address nobody typed.
    var buf: u8[>..] = [];
    var got_addr = false;
    if cfg_get(cfg, sec, "address", buf, 16) {
        let parsed, ok = ip4_parse(buf[..]);
        if !ok { return c, E_INVAL; }
        c.addr = parsed;
        got_addr = true;
    }

    buf = [];
    if cfg_get(cfg, sec, "netmask", buf, 16) {
        let parsed, ok = ip4_parse(buf[..]);
        if !ok { return c, E_INVAL; }
        if !ip4_mask_contiguous(parsed) { return c, E_INVAL; }
        c.mask = parsed;
    }

    buf = [];
    if cfg_get(cfg, sec, "gateway", buf, 16) {
        let parsed, ok = ip4_parse(buf[..]);
        if !ok { return c, E_INVAL; }
        c.gw = parsed;
    }

    buf = [];
    if cfg_get(cfg, sec, "dns", buf, 16) {
        let parsed, ok = ip4_parse(buf[..]);
        if !ok { return c, E_INVAL; }
        c.dns1 = parsed;
    }

    let mtu_v, mtu_ok = cfg_int(cfg, sec, "mtu", 1500);
    if mtu_ok {
        if mtu_v < 576 || mtu_v > 1500 { return c, E_INVAL; }
        c.mtu = mtu_v;
    }

    // A static address with no mask is refused: there is no sensible default mask, and
    // guessing /24 has put hosts on the wrong network for decades.
    if got_addr && !c.use_dhcp && ip4_zero(c.mask) { return c, E_INVAL; }
    c.configured = got_addr || dhcp_ok;
    return c, CODE_OK;
}
