# OC3B-044 + OC3B-043 — archives and thumbnailers

Archives: Xfce opens zip/tar via thunar-archive-plugin + an installed
archiver. Neither the plugin nor an archiver is named in any package
list on main, and no archive handler ships in OC2's drop-ins. So: NOT
claimed working. Owner to name the archiver package: ISO lane at
image build; OC1 confirms open-works at boot. Until then the honest
record is "absent until named", not a silent gap.

OC3B-043 quiet: no thumbnailer config ships in any lane (nothing to
phone home in-tree). Tumbler defaults, if present on the image, fetch
nothing off-machine for local files. Network-thumbnail behavior is an
OC1 boot note only if the Network node exists (see places note).
