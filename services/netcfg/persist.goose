// services/netcfg/persist.goose
//
// B-L1-104 — Network configuration persistence.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE FORMAT IS THE ONE iface_from_config ALREADY READS
// -----------------------------------------------------
// There is no second format here. `netcfg_render` emits exactly the `[net.<name>]` section
// that `iface_from_config` (netcfg.goose) parses, and `netcfg_load` reads a file straight
// into that same function. A save format separate from the read format is two grammars to
// keep in step, and the day they drift is the day a machine boots with no address and a
// perfectly valid-looking config file.
//
// WHAT IS WRITTEN, AND WHAT IS NOT
// -------------------------------
// - `dhcp=yes` is written when the interface is dynamic. When it is, the driver's
//   discovered address is NOT written: an address learned from DHCP is not configuration,
//   and persisting it would pin a lease to a machine that has since moved.
// - A zero address is omitted rather than written as 0.0.0.0, because 0.0.0.0 is a
//   legitimate "unset" only by accident -- a file that says `address=0.0.0.0` and one that
//   says nothing must not mean the same thing to a reader that validates.
// - The file is small, fixed-capacity (NETCFG_TEXT_MAX), and rewritten whole. There is no
//   in-place patching: a partially rewritten config after a power cut is worse than the
//   previous one, which is why `netcfg_save` truncates and writes in that order and the
//   caller is expected to have the old text in hand.

import common.err.err;
import common.fmt.fmt;
import netcfg.netcfg;
import fs.fs;

let NETCFG_TEXT_MAX: i64 = 512;

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

// Render one interface as a config section. Returns the byte count, or -1 when the text
// does not fit -- never a truncated section, since a half section parses as a different
// configuration than the one that was saved.
fn netcfg_render(c: IfaceCfg&, out: u8[>..]&, cap: i64) -> i64 {
    if !append_str(out, cap, "[net.") { return -1; }
    var i: i64 = 0;
    while i < c.name_len {
        if !append_char(out, cap, c.name[i]) { return -1; }
        i++;
    }
    if !append_str(out, cap, "]\n") { return -1; }

    if c.use_dhcp {
        if !netcfg_kv_bool(out, cap, "dhcp", true) { return -1; }
        // Address, mask and gateway are deliberately absent: see the header.
    } else {
        if !netcfg_kv_bool(out, cap, "dhcp", false) { return -1; }
        if !netcfg_kv_ip(out, cap, "address", c.addr) { return -1; }
        if !netcfg_kv_ip(out, cap, "netmask", c.mask) { return -1; }
        if !netcfg_kv_ip(out, cap, "gateway", c.gw) { return -1; }
    }
    if !netcfg_kv_ip(out, cap, "dns", c.dns1) { return -1; }
    if !ip4_zero(c.dns2) {
        // The section format carries one nameserver. A second is reported rather than
        // silently dropped, because dropping it changes what the machine resolves.
        return -2;
    }
    if c.mtu > 0 {
        if !append_str(out, cap, "mtu=") { return -1; }
        if !append_int(out, cap, c.mtu) { return -1; }
        if !append_char(out, cap, '\n') { return -1; }
    }
    return used(out);
}

fn netcfg_kv_bool(out: u8[>..]&, cap: i64, key: const u8[:], v: bool) -> bool {
    if !append_str(out, cap, key) { return false; }
    if !append_char(out, cap, '=') { return false; }
    if !append_bool(out, cap, v) { return false; }
    return append_char(out, cap, '\n');
}

// A zero address writes nothing at all: absent and 0.0.0.0 must not be the same statement.
fn netcfg_kv_ip(out: u8[>..]&, cap: i64, key: const u8[:], addr: Ipv4&) -> bool {
    if ip4_zero(addr) { return true; }
    if !append_str(out, cap, key) { return false; }
    if !append_char(out, cap, '=') { return false; }
    var text: u8[..16];
    let n = ip4_render(addr, text);
    if n <= 0 { return false; }
    if !append_str(out, cap, text[..n]) { return false; }
    return append_char(out, cap, '\n');
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

// Write the interface's section over whatever the inode held.
//
// Truncate first, then write: fs_write refuses a gap (off > size), which is the property
// that makes the ordering matter rather than being a style choice.
fn netcfg_save(ino: i64, c: IfaceCfg&) -> i64 {
    var text: u8[>..] = [];
    let n = netcfg_render(c, text, NETCFG_TEXT_MAX);
    if n == -2 { return E_UNSUPPORTED; }    // a second nameserver cannot be expressed
    if n < 0 { return E_NOROOM; }

    let tcode = fs_truncate(ino);
    if tcode != CODE_OK { return tcode; }
    let wrote, wcode = fs_write(ino, 0, text[..]);
    if wcode != CODE_OK { return wcode; }
    if wrote != n { return E_IO; }          // short write: not a success
    return CODE_OK;
}

// Read the section back out of the inode and parse it with the one parser there is.
// Returns (iface, code); on any failure the iface is the documented default for `name`,
// so a caller that ignores the code still gets a value that cannot route anywhere.
fn netcfg_load(ino: i64, name: const u8[:]) -> IfaceCfg, i64 {
    var text: u8[>..] = [];
    let n, rcode = fs_read(ino, 0, text, NETCFG_TEXT_MAX);
    if rcode != CODE_OK { return iface_default(name), rcode; }
    if n == 0 { return iface_default(name), E_NOTFOUND; }
    return iface_from_config(text[..], name);
}
