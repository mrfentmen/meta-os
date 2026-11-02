// services/net/arp.goose
//
// B-L1-96 — ARP request/reply and a small cache.
//
// Status: RUNS — reached by tests/t67_net (89 checks, exit 0). Measured 2026-11-02 by audit_status.py.
//
// THE CACHE IS THE PART THAT MATTERS
// ----------------------------------
// Building a request is twelve lines. The cache is where ARP gets dangerous: an entry with
// no expiry is a stale MAC that sends frames to a machine that moved, and an entry with no
// cap is a table an attacker fills with 4,096 invented addresses in a second. So the cache
// here has a fixed 8 slots, an age in milliseconds, and a rule that a full cache evicts the
// OLDEST entry rather than refusing the new one -- refusing would make the last host you
// talk to unreachable while a dead one keeps its slot.

import common.err.err;
import net.ip;
import netcfg.netcfg;

let ARP_HW_ETHER: i64 = 1;
let ARP_OP_REQUEST: i64 = 1;
let ARP_OP_REPLY: i64 = 2;
let ARP_LEN: i64 = 28;
let ARP_SLOTS: i64 = 8;
let ARP_TTL_MS: i64 = 60000;
let MAC_LEN: i64 = 6;

struct Mac {
    m0: i64, m1: i64, m2: i64, m3: i64, m4: i64, m5: i64,
}

struct ArpMsg {
    op: i64,
    sender_mac: Mac,
    sender_ip: Ipv4,
    target_mac: Mac,
    target_ip: Ipv4,
}

struct ArpEntry {
    used: bool,
    ip: Ipv4,
    mac: Mac,
    added_ms: i64,
}

var arp_table: ArpEntry[..8] = [ArpEntry { .. }; 8];
var arp_drops: i64 = 0;

fn mac(a: i64, b: i64, c: i64, d: i64, e: i64, f: i64) -> Mac {
    return Mac { m0: a, m1: b, m2: c, m3: d, m4: e, m5: f };
}

fn mac_zero() -> Mac {
    return Mac { m0: 0, m1: 0, m2: 0, m3: 0, m4: 0, m5: 0 };
}

fn mac_eq(x: Mac&, y: Mac&) -> bool {
    return x.m0 == y.m0 && x.m1 == y.m1 && x.m2 == y.m2 && x.m3 == y.m3 && x.m4 == y.m4 && x.m5 == y.m5;
}

fn mac_is_broadcast(x: Mac&) -> bool {
    return x.m0 == 0xff && x.m1 == 0xff && x.m2 == 0xff && x.m3 == 0xff && x.m4 == 0xff && x.m5 == 0xff;
}

fn arp_build(out: u8[..1500]&, op: i64, sha: Mac&, spa: Ipv4&, tha: Mac&, tpa: Ipv4&) -> i64, i64 {
    if op != ARP_OP_REQUEST && op != ARP_OP_REPLY { return 0, E_INVAL; }
    var i: i64 = 0;
    while i < ARP_LEN { out[i] = 0; i = i + 1; }
    out[0] = 0; out[1] = ARP_HW_ETHER as u8;    // hardware: ethernet
    // Protocol type 0x0800, network byte order: the 0x08 goes FIRST. It was written
    // the other way round, so every frame this stack built said protocol 0x0008 and
    // arp_parse -- correctly -- refused it. Build and parse disagreed about one field.
    out[2] = 0x08; out[3] = 0;
    out[4] = MAC_LEN as u8;
    out[5] = 4;
    out[6] = 0; out[7] = (op & 0xff) as u8;
    out[8] = sha.m0 as u8; out[9] = sha.m1 as u8; out[10] = sha.m2 as u8;
    out[11] = sha.m3 as u8; out[12] = sha.m4 as u8; out[13] = sha.m5 as u8;
    out[14] = spa.a as u8; out[15] = spa.b as u8; out[16] = spa.c as u8; out[17] = spa.d as u8;
    out[18] = tha.m0 as u8; out[19] = tha.m1 as u8; out[20] = tha.m2 as u8;
    out[21] = tha.m3 as u8; out[22] = tha.m4 as u8; out[23] = tha.m5 as u8;
    out[24] = tpa.a as u8; out[25] = tpa.b as u8; out[26] = tpa.c as u8; out[27] = tpa.d as u8;
    return ARP_LEN, CODE_OK;
}

