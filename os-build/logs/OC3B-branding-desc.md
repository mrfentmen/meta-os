# OC3B-261/262 — branding.desc matches reality

File: os-build/iso/calamares/branding/metaos/branding.desc on main.

- productName "MetaOS", shortProductName "MetaOS", version "1.0",
  shortVersion "1.0", versionedName "MetaOS 1.0",
  bootloaderEntryName "MetaOS". Correct for the 1.0 remaster
  (OC3B-262 PASS).
- Images productLogo/productIcon/productWelcome point at PNGs that
  exist in the same dir (verified in tree listing). Header states
  they are drawn by assets/make_assets.py (ring mark + 5x7 block
  wordmark, original work).
- URLs deliberately absent (no public domain yet); welcome.conf
  sets showSupportUrl/showReleaseNotesUrl false. Honest, not a gap.
- 261 verdict: descriptor matches the shipped payload. No drift.
