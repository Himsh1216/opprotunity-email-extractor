#!/usr/bin/env bash
# Opportunity Mail Extractor - macOS / Linux launcher.
# Open Terminal, type "bash " (with a space), drag this file into the window and press Enter.
# Everything runs on this computer; nothing is uploaded.
set -u
cd "$(dirname "$0")" || exit 1

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$candidate"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.9 or newer is needed."
  echo "  macOS: install it from https://www.python.org/downloads/"
  echo "  Linux: sudo apt install python3 python3-venv   (or your distribution's equivalent)"
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "First run: setting up. This needs internet once and takes about a minute..."
  "$PY" -m venv .venv >/dev/null 2>&1 || rm -rf .venv
fi
if [ -x .venv/bin/python ]; then
  RUN=.venv/bin/python
  "$RUN" -c 'import openpyxl' 2>/dev/null ||
    "$RUN" -m pip install --quiet --disable-pip-version-check -r requirements.txt ||
    { echo "Could not install openpyxl. Check your internet connection and run this again."; exit 1; }
else
  RUN="$PY"   # no venv module (some Linux distributions): use the system Python
  "$RUN" -c 'import openpyxl' 2>/dev/null || {
    echo "Please install openpyxl first, then run this again:"
    echo "  $PY -m pip install --user openpyxl      (Debian/Ubuntu: sudo apt install python3-openpyxl)"
    exit 1
  }
fi

exec "$RUN" -m opportunity_extractor "$@"
