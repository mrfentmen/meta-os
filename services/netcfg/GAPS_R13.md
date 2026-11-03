# Gap records — R13-023 netcfg

## R13-023-G1 — README says MTU is clamped; code refuses it

- **Claim:** “MTU is clamped to 576..1500.”
- **Reality:** `if mtu_v < 576 || mtu_v > 1500 { return c, E_INVAL; }` — no clamp, no default
  substitution. The caller gets an invalid config back with an error code.
- **Evidence:** `services/netcfg/README.md` configuration rule 4; `services/netcfg/netcfg.goose:339-343`.
- **Impact:** a caller that trusts “clamped” and ignores the code carries an `IfaceCfg` with the
  previous/default MTU, which is safe, but the documented recovery path is wrong. A test expecting
  a clamp would fail.
- **Owner:** netcfg README; `tests/t126_netcfg_r11`.

## R13-023-G2 — `configured` is set by `dhcp=no`

- **Claim:** `IfaceCfg.configured` records whether the interface has an address or dynamic config.
- **Reality:** `c.configured = got_addr || dhcp_ok` (line 348). `dhcp_ok` is the parse-success flag,
  not `said_dhcp`, so `dhcp=no` alone sets `configured = true` with no address, mask or DHCP.
- **Evidence:** `services/netcfg/netcfg.goose:301-302` and `:348`.
- **Impact:** a reader of `configured` can believe an interface is usable when it has no address.
  The README's distinction between “unset” and `0.0.0.0` is weakened at this field.
- **Owner:** netcfg config state; `tests/t126_netcfg_r11`.
