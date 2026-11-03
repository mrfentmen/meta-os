# Install: /etc/bash.bashrc.d/metaos.sh (or ~/.bashrc.d/). Shows the
# spinning-logo system screen once per interactive shell.
if [ -n "$PS1" ] && [ -z "$METAOS_WELCOMED" ]; then
  export METAOS_WELCOMED=1
  node /usr/share/metaos/metafetch.mjs --once 2>/dev/null || true
fi
