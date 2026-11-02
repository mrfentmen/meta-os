// services/net/udp.goose
//
// B-L1-98 — UDP datagrams.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE CHECKSUM, AND THE ONE HONEST SPECIAL CASE
// ---------------------------------------------
// A UDP checksum covers a pseudo-header (source, destination, zero, protocol, length) plus
// the datagram. Unlike TCP's it is optional in IPv4: a sender may put zero and mean "not
// computed". So the parse side treats zero as "unverified" and says so in its return --
// `E_UNSUPPORTED` would make every real UDP peer unusable, and accepting silently would
// hide the fact that the datagram was never checked.
//
// Everything else here refuses loudly: a length field that disagrees with the datagram is
// E_CORRUPT (that discrepancy is the classic UDP attack, where a receiver reads past the
// datagram into the next one).

import common.err.err;
import net.ip;
import netcfg.netcfg;

let UDP_HDR: i64 = 8;

struct UdpView {
    src_port: i64,
    dst_port: i64,
    payload_off: i64,
    payload_len: i64,
    checksum_ok: bool,     // false means "the sender did not compute one"
}

fn udp_pseudo_sum(src: Ipv4&, dst: Ipv4&, udp_len: i64) -> i64 {
    var sum: i64 = 0;
    sum = sum + (((src.a as i64) << 8) | (src.b as i64));
    sum = sum + (((src.c as i64) << 8) | (src.d as i64));
    sum = sum + (((dst.a as i64) << 8) | (dst.b as i64));
    sum = sum + (((dst.c as i64) << 8) | (dst.d as i64));
    sum = sum + IP_PROTO_UDP;
    sum = sum + udp_len;
    return sum;
}

fn udp_sum16(buf: u8[..1500]&, off: i64, len: i64) -> i64 {
    var sum: i64 = 0;
    var i = off;
    while i + 1 < off + len {
        sum = sum + (((buf[i] as i64) << 8) | (buf[i + 1] as i64));
        i = i + 2;
    }
    if (len % 2) != 0 { sum = sum + ((buf[off + len - 1] as i64) << 8); }
    while sum > 0xffff { sum = (sum & 0xffff) + (sum >> 16); }
    return sum;
}

fn udp_build(out: u8[..1500]&, src: Ipv4&, dst: Ipv4&, sport: i64, dport: i64, payload: const u8[:]) -> i64, i64 {
    let udp_len = UDP_HDR + payload.len;
    if udp_len > 1480 { return 0, E_NOROOM; }      // 1500 - 20 IP
    if sport < 1 || sport > 65535 || dport < 1 || dport > 65535 { return 0, E_INVAL; }
    out[0] = ((sport >> 8) & 0xff) as u8;
    out[1] = (sport & 0xff) as u8;
    out[2] = ((dport >> 8) & 0xff) as u8;
    out[3] = (dport & 0xff) as u8;
    out[4] = ((udp_len >> 8) & 0xff) as u8;
    out[5] = (udp_len & 0xff) as u8;
    out[6] = 0; out[7] = 0;
    var i: i64 = 0;
    while i < payload.len { out[UDP_HDR + i] = payload[i]; i = i + 1; }

    var sum = udp_pseudo_sum(src, dst, udp_len);
    sum = sum + udp_sum16(out, 0, udp_len);
    while sum > 0xffff { sum = (sum & 0xffff) + (sum >> 16); }
    var csum = (~sum) & 0xffff;
    // A computed zero is transmitted as 0xffff: zero on the wire means "no checksum", so a
    // real checksum that happens to be zero would be read as absent.
    if csum == 0 { csum = 0xffff; }
    out[6] = ((csum >> 8) & 0xff) as u8;
    out[7] = (csum & 0xff) as u8;
    return udp_len, CODE_OK;
}

fn udp_parse(dgram: u8[..1500]&, len: i64, src: Ipv4&, dst: Ipv4&) -> UdpView, i64 {
    var none = UdpView { src_port: 0, dst_port: 0, payload_off: 0, payload_len: 0, checksum_ok: false };
    if len < UDP_HDR { return none, E_CORRUPT; }
    let declared = (((dgram[4] as i64) << 8) | (dgram[5] as i64));
    if declared < UDP_HDR { return none, E_CORRUPT; }
    // The length field must equal the datagram, not merely fit inside it. A shorter declared
    // length is the overlap attack; a longer one reads past the buffer.
    if declared != len { return none, E_CORRUPT; }

    let stored = (((dgram[6] as i64) << 8) | (dgram[7] as i64));
    var ok = false;
    if stored == 0 {
        ok = false;                                 // sender did not compute one
    } else {
        dgram[6] = 0; dgram[7] = 0;
        var sum = udp_pseudo_sum(src, dst, len);
        sum = sum + udp_sum16(dgram, 0, len);
        while sum > 0xffff { sum = (sum & 0xffff) + (sum >> 16); }
        ok = ((~sum) & 0xffff) == 0;
        dgram[6] = ((stored >> 8) & 0xff) as u8;
        dgram[7] = (stored & 0xff) as u8;
        if !ok { return none, E_CORRUPT; }
    }
    return UdpView {
        src_port: (((dgram[0] as i64) << 8) | (dgram[1] as i64)),
        dst_port: (((dgram[2] as i64) << 8) | (dgram[3] as i64)),
        payload_off: UDP_HDR,
        payload_len: declared - UDP_HDR,
        checksum_ok: ok,
    }, CODE_OK;
}
