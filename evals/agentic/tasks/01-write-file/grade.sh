#!/bin/sh
set -e
test "$(cat hello.txt)" = "META_OK"
test "$(wc -c < hello.txt)" -eq 8
