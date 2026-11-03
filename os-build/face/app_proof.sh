#!/bin/bash
# app_proof.sh — dock-lane proof: notes/notesd + editor/files/trash as one system.
#
# Runs INSIDE the guest (or anywhere 18936/18937 answer on loopback):
#   bash /opt/face/app_proof.sh
#
# Rows (notesd :18937 + files :18936):
#   1. write note (POST /notes)              -> 200 + id
#   2. read back (GET /notes has id+text)    -> match
#   3. md mirror (~/Notes/<id>.md has text)  -> match
#   4. trash (POST /trash the .md)           -> gone from disk
#   5. restore (POST /restore)                -> byte-identical (md5)
#   6. edit-save (POST /save new text)       -> GET /read matches
#
# Prints PASS/FAIL per row, exits 1 on any failure.
set -u

HOST="${PROOF_HOST:-127.0.0.1}"
NOTES="http://$HOST:18937"
FILES="http://$HOST:18936"

command -v curl >/dev/null 2>&1 || { echo "FAIL: curl not found" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "FAIL: python3 not found" >&2; exit 2; }

TMPD="$(mktemp -d "${TMPDIR:-/tmp}/app-proof-XXXXXX")"
trap 'rm -rf "$TMPD"' EXIT INT TERM

PASS=0
FAIL=0

row() {
  # row <name> <pass:0/1> [note]
  name="$1"; ok="$2"; note="${3:-}"
  if [ "$ok" = "1" ]; then
    echo "PASS $name${note:+ ($note)}"
    PASS=$((PASS + 1))
  else
    echo "FAIL $name${note:+ ($note)}"
    FAIL=$((FAIL + 1))
  fi
}

TEXT="app-proof note $(date -u +%FT%TZ) body-alpha"
EDITED="app-proof note second revision body-beta"

# 1) write note
code="$(curl -s -m 10 -o "$TMPD/create.json" -w "%{http_code}" -X POST "$NOTES/notes" \
  -H "Content-Type: application/json" \
  --data "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "$TEXT")")"
NID="$(python3 -c 'import json; print(json.load(open("'$TMPD'/create.json")).get("note",{}).get("id",""))' 2>/dev/null)"
if [ "$code" = "200" ] && [ -n "$NID" ]; then row "1 write-note" 1 "id=$NID"; else row "1 write-note" 0 "http=$code"; fi

# 2) read back
code="$(curl -s -m 10 -o "$TMPD/list.json" -w "%{http_code}" "$NOTES/notes")"
if [ "$code" = "200" ] && python3 - "$TMPD/list.json" "$NID" "$TEXT" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
notes = d.get("notes", []) if d.get("ok") else []
hits = [n for n in notes if n.get("id") == sys.argv[2] and n.get("text") == sys.argv[3]]
sys.exit(0 if hits else 1)
EOF
then row "2 read-back" 1; else row "2 read-back" 0 "http=$code"; fi

# 3) md mirror
MDFILE="$HOME/Notes/$NID.md"
if [ -f "$MDFILE" ] && grep -q "body-alpha" "$MDFILE"; then row "3 md-mirror" 1 "$MDFILE"; else row "3 md-mirror" 0 "$MDFILE"; fi

# 4) trash the mirror through files.py
BEFORE_MD5="$(md5sum "$MDFILE" 2>/dev/null | cut -d' ' -f1)"
code="$(curl -s -m 10 -o "$TMPD/trash.json" -w "%{http_code}" -X POST "$FILES/trash" \
  -H "Content-Type: application/json" \
  --data "$(python3 -c 'import json,sys; print(json.dumps({"path": sys.argv[1]}))' "$MDFILE")")"
TNAME="$(python3 -c 'import json; print(json.load(open("'$TMPD'/trash.json")).get("name",""))' 2>/dev/null)"
if [ "$code" = "200" ] && [ -n "$TNAME" ] && [ ! -e "$MDFILE" ]; then row "4 trash" 1 "name=$TNAME"; else row "4 trash" 0 "http=$code"; fi

# 5) restore, byte-identical
code="$(curl -s -m 10 -o "$TMPD/restore.json" -w "%{http_code}" -X POST "$FILES/restore" \
  -H "Content-Type: application/json" \
  --data "$(python3 -c 'import json,sys; print(json.dumps({"name": sys.argv[1]}))' "$TNAME")")"
AFTER_MD5="$(md5sum "$MDFILE" 2>/dev/null | cut -d' ' -f1)"
if [ "$code" = "200" ] && [ -n "$BEFORE_MD5" ] && [ "$BEFORE_MD5" = "$AFTER_MD5" ]; then row "5 restore-identical" 1 "md5=$AFTER_MD5"; else row "5 restore-identical" 0 "http=$code"; fi

# 6) edit-save new text through files.py, read back
code="$(curl -s -m 10 -o "$TMPD/save.json" -w "%{http_code}" -X POST "$FILES/save" \
  -H "Content-Type: application/json" \
  --data "$(python3 -c 'import json,sys; print(json.dumps({"path": sys.argv[1], "content": sys.argv[2]}))' "$MDFILE" "$EDITED")")"
GOT="$(curl -s -m 10 "$FILES/read?path=$MDFILE" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("content",""))' 2>/dev/null)"
if [ "$code" = "200" ] && [ "$GOT" = "$EDITED" ]; then row "6 edit-save-read" 1; else row "6 edit-save-read" 0 "http=$code"; fi

# cleanup: delete the proof note from the daemon + remove the file
curl -s -m 10 -o /dev/null -X POST "$NOTES/notes/delete" -H "Content-Type: application/json" \
  --data "$(python3 -c 'import json,sys; print(json.dumps({"id": sys.argv[1]}))' "$NID")" 2>/dev/null
rm -f "$MDFILE" 2>/dev/null

echo "----------------------------------------------------------------------"
echo "PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
  echo "app_proof: FAIL ($FAIL row(s) failed)"
  exit 1
fi
echo "app_proof: PASS (6/6)"
exit 0
