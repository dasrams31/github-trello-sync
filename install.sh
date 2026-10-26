#!/usr/bin/env sh
# Installer github-trello-sync untuk Linux, macOS, dan Git Bash di Windows.
# Pemakaian dari folder repo target:
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/dasrams31/github-trello-sync/main/install.sh)"
set -eu

RAW="https://raw.githubusercontent.com/dasrams31/github-trello-sync/main/install.py"

PY=""
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1 \
    && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.8 atau lebih baru belum terpasang. Unduh di https://www.python.org/downloads/" >&2
  exit 1
fi

SCRIPT=""
HERE=$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)
if [ -n "$HERE" ] && [ -f "$HERE/install.py" ]; then
  SCRIPT="$HERE/install.py"
else
  SCRIPT=$(mktemp)
  trap 'rm -f "$SCRIPT"' EXIT
  curl -fsSL "$RAW" -o "$SCRIPT"
fi

if [ -t 0 ]; then
  "$PY" "$SCRIPT" "$@"
else
  "$PY" "$SCRIPT" "$@" </dev/tty
fi
