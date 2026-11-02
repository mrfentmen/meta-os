// services/tests/t126_netcfg_r11.goose
//
// Round 11 — netcfg: the parser's refusals, the mask rules, and a render/parse round trip.
//
// WHAT THIS ADDS
// --------------
// t67 proves the happy parse. t79 and t80 name IF_NAME_MAX and NETCFG_TEXT_MAX. Neither
// asserts the leading-zero refusal, the /0 and /32 mask ends, the non-contiguous mask, the
// "dhcp wins over static" rule, the MTU window's exact edges, or that what `netcfg_render`
// writes is what `iface_from_config` reads back. That last one is the property the two
// functions exist for: two formats would drift, and the drift would boot a machine with no
// address and a valid-looking file.
//
// The filesystem half of persistence (save/load through an inode) is t80's; this file keeps
// to the render/parse contract and says so.

import netcfg.netcfg;
import netcfg.persist;
import common.err.err;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn lit(s: const u8[:], out: u8[..512]&) -> i64 {
    var i: i64 = 0;
    while i < s.len { out[i] = s[i]; i = i + 1; }
    return s.len;
}

fn same(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn has(hay: const u8[:], needle: const u8[:]) -> bool {
    if needle.len > hay.len { return false; }
    var i: i64 = 0;
    while i + needle.len <= hay.len {
        var k: i64 = 0;
        var ok = true;
        while k < needle.len {
            if hay[i + k] != needle[k] { ok = false; k = needle.len; }
            else { k = k + 1; }
        }
        if ok { return true; }
        i = i + 1;
    }
    return false;
}

fn eq4(x: Ipv4, y: Ipv4) -> bool {
    return x.a == y.a && x.b == y.b && x.c == y.c && x.d == y.d;
}

fn t_parse() {
    say("-- ip4_parse is strict\n");

    let a, oka = ip4_parse("10.0.2.15");
    check("parse: a normal address", oka && a.a == 10 && a.b == 0 && a.c == 2 && a.d == 15);
    let z, okz = ip4_parse("0.0.0.0");
    check("parse: 0.0.0.0 is a legal address", okz && ip4_zero(z));
    let b, okb = ip4_parse("255.255.255.255");
    var all = ip4_broadcast();
    check("parse: broadcast parses", okb && eq4(b, all));

    let _x1, ox1 = ip4_parse("010.0.2.1");
    check("parse: a leading zero is refused (octal-looking)", !ox1);
    let _x2, ox2 = ip4_parse("1.2.3.256");
    check("parse: 256 is refused", !ox2);
    let _x3, ox3 = ip4_parse("1.2.3");
    check("parse: three parts is refused", !ox3);
    let _x4, ox4 = ip4_parse("1.2.3.4.5");
    check("parse: five parts is refused", !ox4);
    let _x5, ox5 = ip4_parse("1..3.4");
    check("parse: an empty part is refused", !ox5);
    let _x6, ox6 = ip4_parse("1.2.3.");
    check("parse: a trailing dot is refused", !ox6);
    let _x7, ox7 = ip4_parse("1.2.3.a");
    check("parse: a letter is refused", !ox7);
    let _x8, ox8 = ip4_parse("");
    check("parse: an empty string is refused", !ox8);
    let _x9, ox9 = ip4_parse("1.2.3.1000");
    check("parse: four digits in a part is refused", !ox9);

    var text: u8[..16] = [0; 16];
    let n = ip4_render(a, text);
    check("render: the address renders", n == 9 && same(text[..n], "10.0.2.15"));
    var t3: u8[..16] = [0; 16];
    var a2 = ip4(1, 22, 3, 255);
    let n3 = ip4_render(a2, t3);
    check("render: one-, two- and three-digit octets", n3 == 10 && same(t3[..n3], "1.22.3.255"));
}

fn t_masks() {
    say("-- masks and subnets\n");

    let m24, ok24 = ip4_mask(24);
    check("mask: /24", ok24 && m24.a == 255 && m24.b == 255 && m24.c == 255 && m24.d == 0);
    let m0, ok0 = ip4_mask(0);
    check("mask: /0 is legal and empty", ok0 && ip4_zero(m0));
    let m32, ok32 = ip4_mask(32);
    var full_mask = ip4_broadcast();
    check("mask: /32 is legal and full", ok32 && eq4(m32, full_mask));
    let _m33, ok33 = ip4_mask(33);
    check("mask: /33 is refused", !ok33);
    let _mn, okn = ip4_mask(-1);
    check("mask: a negative prefix is refused", !okn);

    var c1 = ip4(255, 255, 255, 0);
    check("mask: 255.255.255.0 is contiguous", ip4_mask_contiguous(c1));
    var c2m = ip4(255, 0, 255, 0);
    check("mask: 255.0.255.0 is not", !ip4_mask_contiguous(c2m));
    check("mask: 255.255.255.255 is contiguous", ip4_mask_contiguous(full_mask));
    var zero4 = ip4_any();
    check("mask: 0.0.0.0 is contiguous", ip4_mask_contiguous(zero4));
    var c3 = ip4(255, 255, 254, 0);
    check("mask: 255.255.254.0 is contiguous", ip4_mask_contiguous(c3));

    var local = ip4(10, 0, 2, 15);
    var same = ip4(10, 0, 2, 99);
    var othernet = ip4(10, 0, 3, 1);
    check("subnet: 10.0.2.99 is in 10.0.2.0/24", ip4_same_subnet(local, same, m24));
    check("subnet: 10.0.3.1 is not", !ip4_same_subnet(local, othernet, m24));
    let bc = ip4_subnet_broadcast(local, m24);
    var want_bc = ip4(10, 0, 2, 255);
    check("subnet: the directed broadcast is .255", eq4(bc, want_bc));
}

fn t_iface() {
    say("-- interface configuration: every refusal\n");

    var d = iface_default("eth0");
    check("iface_default: name stored", d.name_len == 4);
    check("iface_default: not configured", !d.configured && !d.use_dhcp);
    check("iface_default: the default MTU is 1500", d.mtu == 1500);
    var long_name = iface_default("abcdefghij");
    check("iface_default: the name is cut at IF_NAME_MAX-1", long_name.name_len == IF_NAME_MAX - 1);

    var text: u8[..512] = [0; 512];
    var n = lit("[net.eth0]\naddress=10.0.2.15\nnetmask=255.255.255.0\n", text);
    let c, code = iface_from_config(text[..n], "eth0");
    check("iface: static config is accepted", code == CODE_OK && c.configured);
    var want_addr = ip4(10, 0, 2, 15);
    var want_mask = ip4(255, 255, 255, 0);
    check("iface: the address is stored", eq4(c.addr, want_addr));
    check("iface: the mask is stored", eq4(c.mask, want_mask));
    check("iface: no DHCP", !c.use_dhcp);

    // dhcp=yes wins over static fields: the dynamic reading cannot black-hole the machine.
    n = lit("[net.eth0]\ndhcp=yes\naddress=10.0.2.15\nnetmask=255.255.255.0\n", text);
    let cd, coded = iface_from_config(text[..n], "eth0");
    check("iface: dhcp wins over static fields", coded == CODE_OK && cd.use_dhcp && cd.configured);

    n = lit("[net.eth0]\naddress=10.0.2.15\n", text);
    let _c1, code1 = iface_from_config(text[..n], "eth0");
    check("iface: a static address with no mask is E_INVAL", code1 == E_INVAL);

    n = lit("[net.eth0]\naddress=10.0.2.999\nnetmask=255.255.255.0\n", text);
    let _c2, code2 = iface_from_config(text[..n], "eth0");
    check("iface: an invalid address fails the whole interface", code2 == E_INVAL);

    n = lit("[net.eth0]\naddress=10.0.2.15\nnetmask=255.0.255.0\n", text);
    let _c3, code3 = iface_from_config(text[..n], "eth0");
    check("iface: a non-contiguous mask is E_INVAL", code3 == E_INVAL);

    n = lit("[net.eth0]\naddress=10.0.2.15\nnetmask=255.255.255.0\nmtu=575\n", text);
    let _c4, code4 = iface_from_config(text[..n], "eth0");
    check("iface: mtu 575 is E_INVAL", code4 == E_INVAL);
    n = lit("[net.eth0]\naddress=10.0.2.15\nnetmask=255.255.255.0\nmtu=1501\n", text);
    let _c5, code5 = iface_from_config(text[..n], "eth0");
    check("iface: mtu 1501 is E_INVAL", code5 == E_INVAL);
    n = lit("[net.eth0]\naddress=10.0.2.15\nnetmask=255.255.255.0\nmtu=576\n", text);
    let _c6, code6 = iface_from_config(text[..n], "eth0");
    check("iface: mtu 576 is accepted", code6 == CODE_OK);
    n = lit("[net.eth0]\naddress=10.0.2.15\nnetmask=255.255.255.0\nmtu=1500\n", text);
    let _c7, code7 = iface_from_config(text[..n], "eth0");
    check("iface: mtu 1500 is accepted", code7 == CODE_OK);

    n = lit("[net.eth1]\naddress=10.0.2.15\nnetmask=255.255.255.0\n", text);
    let other, code8 = iface_from_config(text[..n], "eth0");
    check("iface: another interface's section does not configure this one",
          code8 == CODE_OK && !other.configured);
}

fn t_round_trip() {
    say("-- render, then parse: one format, not two\n");

    var text: u8[..512] = [0; 512];
    let n = lit("[net.eth0]\naddress=10.0.2.15\nnetmask=255.255.255.0\ngateway=10.0.2.1\ndns=10.0.2.2\nmtu=1400\n", text);
    let c, code = iface_from_config(text[..n], "eth0");
    check("round trip: the source config parses", code == CODE_OK);

    var out: u8[>..] = [];
    let rn = netcfg_render(c, out, NETCFG_TEXT_MAX);
    check("round trip: render succeeds", rn > 0);
    check("round trip: the section header is written", has(out[..rn], "[net.eth0]"));
    check("round trip: dhcp=false is written", has(out[..rn], "dhcp=false"));
    check("round trip: the address is written", has(out[..rn], "address=10.0.2.15"));
    check("round trip: the MTU is written", has(out[..rn], "mtu=1400"));

    var round: u8[..512] = [0; 512];
    var i: i64 = 0;
    while i < rn { round[i] = out[i]; i = i + 1; }
    let c2, code2 = iface_from_config(round[..rn], "eth0");
    check("round trip: the rendered text parses", code2 == CODE_OK);
    check("round trip: the address survives", eq4(c2.addr, c.addr));
    check("round trip: the mask survives", eq4(c2.mask, c.mask));
    check("round trip: the gateway survives", eq4(c2.gw, c.gw));
    check("round trip: the DNS survives", eq4(c2.dns1, c.dns1));
    check("round trip: the MTU survives", c2.mtu == 1400);

    // A dynamic interface writes no address at all: an address learned from DHCP is not
    // configuration, and persisting it would pin a lease to a machine that moved.
    var dyn = iface_default("eth0");
    dyn.use_dhcp = true;
    dyn.addr = ip4(10, 0, 2, 15);
    dyn.mask = ip4(255, 255, 255, 0);
    var dout: u8[>..] = [];
    let dn = netcfg_render(dyn, dout, NETCFG_TEXT_MAX);
    check("round trip: a dynamic interface renders", dn > 0 && has(dout[..dn], "dhcp=true"));
    check("round trip: a dynamic interface writes no address", !has(dout[..dn], "address="));

    // A second nameserver cannot be expressed in the section format. -2 is the service
    // saying so rather than dropping it silently.
    var two = iface_default("eth0");
    two.dns1 = ip4(10, 0, 2, 2);
    two.dns2 = ip4(10, 0, 2, 3);
    var tout: u8[>..] = [];
    check("round trip: a second nameserver is refused, not dropped",
          netcfg_render(two, tout, NETCFG_TEXT_MAX) == -2);

    // The cap is a cap: a render that does not fit says so and writes no partial section.
    var small: u8[>..] = [];
    check("round trip: a cap too small is E_NOROOM-sized (-1)",
          netcfg_render(c, small, 8) == -1);
}

fn t_load() {
    say("-- load: 100 render/parse round trips\n");

    var text: u8[..512] = [0; 512];
    let n = lit("[net.eth0]\naddress=10.0.2.15\nnetmask=255.255.255.0\nmtu=1500\n", text);
    let c, _code = iface_from_config(text[..n], "eth0");
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    var i: i64 = 0;
    while i < 100 {
        var out: u8[>..] = [];
        let rn = netcfg_render(c, out, NETCFG_TEXT_MAX);
        var round: u8[..512] = [0; 512];
        var k: i64 = 0;
        while k < rn { round[k] = out[k]; k = k + 1; }
        let c2, code2 = iface_from_config(round[..rn], "eth0");
        ops = ops + 1;
        if rn > 0 && code2 == CODE_OK && eq4(c2.addr, c.addr) { ok = ok + 1; }
        else { refused = refused + 1; }
        i = i + 1;
    }
    check("load: every round trip agreed", ok == ops);
    say("LOAD netcfg ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    ob = [];
    let _ = append_int(ob, 32, ok);
    say(ob[..]);
    say(" refused=");
    ob = [];
    let _ = append_int(ob, 32, refused);
    say(ob[..]);
    say("\n");
}

fn main() {
    say("t126 netcfg r11\n");
    t_parse();
    t_masks();
    t_iface();
    t_round_trip();
    t_load();
    say("t126 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
