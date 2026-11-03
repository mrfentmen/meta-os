# OC3B-041 — single- vs double-click policy (key named, observed deferred)

The governing key is Thunar's xfconf `/misc-single-click` (true =
single click opens, false = double click). No thunar.xml ships in any
theme/config tree on main, so the compiled-in upstream default applies
at first boot. This lane does NOT assert which default that is from
memory — OC1 records the observed behavior at first boot and, if the
project wants single-click, the fix is one xfconf line owned by the
theme lane. Until then: policy = upstream default, key named above.
