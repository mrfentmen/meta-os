# Contract note — R13-022, net fixture coverage

Status: **AUDITED — 2 gaps filed**.
Facet: which network fixtures exist, which code paths they cover, and which successful paths are
not covered.

## Evidence

Commands:

```sh
ls -1 services/tests | grep -Ei 'net|packet|dhcp|dns|socket|loopback'
find services/tests os-build -type f \( -iname '*net*' -o -iname '*fixture*' -o -iname '*.pcap' \)
grep -nEi 'var .*pkt|\[0x' services/tests/t125_net_r11.goose services/tests/t67_net.goose
```

Relevant output:

```text
t101_netaddr.goose
t114_dhcp_r11.goose
t116_dns_r11.goose
t125_net_r11.goose
t126_netcfg_r11.goose
t57_dhcp_dns.goose
t67_net.goose
t85_net_deep.goose
```

No `.pcap` or fixture data file exists. `t67_net.goose:61` builds `var pkt: u8[..1500] = [0; 1500]`
inline; the other tests do the same.

## Corrected contract

The corpus is eight Goose test programs, all with frames and packets constructed in code. There is
no captured-packet fixture set and no replay file. Coverage is:

| Area | Driver |
|---|---|
| Ethernet/IP/ARP/ICMP/UDP/TCP helpers | `t67_net`, `t85_net_deep` |
| packet interface refusals and drop counter | `t125_net_r11` |
| IPv4 parsing and masks | `t101_netaddr` |
| DHCP parser and lease clock | `t57_dhcp_dns`, `t114_dhcp_r11` |
| DNS query/parse and jump cap | `t57_dhcp_dns`, `t116_dns_r11` |
| interface config and persistence | `t126_netcfg_r11` |

The host shim refuses every `sys_net_send` frame, so successful transmit and receive through the
kernel are not covered. Loopback delivery is the one completed path.

## Mismatches

- **R13-022-G1** — no captured fixture corpus; every test frame is hand-built in Goose.
- **R13-022-G2** — the real send/receive path is unproven because the host shim refuses every
  frame. See `services/net/GAPS_R13.md`.
