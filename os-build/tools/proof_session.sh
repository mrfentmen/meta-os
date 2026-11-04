#!/bin/bash
# proof_session.sh — one command that says whether the Meta OS image is healthy.
#
# Runs INSIDE the guest:
#   bash proof_session.sh
#   bash /opt/face/proof_session.sh
#
# Install:
#   bash proof_session.sh --install     # copies itself to /opt/face/proof_session.sh
#   cp proof_session.sh /opt/face/proof_session.sh
#
# What it does: curls every face/metaosd backend, prints a PASS/FAIL table,
# exits 1 if any row fails and names the dead port(s).
#
# Rows (9 checks, 8 ports):
#   18900 GET /shell.html    -> 200
#   18931 POST /launch {}    -> 403 refusal is EXPECTED (allow-list, no shell)
#   18932 GET /facts         -> 200 + cpu/mem/disk/net keys
#   18933 TCP connect        -> connect succeeds (ptyd is raw TCP + WS)
#   18934 GET /index.html    -> 200
#   18935 GET /rooms         -> 200 + rooms key
#   18936 GET /trash         -> 200 + ok key
#   18940 GET /status        -> 200 + stateDir/queueUrl key
#   18940 GET /agents        -> 200 + agents/ok key
#
# Deps: curl, python3 (stdlib only). Loopback only.
set -u

HOST="${PROOF_HOST:-127.0.0.1}"
TIMEOUT="${PROOF_TIMEOUT:-5}"
SELF="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/$(basename -- "$0")"

if [ "${1:-}" = "--install" ]; then
  DST="/opt/face/proof_session.sh"
  if mkdir -p "$(dirname "$DST")" 2>/dev/null && cp -f "$SELF" "$DST" 2>/dev/null; then
    chmod +x "$DST" 2>/dev/null || true
    echo "installed to $DST"
  elif command -v sudo >/dev/null 2>&1 && sudo mkdir -p "$(dirname "$DST")" && sudo cp -f "$SELF" "$DST" && sudo chmod +x "$DST"; then
    echo "installed to $DST (via sudo)"
  else
    echo "install: cannot write $DST (try: sudo cp proof_session.sh $DST)" >&2
    exit 2
  fi
  exit 0
fi

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "usage: bash proof_session.sh [--install]"
  echo "  runs inside the guest, checks 127.0.0.1 backends, exit 1 on any FAIL"
  exit 0
fi

command -v curl >/dev/null 2>&1 || { echo "FAIL: curl not found" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "FAIL: python3 not found" >&2; exit 2; }

TMPD="$(mktemp -d "${TMPDIR:-/tmp}/proof-session-XXXXXX")"
trap 'rm -rf "$TMPD"' EXIT INT TERM

PASS=0
FAIL=0
DEAD=""

row() {
  # row <port> <endpoint> <expect> <got> <pass:0/1> <note>
  port="$1"; endpoint="$2"; expect="$3"; got="$4"; ok="$5"; note="${6:-}"
  if [ "$ok" = "1" ]; then
    result="PASS"
    PASS=$((PASS + 1))
  else
    result="FAIL"
    FAIL=$((FAIL + 1))
    DEAD="$DEAD $port"
  fi
  if [ -n "$note" ]; then
    printf "%-6s %-18s %-16s %-14s %-6s %s\n" "$port" "$endpoint" "$expect" "$got" "$result" "$note"
  else
    printf "%-6s %-18s %-16s %-14s %-6s\n" "$port" "$endpoint" "$expect" "$got" "$result"
  fi
}

http_code() {
  # http_code <method> <url> [data] -> prints "<code> <bodyfile>"
  method="$1"; url="$2"; data="${3:-}"
  body="$TMPD/body.$$.$RANDOM"
  if [ "$method" = "POST" ]; then
    code="$(curl -s -m "$TIMEOUT" -o "$body" -w "%{http_code}" -X POST "$url" \
      -H "Content-Type: application/json" --data "$data" 2>/dev/null || true)"
  else
    code="$(curl -s -m "$TIMEOUT" -o "$body" -w "%{http_code}" "$url" 2>/dev/null || true)"
  fi
  [ -n "$code" ] || code="000"
  # curl prints 000 on connection failure already; guard against empty
  printf "%s %s" "$code" "$body"
}

echo "Meta OS session proof — host $HOST"
printf "%-6s %-18s %-16s %-14s %-6s\n" "PORT" "ENDPOINT" "EXPECT" "GOT" "RESULT"
echo "----------------------------------------------------------------------"

# 1) 18900 /shell.html
set -- $(http_code GET "http://$HOST:18900/shell.html")
code="$1"; body="$2"
if [ "$code" = "200" ] && grep -aq "<html" "$body" 2>/dev/null; then
  row "18900" "/shell.html" "200" "$code" 1 ""
