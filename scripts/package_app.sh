#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

APP_PATH="dist/AI Info Collection.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "[package-app] app not found: $APP_PATH"
  echo "[package-app] run scripts/build_app.sh first."
  exit 1
fi

OUT_DIR="dist"
STAMP="$(date +%Y%m%d-%H%M%S)"
ZIP_PATH="$OUT_DIR/AI-Info-Collection-$STAMP.zip"

ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
echo "[package-app] created: $ZIP_PATH"
