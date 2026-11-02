// services/tests/t101_netaddr.goose
//
// The address arithmetic under the network stack: loopback's own contract, the directed
// broadcast, the prefix-to-mask conversion, and "is this frame addressed to everyone".
//
// WHY THIS FILE EXISTS
// --------------------
// The census listed `lo_mask`, `lo_configured`, `lo_route`, `lo_source_for`, `mac_is_broadcast`,
// `ip4_mask` and `ip4_subnet_broadcast` as functions nothing calls. Every one of them decides
// where a packet goes or who receives it, and the failure mode of getting one wrong is silent:
// a packet with the wrong source address is not an error, it is a packet nothing answers, and a
// frame sent to the wrong broadcast address is not an error either, it is a packet that never
// arrives. So the route decision is driven at every branch, including the two refusals.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import net.loopback;
import net.arp;
import net.ip;
import netcfg.netcfg;
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

fn same4(x: Ipv4, a: u8, b: u8, c: u8, d: u8) -> bool {
    return x.a == a && x.b == b && x.c == c && x.d == d;
}

fn main() {
    say("t101 network addresses\n");

    // ======================================================================
    // 1. loopback: its mask, and that it is always up
    // ======================================================================
    let lm = lo_mask();
    check("lo_mask: 127.0.0.1 is in a /8", same4(lm, 255, 0, 0, 0));
    check("lo_mask: the mask is contiguous", ip4_mask_contiguous(lm));
    check("lo_configured: always true, nothing configures loopback", lo_configured());

    // ======================================================================
    // 2. route selection: the four answers, and the two refusals
    // ======================================================================
    let local = ip4(192, 168, 1, 10);
    let mask24 = ip4(255, 255, 255, 0);
    let gw = ip4(192, 168, 1, 1);
    let zero = ip4(0, 0, 0, 0);

    // 127.0.0.0/8 is loopback, not only .1: a stack that special-cases the one address sends
    // 127.0.0.5 out on the wire, where nothing answers.
    let r_lo, c_lo = lo_route(ip4(127, 0, 0, 5), local, mask24, gw);
    check("lo_route: any address in 127/8 is local", r_lo == 0 && c_lo == CODE_OK);
    let r_lo1, _ = lo_route(ip4(127, 0, 0, 1), local, mask24, gw);
    check("lo_route: 127.0.0.1 is local too", r_lo1 == 0);

    // The host's own address is delivered locally, not ARPed for.
    let r_self, c_self = lo_route(local, local, mask24, gw);
    check("lo_route: the interface's own address is local", r_self == 1 && c_self == CODE_OK);

    // Same subnet: send directly.
    let r_sub, c_sub = lo_route(ip4(192, 168, 1, 20), local, mask24, gw);
    check("lo_route: a neighbour on the subnet goes direct", r_sub == 2 && c_sub == CODE_OK);

    // Off-subnet with a gateway: hand it to the gateway.
    let r_gw, c_gw = lo_route(ip4(8, 8, 8, 8), local, mask24, gw);
    check("lo_route: off-subnet goes via the gateway", r_gw == 3 && c_gw == CODE_OK);

    // Off-subnet with no gateway is unreachable, not "send it anyway".
    let r_nogw, c_nogw = lo_route(ip4(8, 8, 8, 8), local, mask24, zero);
    check("lo_route: off-subnet with no gateway is unreachable", r_nogw == -1 && c_nogw == E_UNREACHABLE);

    // An unconfigured interface fails to send rather than sourcing from 0.0.0.0, which is how a
    // packet gets a source address no reply can reach.
    let r_noaddr, c_noaddr = lo_route(ip4(8, 8, 8, 8), zero, mask24, gw);
    check("lo_route: an unconfigured interface has no route", r_noaddr == -1 && c_noaddr == E_NO_ADDRESS);

    // Order matters: loopback is decided before the interface is consulted, so a machine with no
    // address can still talk to itself.
    let r_lo_noaddr, c_lo_noaddr = lo_route(ip4(127, 0, 0, 1), zero, mask24, gw);
    check("lo_route: loopback works on an unconfigured interface",
          r_lo_noaddr == 0 && c_lo_noaddr == CODE_OK);

    // A destination on the subnet of a zero gateway is still direct: the gateway is only
    // consulted when the subnet check fails.
    let r_sub_nogw, _ = lo_route(ip4(192, 168, 1, 44), local, mask24, zero);
    check("lo_route: a local peer does not need a gateway", r_sub_nogw == 2);

    // ======================================================================
    // 3. source address selection
    // ======================================================================
    check("lo_source_for: loopback traffic sources from 127.0.0.1",
          same4(lo_source_for(0, local), 127, 0, 0, 1));
    check("lo_source_for: a direct send sources from the interface",
          same4(lo_source_for(2, local), 192, 168, 1, 10));
    check("lo_source_for: a gatewayed send sources from the interface",
          same4(lo_source_for(3, local), 192, 168, 1, 10));

    // ======================================================================
    // 4. ARP: the broadcast MAC, exactly
    // ======================================================================
    let bc = mac(255, 255, 255, 255, 255, 255);
    check("mac_is_broadcast: ff:ff:ff:ff:ff:ff", mac_is_broadcast(bc));
    check("mac_is_broadcast: one bit off is not broadcast",
          !mac_is_broadcast(mac(255, 255, 255, 255, 255, 254)));
    check("mac_is_broadcast: the zero MAC is not broadcast", !mac_is_broadcast(mac_zero()));
    check("mac_is_broadcast: a multicast MAC is not broadcast",
          !mac_is_broadcast(mac(1, 0, 94, 0, 0, 1)));

    // ======================================================================
    // 5. prefix to mask
    // ======================================================================
    let m0v, m0ok = ip4_mask(0);
    check("ip4_mask: /0 is a legal mask of zero", m0ok && same4(m0v, 0, 0, 0, 0));
    let m8v, m8ok = ip4_mask(8);
    check("ip4_mask: /8", m8ok && same4(m8v, 255, 0, 0, 0));
    let m24v, m24ok = ip4_mask(24);
    check("ip4_mask: /24", m24ok && same4(m24v, 255, 255, 255, 0));
    let m25v, m25ok = ip4_mask(25);
    check("ip4_mask: /25 splits the last byte at the high bit", m25ok && same4(m25v, 255, 255, 255, 128));
    let m26v, m26ok = ip4_mask(26);
    check("ip4_mask: /26", m26ok && same4(m26v, 255, 255, 255, 192));
    let m31v, m31ok = ip4_mask(31);
    check("ip4_mask: /31", m31ok && same4(m31v, 255, 255, 255, 254));
    let m32v, m32ok = ip4_mask(32);
    check("ip4_mask: /32 is a legal mask of everything", m32ok && same4(m32v, 255, 255, 255, 255));

    // Every prefix produces a contiguous mask: a non-contiguous one makes every subnet test
    // below meaningless, and a loop that got the byte boundary wrong would show up here.
    var all_contiguous = true;
    var pfx: i64 = 0;
    while pfx <= 32 {
        let pm, pok = ip4_mask(pfx);
        if !pok || !ip4_mask_contiguous(pm) { all_contiguous = false; }
        pfx = pfx + 1;
    }
    check("ip4_mask: every prefix from 0 to 32 is contiguous", all_contiguous);

    let _, m33ok = ip4_mask(33);
    check("ip4_mask: /33 is refused", !m33ok);
    let _, mnegok = ip4_mask(-1);
    check("ip4_mask: a negative prefix is refused", !mnegok);

    // ======================================================================
    // 6. directed broadcast
    // ======================================================================
    let b24 = ip4_subnet_broadcast(local, mask24);
    check("ip4_subnet_broadcast: 192.168.1.10/24 is 192.168.1.255",
          same4(b24, 192, 168, 1, 255));
    let b8 = ip4_subnet_broadcast(ip4(10, 1, 2, 3), m8v);
    check("ip4_subnet_broadcast: 10.1.2.3/8 is 10.255.255.255", same4(b8, 10, 255, 255, 255));
    let b32 = ip4_subnet_broadcast(ip4(10, 1, 2, 3), m32v);
    check("ip4_subnet_broadcast: a /32 broadcast is the address itself",
          same4(b32, 10, 1, 2, 3));
    let b0 = ip4_subnet_broadcast(ip4(10, 1, 2, 3), m0v);
    check("ip4_subnet_broadcast: /0 broadcast is 255.255.255.255",
          same4(b0, 255, 255, 255, 255));

    // The broadcast is the last address of the subnet, so the address itself must be in it.
    check("ip4_subnet_broadcast: the host is on the subnet it broadcasts to",
          ip4_same_subnet(local, b24, mask24));

    say("t101 done  pass=");
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
