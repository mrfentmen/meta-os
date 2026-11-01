#!/bin/bash
# Starts the MCP gateway from this directory (repo copy).
# Needs a local venv with the Python MCP SDK: see README.md in this folder.
set -u
cd "$(dirname "$0")"
exec .venv/bin/python gateway.py
