# Contract note — R13-011, dhcp input validation

Status: **AUDITED — 2 gaps filed**.
Facet: which inputs are refused before a packet can become a lease, and which error each refusal returns.

## Evidence

Command:

```sh
nl -ba services/dhcp/dhcp.goose | sed -n '202,273p'
```

Relevant output:

```text
207  fn dhcp_parse(pkt: const u8[:], out: Lease&) -> i64 {
208      if pkt.len < 240 { return E_CORRUPT; }
209      if pkt[0] != 2 { return E_CORRUPT; }
210      if pkt[1] != 1 || pkt[2] != 6 { return E_CORRUPT; }
211      if pkt[236] != DHCP_MAGIC_0 || ... { return E_CORRUPT; }
235      if i + 1 >= pkt.len { return E_CORRUPT; }
237      if i + 2 + len > pkt.len { return E_CORRUPT; }
267      if ip4_zero(out.addr) { return E_NO_ADDRESS; }
268      if out.lease_ms <= 0 { return E_INVAL; }
269      if !out.mask_given { return E_NO_MASK; }
```

## Corrected contract

`dhcp_parse` is the only gate between bytes and a `Lease`. It refuses, in order:

| Input | Code |
|---|---|
| shorter than 240 bytes | `E_CORRUPT` |
| `op != 2`, `htype != 1`, `hlen != 6` | `E_CORRUPT` |
| missing magic cookie | `E_CORRUPT` |
| option with no length byte, or length past packet | `E_CORRUPT` |
| `yiaddr == 0.0.0.0` | `E_NO_ADDRESS` |
| lease time missing or zero | `E_INVAL` |
| no *contiguous* subnet mask | `E_NO_MASK` |

Unknown options are skipped. A packet that passes returns a lease whose T1/T2 default to 1/2 and 7/8 of the lease.

## Mismatches

- **R13-011-G1** — a known option shorter than its fixed width is skipped, not refused. The
  README's table only covers lengths that run *past* the packet.
- **R13-011-G2** — a present but non-contiguous mask is collapsed to `E_NO_MASK`, the same
  code as an absent mask, so the caller cannot tell “not offered” from “offered and malformed”.
  See `services/dhcp/GAPS_R13.md`.