// Parse strictly: wrong hardware type, wrong protocol, or a hardware/protocol length that is
// not 6/4 is E_UNSUPPORTED rather than "read it as ethernet anyway". A reply for a
// different link type is how a stack ends up caching an address it cannot use.
fn arp_parse(pkt: u8[..1500]&, len: i64) -> ArpMsg, i64 {
    var none = ArpMsg { op: 0, sender_mac: mac_zero(), sender_ip: ip4_any(), target_mac: mac_zero(), target_ip: ip4_any() };
    if len < ARP_LEN { return none, E_CORRUPT; }
    if (((pkt[0] as i64) << 8) | (pkt[1] as i64)) != ARP_HW_ETHER { return none, E_UNSUPPORTED; }
    if (((pkt[2] as i64) << 8) | (pkt[3] as i64)) != 0x0800 { return none, E_UNSUPPORTED; }
    if (pkt[4] as i64) != MAC_LEN || (pkt[5] as i64) != 4 { return none, E_UNSUPPORTED; }
    let op = ((pkt[6] as i64) << 8) | (pkt[7] as i64);
    if op != ARP_OP_REQUEST && op != ARP_OP_REPLY { return none, E_UNSUPPORTED; }
    return ArpMsg {
        op: op,
        sender_mac: mac(pkt[8] as i64, pkt[9] as i64, pkt[10] as i64, pkt[11] as i64, pkt[12] as i64, pkt[13] as i64),
        sender_ip: ip4(pkt[14] as u8, pkt[15] as u8, pkt[16] as u8, pkt[17] as u8),
        target_mac: mac(pkt[18] as i64, pkt[19] as i64, pkt[20] as i64, pkt[21] as i64, pkt[22] as i64, pkt[23] as i64),
        target_ip: ip4(pkt[24] as u8, pkt[25] as u8, pkt[26] as u8, pkt[27] as u8),
    }, CODE_OK;
}

// ---------------------------------------------------------------------------
// Cache
// ---------------------------------------------------------------------------

fn arp_cache_lookup(ipv: Ipv4&, now_ms: i64) -> Mac, bool {
    var i: i64 = 0;
    while i < ARP_SLOTS {
        if arp_table[i].used && ip4_equal(arp_table[i].ip, ipv) {
            if now_ms - arp_table[i].added_ms > ARP_TTL_MS {
                arp_table[i].used = false;        // expired: report a miss, and free the slot
                return mac_zero(), false;
            }
            return arp_table[i].mac, true;
        }
        i = i + 1;
    }
    return mac_zero(), false;
}

fn arp_cache_put(ipv: Ipv4&, macv: Mac&, now_ms: i64) {
    // Update in place when the address is already known, so a refresh does not consume a
    // second slot.
    var i: i64 = 0;
    while i < ARP_SLOTS {
        if arp_table[i].used && ip4_equal(arp_table[i].ip, ipv) {
            arp_table[i].mac = macv;
            arp_table[i].added_ms = now_ms;
            return;
        }
        i = i + 1;
    }
    // Free slot first.
    i = 0;
    while i < ARP_SLOTS {
        if !arp_table[i].used {
            arp_table[i].used = true;
            arp_table[i].ip = ipv;
            arp_table[i].mac = macv;
            arp_table[i].added_ms = now_ms;
            return;
        }
        i = i + 1;
    }
    // Full: evict the oldest. Refusing here would make the newest host unreachable while a
    // dead entry keeps its slot, which is the wrong failure to hand a user.
    var oldest: i64 = 0;
    i = 1;
    while i < ARP_SLOTS {
        if arp_table[i].added_ms < arp_table[oldest].added_ms { oldest = i; }
        i = i + 1;
    }
    arp_table[oldest].ip = ipv;
    arp_table[oldest].mac = macv;
    arp_table[oldest].added_ms = now_ms;
    arp_drops = arp_drops + 1;
}

fn arp_cache_clear() {
    var i: i64 = 0;
    while i < ARP_SLOTS {
        arp_table[i].used = false;
        arp_table[i].added_ms = 0;
        i = i + 1;
    }
}

fn arp_cache_count(now_ms: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < ARP_SLOTS {
        if arp_table[i].used && now_ms - arp_table[i].added_ms <= ARP_TTL_MS { n = n + 1; }
        i = i + 1;
    }
    return n;
}
