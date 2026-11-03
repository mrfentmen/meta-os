# OC3B-034 — file manager sidebar (CODE-INSPECTED defaults)

Thunar sidebar out of the box: Home, Desktop, File System, removable
volumes when present, Network browsing node. Evidence from tree, not
boot: the MetaOS icon theme ships `places/48/user-home.svg`,
`folder.svg`, `folder-open.svg` (theme/src present on main), so the
sidebar Home/Folder glyphs resolve to Meta art, not Grey icon-set
fallbacks. Xfce panel/launcher side is OC1/theme territory.
Presence-or-absence of the Network node at runtime is an OC1 boot
note (Thunar needs gvfs-backends; not asserted here either way).
