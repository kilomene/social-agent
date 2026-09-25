#!/usr/bin/env bash
# install.sh — create one isolated social-agent workspace ("its own brain").
# Usage: ./install.sh [--home DIR] [--force]
# Idempotent; refuses to clobber a non-empty foreign directory.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/core/install.py" "$@"
