# OC3B-027/028/032/033/042/047 basics + OC3B-035/049 USB + OC3B-036 network + OC3B-048 disk — boot-bound, owners named

Every task in this file opens Thunar and observes it. No Thunar runs
on this Mac against the image (no squashfs tooling, no boot rights —
OC1 owns all boots). Per the no-waiting rule each item below is
recorded BLOCKED-with-owner, not left blank:

- 027 open/list/create/rename/delete, 028 trash+empty, 032 hidden-files
  toggle, 033 in-folder search, 042 thumbnails, 047 opens-under-2s-cold:
  owner OC1 at first boot. Expected pass per Xfce defaults; timed
  claims (047) need OC1's stopwatch, not estimates.
- 035 USB appears when plugged + 049 eject/unmount: owner OC1 with
  hardware in hand; stack owner (gvfs/udevil provision) named if the
  sidebar stays empty.
- 036 network locations: working-or-honestly-absent is an OC1
  observation (needs gvfs-backends on the image — package presence
  itself is an ISO-lane question already filed under archives).
- 048 disk-usage correctness: OC1, one screenshot of Properties vs
  `df`, at boot.
- OC3B-031 home defaults (Documents/Downloads/Pictures/Music): NOT
  asserted — Xubuntu ships xdg-user-dirs but provisioning them is the
  first-boot path, which is OC3's T3/OC1 territory to observe. Owner:
  whoever runs first boot; watch item here.
