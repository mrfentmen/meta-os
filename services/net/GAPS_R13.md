# Gap records — R13-022 net

## R13-022-G1 — no captured packet fixtures

- **Claim:** `net` has a fixture corpus covering its parsers.
- **Reality:** there is no `.pcap`, binary fixture or replay file under `services/tests` or
  `os-build`. Every frame is built in a Goose test, starting from a zeroed
  `u8[..1500]` buffer and assigning bytes.
- **Evidence:** the `find` and `grep` commands in `CONTRACT_R13.md`; `t67_net.goose:61`.
- **Impact:** a regression caused by a real-world frame shape that the test author did not
  imagine has no fixture to catch it. Coverage is only as broad as the inline builders.
- **Owner:** net test corpus.

## R13-022-G2 — successful kernel transmit/receive is unproven

- **Claim:** the packet interface has been exercised end to end.
- **Reality:** `sys_net_send` and `sys_net_recv` are extern declarations with no kernel
  implementation. The host shim refuses every frame, so tests assert `E_IO` and the drop counter;
  loopback is the only path that completes.
- **Evidence:** `services/net/README.md` “What running does not prove”;
  `services/net/packet.goose:26-27`.
- **Impact:** every successful hardware send/receive path, including MTU behaviour on a real link,
  is untested. The refusal paths are real; the delivery path is not.
- **Owner:** B-L1-73 packet binding; Layer 3 driver.
