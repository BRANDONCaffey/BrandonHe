#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PY="${PYTHON:-python3}"

echo "[build-app] using python: $PY"
"$PY" -m pip install -e ".[app]"
"$PY" -m pip install "setuptools<81"
rm -rf build dist
if "$PY" setup.py py2app; then
  echo "[build-app] done with py2app: dist/AI Info Collection.app"
  exit 0
fi

echo "[build-app] py2app failed, fallback to PyInstaller..."
rm -rf build dist "__pycache__"
find . -maxdepth 1 -type f -name "*.spec" -delete
"$PY" -m PyInstaller \
  --noconfirm \
  --windowed \
  --name "AI Info Collection" \
  --paths "src" \
  launch_frontend.py

echo "[build-app] done with PyInstaller: dist/AI Info Collection.app"
