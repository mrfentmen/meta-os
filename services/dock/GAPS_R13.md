# Gap records — R13-014 dock

## R13-014-G1 — failure-code table is missing from the README

- **Claim:** the dock documents its failure-code table.
- **Reality:** the README explains three behaviours in prose and names `E_BUSY` once. `E_INVAL`,
  `E_NOROOM`, `E_NO_SPACE`, `E_STATE` and `E_NOTFOUND` are not listed, and no table maps a
  function to the codes it can return.
- **Evidence:** `services/dock/README.md` (sections “What it is”, “The three rules”, “Surface”);
  source returns at `services/dock/dock.goose:103-230`.
- **Impact:** a caller has to read the implementation to know whether a launch can fail with
  `E_NOTFOUND` or `E_STATE`. The contract note above is now the only complete table.
- **Owner:** dock README.

## R13-014-G2 — two capacity codes for one operation

- **Claim:** `dk_pin` has one capacity failure.
- **Reality:** a name of 16+ bytes returns `E_NOROOM` (line 104); a full dock returns
  `E_NO_SPACE` (line 111). Both are capacity exhaustion at the same call site, with no README
  distinction.
- **Evidence:** `services/dock/dock.goose:102-111`.
- **Impact:** the caller must handle two codes for “cannot pin another entry”, and the names do
  not say which resource is exhausted (name buffer vs dock slots).
- **Owner:** dock error taxonomy.
