# install.sh desktop proposal (NOT applied — OC1 owns system install)

Sketch for a future opt-in `--with-desktop` flag on `agent-layer/install.sh`
(user-level `$HOME/.local/share/applications`, no sudo, no mimeapps copy,
default OFF so current behavior is unchanged). Filed here instead of editing
the installer while OC1/OC3 work, so the default install path stays frozen.

```diff
--- a/agent-layer/install.sh
+++ b/agent-layer/install.sh
@@ -61,6 +61,24 @@
 echo "units linked: $(ls "$ROOT/agent-layer/units" | tr '\n' ' ')"
 
+# 4b. Desktop entries (OPT-IN, default OFF; user-level only, no sudo).
+# Without --with-desktop this block is skipped: default behavior unchanged.
+# System-wide /usr/share/applications remains OC1's lane (see
+# agent-layer/desktop-entries/README.md); mimeapps.list is never copied here.
+WITH_DESKTOP=0
+for arg in "$@"; do
+  case "$arg" in --with-desktop) WITH_DESKTOP=1 ;; esac
+done
+if [ "$WITH_DESKTOP" = "1" ]; then
+  DESKDIR="$HOME/.local/share/applications"
+  mkdir -p "$DESKDIR"
+  for path in "$ROOT/agent-layer/desktop-entries/"*.desktop; do
+    [ -e "$path" ] || continue
+    cp "$path" "$DESKDIR/$(basename "$path")"
+  done
+  update-desktop-database "$DESKDIR" 2>/dev/null || true
+  echo "desktop entries installed to $DESKDIR (user-level; system /usr/share is OC1's lane)"
+fi
+
 # 5. Reload + enable (linger attempted; recorded if unavailable).
```

Decision for later (not now): adopt only if OC1 asks for a user-level
install path. System install stays OC1's lane per INSTALL-OC1.md.
