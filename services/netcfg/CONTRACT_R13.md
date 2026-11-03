# Contract note — R13-023, netcfg README accuracy

Status: **AUDITED — 2 gaps filed**.
Facet: whether every claim in `services/netcfg/README.md` matches the parser and persistence code.

## Evidence

Command:

```sh
nl -ba services/netcfg/netcfg.goose | sed -n '288,350p'
nl -ba services/netcfg/persist.goose | sed -n '95,125p'
```

Relevant output:

```text
301  let said_dhcp, dhcp_ok = cfg_bool(cfg, sec, "dhcp", false);
302  if dhcp_ok && said_dhcp { c.use_dhcp = true; }
...
339  let mtu_v, mtu_ok = cfg_int(cfg, sec, "mtu", 1500);
340  if mtu_ok {
341      if mtu_v < 576 || mtu_v > 1500 { return c, E_INVAL; }
342      c.mtu = mtu_v;
343  }
...
347  if got_addr && !c.use_dhcp && ip4_zero(c.mask) { return c, E_INVAL; }
348  c.configured = got_addr || dhcp_ok;
```

```text
101  fn netcfg_save(ino: i64, c: IfaceCfg&) -> i64 {
107      let tcode = fs_truncate(ino);
108      if tcode != CODE_OK { return tcode; }
109      let wrote, wcode = fs_write(ino, 0, text[..]);
111      if wrote != n { return E_IO; }
```

## Corrected contract

The README is accurate on parsing, masks, fresh read buffers, `dhcp=yes` precedence, the
static-address-without-mask refusal, and save-then-truncate ordering. Two statements do not match:

- README: “**MTU is clamped to 576..1500.**” Code: an out-of-range MTU is refused with `E_INVAL`;
  nothing is clamped.
- README: `configured` “records the second question separately.” Code sets
  `c.configured = got_addr || dhcp_ok`, where `dhcp_ok` means the `dhcp` key parsed, even when its
  value is `no`. A file containing only `dhcp=no` therefore marks the interface configured.

`netcfg_save` is correctly ordered: truncate, check the truncate code, write, require a full
write, return `E_IO` on a short write.

## Mismatches

- **R13-023-G1** — “clamped” is false; out-of-range MTU is rejected.
- **R13-023-G2** — `configured` is true for `dhcp=no`, not only for an address or dynamic
  configuration. See `services/netcfg/GAPS_R13.md`.
