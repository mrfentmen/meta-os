# OC3B-130/131/146 — welcome app, once-only, fonts

- Opens from the menu: metaos-welcome.desktop committed on main
  (Exec + TryExec both point at the .py). Menu entry present.
- Shows once, not always: flag file `~/.config/metaos/welcome-shown`
  (CODE-INSPECTED in metaos-welcome.py: shown-once logic + graceful
  degradation). Observed-once confirmation is OC1's login test.
- test_welcome.py: 30/30 PASS on this Mac when the trio it tests
  (.py + test + .desktop) is co-located, as shipped on main.
  An earlier 4-error run in /tmp was my harness missing the
  .desktop file, not a product defect — recorded so nobody
  re-discovers it as a scare.
- Inter in the font picker: xsettings pins `FontName=Inter 10`
  on main; the picker lists it because the desktop does. Config
  verified, pixels are OC1's.
