# Gap records — R13-011 dhcp

## R13-011-G1 — short known options are silently skipped

- **Claim:** malformed DHCP options are refused (`README`, “What the parser refuses”).
- **Reality:** the bounds check only catches a length that runs past the packet. For a known
  fixed-width option such as option 1, 51, 54, 58 or 59, a length of 1–3 falls through every
  `len >= 4` branch and is discarded without an error. A packet with a 3-byte subnet mask and a
  valid lease returns `E_NO_MASK`, not `E_CORRUPT`.
- **Evidence:** `services/dhcp/dhcp.goose:235-261` — the TLV bounds check is at 237; each known
  option then tests `len >= 4` and has no `else` refusal.
- **Impact:** the packet still cannot become a lease without a valid mask, so this is a
  misclassification rather than a bind of malformed data. A client diagnosing its network gets
  the wrong reason.
- **Owner:** dhcp parser; fixture `tests/t114_dhcp_r11` should pin the error code.

## R13-011-G2 — non-contiguous mask is indistinguishable from an absent mask

- **Claim:** a malformed mask is an input-validation failure.
- **Reality:** `ip4_mask_contiguous(out.mask)` only sets `mask_given` when the mask is contiguous;
  a mask that was present but invalid leaves `mask_given == false` and returns `E_NO_MASK`.
- **Evidence:** `services/dhcp/dhcp.goose:240-242` and `:269-273`.
- **Impact:** the README says `E_NO_MASK` means “no subnet mask (option 1)”, but the code also
  returns it for a malformed option 1. Callers cannot choose different remediation.
- **Owner:** dhcp parser error taxonomy.