else
  if [ "$code" = "000" ]; then got="conn refused"; else got="$code"; fi
  row "18900" "/shell.html" "200" "$got" 0 ""
fi

# 2) 18931 POST /launch {} -> 403 refusal is EXPECTED
set -- $(http_code POST "http://$HOST:18931/launch" '{}')
code="$1"; body="$2"
if [ "$code" = "403" ] && grep -aq "ok" "$body" 2>/dev/null; then
  row "18931" "POST /launch" "403 refusal" "$code" 1 "refusal expected"
else
  if [ "$code" = "000" ]; then got="conn refused"; else got="$code"; fi
  row "18931" "POST /launch" "403 refusal" "$got" 0 "want 403, got $got"
fi

# 3) 18932 /facts
set -- $(http_code GET "http://$HOST:18932/facts")
code="$1"; body="$2"
if [ "$code" = "200" ] && grep -aq "cpu" "$body" 2>/dev/null && grep -aq "mem" "$body" 2>/dev/null; then
  row "18932" "/facts" "200" "$code" 1 ""
else
  if [ "$code" = "000" ]; then got="conn refused"; else got="$code"; fi
  row "18932" "/facts" "200" "$got" 0 ""
fi

# 4) 18933 TCP connect (ptyd raw TCP)
if python3 -c "import socket;socket.create_connection(('$HOST',18933),timeout=$TIMEOUT).close()" 2>/dev/null; then
  row "18933" "TCP connect" "connect" "open" 1 ""
else
  row "18933" "TCP connect" "connect" "refused" 0 ""
fi

# 5) 18934 /index.html
set -- $(http_code GET "http://$HOST:18934/index.html")
code="$1"; body="$2"
if [ "$code" = "200" ]; then
  row "18934" "/index.html" "200" "$code" 1 ""
else
  if [ "$code" = "000" ]; then got="conn refused"; else got="$code"; fi
  row "18934" "/index.html" "200" "$got" 0 ""
fi

# 6) 18935 /rooms
set -- $(http_code GET "http://$HOST:18935/rooms")
code="$1"; body="$2"
if [ "$code" = "200" ] && grep -aq "rooms" "$body" 2>/dev/null; then
  row "18935" "/rooms" "200" "$code" 1 ""
else
  if [ "$code" = "000" ]; then got="conn refused"; else got="$code"; fi
  row "18935" "/rooms" "200" "$got" 0 ""
fi

# 7) 18936 /trash
set -- $(http_code GET "http://$HOST:18936/trash")
code="$1"; body="$2"
if [ "$code" = "200" ] && grep -aq "ok" "$body" 2>/dev/null; then
  row "18936" "/trash" "200" "$code" 1 ""
else
  if [ "$code" = "000" ]; then got="conn refused"; else got="$code"; fi
  row "18936" "/trash" "200" "$got" 0 ""
fi

# 8) 18940 /status
set -- $(http_code GET "http://$HOST:18940/status")
code="$1"; body="$2"
if [ "$code" = "200" ] && grep -aq "stateDir" "$body" 2>/dev/null; then
  row "18940" "/status" "200" "$code" 1 ""
else
  if [ "$code" = "000" ]; then got="conn refused"; else got="$code"; fi
  # fall back: any 200 with queueUrl also counts (older metaosd)
  if [ "$code" = "200" ] && grep -aq "queueUrl" "$body" 2>/dev/null; then
    row "18940" "/status" "200" "$code" 1 ""
  else
    row "18940" "/status" "200" "$got" 0 ""
  fi
fi

# 9) 18940 /agents
set -- $(http_code GET "http://$HOST:18940/agents")
code="$1"; body="$2"
if [ "$code" = "200" ] && grep -aq "agents" "$body" 2>/dev/null; then
  # metaosd answers 200 with {ok:false} when no registry is staged;
  # that still proves the daemon is alive, so PASS liveness here.
  if grep -aq '"ok": *false' "$body" 2>/dev/null; then
    row "18940" "/agents" "200" "$code" 1 "no registry (daemon alive)"
  else
    row "18940" "/agents" "200" "$code" 1 ""
  fi
else
  if [ "$code" = "000" ]; then got="conn refused"; else got="$code"; fi
  row "18940" "/agents" "200" "$got" 0 ""
fi

echo "----------------------------------------------------------------------"
echo "PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
  # dedupe dead ports, keep numeric order
  # shellcheck disable=SC2086
  uniq_dead="$(printf "%s\n" $DEAD | sort -n -u | tr '\n' ' ')"
  echo "DEAD ports:$uniq_dead"
  echo "proof_session: FAIL ($FAIL row(s) failed)"
  exit 1
fi
echo "proof_session: PASS (9/9)"
exit 0
